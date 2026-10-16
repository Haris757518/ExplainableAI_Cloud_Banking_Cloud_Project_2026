import json
import sqlite3
from datetime import datetime, timezone, timedelta
from pathlib import Path
import pytest
from botocore.exceptions import ClientError, EndpointConnectionError
from aws.banking_publisher import run_publisher, row_metrics, connect_readonly
from aws.banking_cloudwatch import collect, investigate

@pytest.fixture
def telemetry(tmp_path):
    p=tmp_path/'telemetry.db'
    db=sqlite3.connect(p)
    db.executescript('CREATE TABLE requests(seq INTEGER PRIMARY KEY,trace_id TEXT,operation TEXT,ts REAL,duration_ms REAL,success INTEGER,status INTEGER,client_latency_ms REAL); CREATE TABLE spans(id TEXT,trace_id TEXT,end REAL,payload TEXT);')
    ts=datetime.now(timezone.utc).timestamp()-120
    for seq in (1,2):
        db.execute('INSERT INTO requests VALUES(?,?,?,?,?,?,?,?)',(seq,'private-trace-'+str(seq),'transfer',ts+seq,21.5,seq%2,200,25.5 if seq==1 else None))
        for i,(service,kind,duration) in enumerate([('banking-api','server',21.5),('ledger-service','server',14),('banking-db','database',2),('banking-db','connection',.5)]):
            span={'service':service,'kind':kind,'operation':'transfer','duration_ms':duration,'exclusive_ms':3,'end':ts+seq,'account':'NEVER PUBLISH'}
            db.execute('INSERT INTO spans VALUES(?,?,?,?)',(str(seq)+str(i),'private-trace-'+str(seq),ts+seq,json.dumps(span)))
    db.commit();db.close();return p

class Writer:
    def __init__(self,fail_on=None,error=None):self.calls=[];self.fail_on=fail_on;self.error=error
    def put_metric_data(self,**kwargs):
        self.calls.append(kwargs)
        if len(self.calls)==self.fail_on:raise self.error
        return {'ResponseMetadata':{'HTTPStatusCode':200}}

def test_actual_metrics_timestamps_units_privacy_and_missing(telemetry):
    with connect_readonly(telemetry) as db:
        row=db.execute('SELECT * FROM requests WHERE seq=1').fetchone();metrics=row_metrics(db,row)
        assert all(m['Timestamp'].timestamp()==row['ts'] for m in metrics)
        assert {m['MetricName'] for m in metrics}=={'RequestCount','ErrorCount','RequestLatencyMilliseconds','ClientLatencyMilliseconds','ServiceLatencyMilliseconds','ExclusiveProcessingMilliseconds','DBQueryMilliseconds','DBConnectionMilliseconds'}
        assert next(m for m in metrics if m['MetricName']=='RequestLatencyMilliseconds')['Value']==21.5
        assert all(m['Unit']==('Count' if m['MetricName'] in ('RequestCount','ErrorCount') else 'Milliseconds') for m in metrics)
        text=json.dumps(metrics,default=str)
        assert 'private-trace' not in text and 'NEVER PUBLISH' not in text and 'account' not in text
        assert 'ClientLatencyMilliseconds' not in [m['MetricName'] for m in row_metrics(db,db.execute('SELECT * FROM requests WHERE seq=2').fetchone())]
        with pytest.raises(sqlite3.OperationalError):db.execute('DELETE FROM requests')

def test_checkpoint_dry_run_and_duplicate_prevention(telemetry,tmp_path):
    cp=tmp_path/'checkpoint.db';cw=Writer()
    assert run_publisher(telemetry,cp,'us-east-1',cw=cw)['published_requests']==0
    assert not cw.calls
    result=run_publisher(telemetry,cp,'us-east-1',cw=cw,publish=True)
    assert result['published_requests']==2 and result['last_confirmed_sequence']==2
    assert result['published_metric_values']==sum(len(call['MetricData']) for call in cw.calls)
    assert run_publisher(telemetry,cp,'us-east-1',cw=cw,publish=True)['status']=='no_new_requests'
    assert len(cw.calls)==2
    assert sum(m['Value'] for c in cw.calls for m in c['MetricData'] if m['MetricName']=='RequestCount')==2
    assert sum(m['Value'] for c in cw.calls for m in c['MetricData'] if m['MetricName']=='ErrorCount')==1

def test_denied_partial_batch_resumes_only_unpublished(telemetry,tmp_path):
    cp=tmp_path/'checkpoint.db'
    error=ClientError({'Error':{'Code':'AccessDenied'},'ResponseMetadata':{'HTTPStatusCode':403}},'PutMetricData')
    cw=Writer(2,error)
    result=run_publisher(telemetry,cp,'us-east-1',cw=cw,publish=True)
    assert result['published_requests']==1 and result['error_code']=='AccessDenied'
    retry=Writer();result=run_publisher(telemetry,cp,'us-east-1',cw=retry,publish=True)
    assert result['published_requests']==1 and len(retry.calls)==1

def test_network_ambiguity_blocks_replay(telemetry,tmp_path):
    cp=tmp_path/'checkpoint.db';cw=Writer(1,EndpointConnectionError(endpoint_url='https://cloudwatch.example'))
    assert run_publisher(telemetry,cp,'us-east-1',cw=cw,publish=True)['status']=='ambiguous_publication'
    retry=Writer()
    assert run_publisher(telemetry,cp,'us-east-1',cw=retry,publish=True)['status']=='ambiguous_publication'
    assert not retry.calls

def test_operation_mapping_and_safety_limits(telemetry,tmp_path):
    with pytest.raises(ValueError):run_publisher(telemetry,tmp_path/'cp','us-east-1',limit=21)
    db=sqlite3.connect(telemetry);db.execute("UPDATE requests SET operation='secret-operation'");db.commit();db.close()
    with pytest.raises(ValueError):run_publisher(telemetry,tmp_path/'cp','us-east-1')

class Reader:
    def __init__(self,paginate=False,denied=False,partial=False):self.calls=[];self.paginate=paginate;self.denied=denied;self.partial=partial
    def get_metric_data(self,**args):
        self.calls.append(args)
        if self.denied:raise ClientError({'Error':{'Code':'AccessDenied'}},'GetMetricData')
        stamp=datetime.now(timezone.utc)-timedelta(minutes=2)
        entries=[{'Id':q['Id'],'StatusCode':'PartialData' if self.partial else 'Complete','Timestamps':[stamp] if q['Id']=='b0' else [],'Values':[3] if q['Id']=='b0' else []} for q in args['MetricDataQueries']]
        return {'MetricDataResults':entries,**({'NextToken':'page2'} if self.paginate and len(self.calls)==1 else {})}

def test_custom_metrics_without_infrastructure_and_pagination():
    cw=Reader(paginate=True);result=collect('us-east-1',cw=cw)
    assert result['observed_series']==1 and result['collection_complete']
    assert len(cw.calls)==2 and cw.calls[1]['NextToken']=='page2'
    assert result['hosting']=='local' and result['resource_relationship']=='not_established'
    assert result['series'][0]['dimensions'][0]['Value']=='academic-local-test'
    assert result['series'][0]['statistic']=='Sum' and result['series'][0]['unit']=='Count'
    assert result['investigation']['status']=='insufficient_evidence'

def test_read_denial_and_partial_responses():
    assert collect('us-east-1',cw=Reader(denied=True))['errors']==[{'code':'AccessDenied'}]
    result=collect('us-east-1',cw=Reader(partial=True))
    assert result['status']=='partial_collection' and not result['collection_complete']
    assert result['investigation']['status']=='insufficient_evidence'

def test_empty_is_missing_not_zero():
    class Empty:
        def get_metric_data(self,**args):return {'MetricDataResults':[{'Id':q['Id'],'StatusCode':'Complete','Timestamps':[],'Values':[]} for q in args['MetricDataQueries']]}
    result=collect('us-east-1',cw=Empty())
    assert result['status']=='pending_or_insufficient_data'
    assert all(s['missing_data'] and not s['points'] for s in result['series'])

def test_stale_or_partial_data_cannot_become_current_anomaly():
    now=datetime.now(timezone.utc)
    row={'metric_name':'ServiceLatencyMilliseconds','service':'ledger-service','operation':'transfer','response_status':'Complete','points':[{'timestamp':(now-timedelta(minutes=30-i)).isoformat(),'value':10 if i<8 else 100} for i in range(10)]}
    result=investigate({'series':[row],'end':now.isoformat(),'collection_complete':True})
    assert not result['affected_services'] and result['findings'][0]['status']=='historical_evidence_only'
    row['points']=[{'timestamp':(now-timedelta(minutes=10-i)).isoformat(),'value':10 if i<8 else 100} for i in range(10)]
    result=investigate({'series':[row],'end':now.isoformat(),'collection_complete':True})
    assert result['affected_services']==['ledger-service'] and result['root_cause']=='not_established'
    assert investigate({'series':[row],'end':now.isoformat(),'collection_complete':False})['status']=='insufficient_evidence'

def test_banking_cloud_endpoint_independent_of_infrastructure(monkeypatch):
    from fastapi.testclient import TestClient
    from backend.main import app
    import backend.aws_banking_api as api
    monkeypatch.setattr(api,'collect',lambda *args:{'status':'observations_available','hosting':'local','resource_relationship':'not_established'})
    with TestClient(app) as client:
        response=client.get('/api/aws/banking/metrics')
        assert response.status_code==200 and response.json()['hosting']=='local'
        assert client.get('/api/aws/banking/metrics?lookback_minutes=30000').status_code==422
        assert client.post('/api/aws/banking/publish').status_code in (404,405)

def test_expired_measurements_not_retimestamped(telemetry,tmp_path):
    db=sqlite3.connect(telemetry);db.execute('UPDATE requests SET ts=ts-15*86400');db.commit();db.close()
    writer=Writer();result=run_publisher(telemetry,tmp_path/'cp','us-east-1',publish=True,cw=writer)
    assert result['status']=='timestamp_outside_publication_window' and not writer.calls
