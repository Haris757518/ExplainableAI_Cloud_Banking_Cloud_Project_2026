"""Isolated synthetic test fixtures only; no AWS calls or live transfers."""
import copy,json,sqlite3,time
from datetime import datetime,timezone
from pathlib import Path
import pytest
from botocore.exceptions import EndpointConnectionError
from aws.banking_publisher import run_publisher,DEMO_ENVIRONMENT
from aws.banking_demo import (create_session,load_session,record_request,validate_source_windows,
    collect_demo,freeze_reference,analyze_demo,trace_corroboration,public_report,bucket,iso,SPECS)
from aws.banking_demo import publish_new

@pytest.fixture
def db(tmp_path):
    path=tmp_path/'telemetry.db'
    with sqlite3.connect(path) as conn:
        conn.executescript('CREATE TABLE requests(seq INTEGER PRIMARY KEY,trace_id TEXT,operation TEXT,ts REAL,duration_ms REAL,success INTEGER,status INTEGER,client_latency_ms REAL); CREATE TABLE spans(id TEXT,trace_id TEXT,end REAL,payload TEXT);')
        conn.execute('INSERT INTO requests VALUES(1,?,?,?,?,?,?,?)',('historical','transfer',time.time()-60,20,1,200,None))
    return path

def insert_request(path,seq,ts):
    with sqlite3.connect(path) as conn:
        conn.execute('INSERT INTO requests VALUES(?,?,?,?,?,?,?,?)',(seq,f'trace-{seq}','transfer',ts,20,1,200,None))
        for i,(service,kind,value) in enumerate([('banking-api','server',20),('ledger-service','server',5),('banking-db','database',1),('banking-db','connection',.2)]):
            payload={'service':service,'kind':kind,'operation':'transfer','end':ts,'duration_ms':value,'exclusive_ms':value}
            conn.execute('INSERT INTO spans VALUES(?,?,?,?)',(f'{seq}-{i}',f'trace-{seq}',ts,json.dumps(payload)))

class Writer:
    def __init__(self,error=None):self.calls=[];self.error=error
    def put_metric_data(self,**kwargs):
        self.calls.append(kwargs)
        if self.error:raise self.error
        return {'ResponseMetadata':{'HTTPStatusCode':200}}

def test_preparation_captures_backlog_without_original_checkpoint_changes(db,tmp_path):
    original=tmp_path/'original-checkpoint.db';original.write_bytes(b'protected standard checkpoint')
    state=create_session(tmp_path/'sessions','demo-test',db,'us-east-1')
    assert state['start_sequence']==1 and not state['records'] and state['status']=='prepared'
    assert original.read_bytes()==b'protected standard checkpoint'
    assert load_session(tmp_path/'sessions/demo-test')['source_identity']==state['source_identity']
    with pytest.raises(ValueError):create_session(tmp_path/'sessions','demo-test',db,'us-east-1')
    with pytest.raises(ValueError):create_session(tmp_path/'sessions','../escape',db,'us-east-1')

def test_high_resolution_manifest_preserves_source_timestamps_and_excludes_backlog(db,tmp_path):
    state=create_session(tmp_path/'sessions','demo-test',db,'us-east-1');directory=tmp_path/'sessions/demo-test'
    ts=bucket(time.time())-9
    insert_request(db,2,ts);insert_request(db,3,ts+2)
    record_request(state,'trace-2',bucket(ts),'normal')
    with pytest.raises(ValueError):record_request(state,'historical',bucket(ts),'normal')
    writer=Writer()
    result=run_publisher(db,directory/'checkpoint.db','us-east-1',publish=True,cw=writer,
        environment=DEMO_ENVIRONMENT,storage_resolution=1,allowed_sequences=[2])
    assert result['published_requests']==1
    data=writer.calls[0]['MetricData']
    assert all(m['StorageResolution']==1 and m['Timestamp'].timestamp()==ts for m in data)
    assert all(any(x['Name']=='Environment' and x['Value']==DEMO_ENVIRONMENT for x in m['Dimensions']) for m in data)
    assert all('trace-' not in json.dumps(m,default=str) for m in data)
    assert run_publisher(db,directory/'checkpoint.db','us-east-1',publish=True,cw=writer,
        environment=DEMO_ENVIRONMENT,storage_resolution=1,allowed_sequences=[2])['status']=='no_new_requests'
    assert len(writer.calls)==1

def test_high_resolution_retains_ambiguous_publication_guard(db,tmp_path):
    create_session(tmp_path/'sessions','demo-test',db,'us-east-1');cp=tmp_path/'sessions/demo-test/checkpoint.db'
    insert_request(db,2,time.time()-1)
    kwargs=dict(publish=True,environment=DEMO_ENVIRONMENT,storage_resolution=1,allowed_sequences=[2])
    assert run_publisher(db,cp,'us-east-1',cw=Writer(EndpointConnectionError(endpoint_url='https://example.invalid')),**kwargs)['status']=='ambiguous_publication'
    retry=Writer()
    assert run_publisher(db,cp,'us-east-1',cw=retry,**kwargs)['status']=='ambiguous_publication'
    assert not retry.calls

def test_complete_phase_drain_is_bounded_and_does_not_replay(db,tmp_path):
    state=create_session(tmp_path/'sessions','demo-phase',db,'us-east-1');directory=tmp_path/'sessions/demo-phase'
    stamp=bucket(time.time())-20
    for seq in range(2,42):
        insert_request(db,seq,stamp+(seq-2)*.01)
        record_request(state,f'trace-{seq}',stamp,'normal')
    writer=Writer();publish_new(state,directory,cw=writer)
    assert len(writer.calls)==40 and sum(x['published_requests'] for x in state['publication'])==40
    assert len(state['publication'])==2 and all(x['request_count']==20 for x in state['publication'])
    publish_new(state,directory,cw=writer)
    assert len(writer.calls)==40

def test_standard_resolution_default_and_invalid_mode(db,tmp_path):
    writer=Writer();run_publisher(db,tmp_path/'standard.db','us-east-1',publish=True,cw=writer)
    assert all(m['StorageResolution']==60 for m in writer.calls[0]['MetricData'])
    with pytest.raises(ValueError):run_publisher(db,tmp_path/'invalid.db','us-east-1',storage_resolution=1)

def evidence():
    now=bucket(time.time())+1
    start=now-1-230
    state={'records':[],'region':'us-east-1'};cloud={'collection_complete':True,'buckets':[]}
    seq=2
    for index in range(15):
        stamp=iso(start+index*10);phase='normal' if index<10 else ('condition' if index<12 else 'followup')
        for j in range(4):
            state['records'].append({'sequence':seq,'timestamp':iso(start+index*10+1+2*j),'bucket_start':stamp,'phase':phase,
                'values':{'api_ms':320 if phase=='condition' else 120,'ledger_ms':206 if phase=='condition' else 6,'db_sum_ms':2,'db_samples':2},'metric_values':12});seq+=1
        cloud['buckets'].append({'timestamp':stamp,'complete':True,'expected_requests':4,
            'values':{'requests':4,'errors':0,'api_ms':320 if phase=='condition' else 120,'ledger_ms':206 if phase=='condition' else 6,'db_sum_ms':8}})
    return state,cloud,now

def test_legitimate_baseline_uses_ten_complete_windows_and_frozen_chronology():
    state,cloud,now=evidence();normal=freeze_reference(state,cloud,now)
    assert normal['request_count']==40 and len(normal['bucket_timestamps'])==10
    assert normal['features']['api_ms']['reference_windows']==6
    assert normal['features']['api_ms']['calibration_windows']==4
    assert normal['features']['api_ms']['median']==120
    assert normal['features']['db_sum_ms']['median']==2
    state['records'][1]['timestamp']=state['records'][0]['timestamp']
    with pytest.raises(ValueError):freeze_reference(state,cloud,now)

def test_baseline_rejects_missing_partial_nonconsecutive_or_stale_evidence():
    state,cloud,now=evidence()
    bad=copy.deepcopy(cloud);bad['buckets'][5]['complete']=False
    with pytest.raises(ValueError):freeze_reference(state,bad,now)
    bad=copy.deepcopy(cloud);bad['collection_complete']=False
    with pytest.raises(ValueError):freeze_reference(state,bad,now)
    with pytest.raises(ValueError):freeze_reference(state,cloud,now+300)
    state['records']=[r for r in state['records'] if r['bucket_start']!=cloud['buckets'][3]['timestamp']]
    with pytest.raises(ValueError):freeze_reference(state,cloud,now)

def test_two_real_complete_periods_detect_service_and_separate_measured_followup():
    state,cloud,now=evidence();baseline=freeze_reference(state,cloud,now)
    before=json.dumps(baseline,sort_keys=True)
    analysis=analyze_demo(cloud,baseline,now)
    assert analysis['status']=='abnormal_latency_detected' and analysis['affected_service']=='ledger-service'
    assert analysis['root_cause']=='not_established' and analysis['gnn_used'] is False
    assert len(analysis['detected_periods'])==2
    assert analysis['followup']['status']=='measured_return_toward_frozen_reference'
    assert json.dumps(baseline,sort_keys=True)==before
    assert trace_corroboration(state,analysis)['requests']==8

@pytest.mark.parametrize('defect',['missing','partial','nonconsecutive','stale','single','api_only','ledger_only'])
def test_defective_evidence_cannot_produce_persistent_anomaly(defect):
    state,cloud,now=evidence();baseline=freeze_reference(state,cloud,now)
    if defect=='missing':cloud['buckets'][10]['complete']=False
    if defect=='partial':cloud['collection_complete']=False
    if defect=='nonconsecutive':cloud['buckets'].pop(10)
    if defect=='stale':now+=300
    if defect=='single':cloud['buckets'][10]['values']['ledger_ms']=6
    if defect=='api_only':
        for b in cloud['buckets'][10:12]:b['values']['ledger_ms']=6
    if defect=='ledger_only':
        for b in cloud['buckets'][10:12]:b['values']['api_ms']=120
    assert analyze_demo(cloud,baseline,now)['status']!='abnormal_latency_detected'

class Reader:
    def __init__(self,stamp,partial=False,missing=False,duplicates=False):self.stamp=stamp;self.partial=partial;self.missing=missing;self.duplicates=duplicates;self.calls=[]
    def get_metric_data(self,**args):
        self.calls.append(args)
        values={'requests':4,'errors':0,'api_ms':20,'api_samples':4,'ledger_ms':5,'ledger_samples':4,'ledger_service_ms':7,'db_sum_ms':4,'db_samples':4}
        if self.duplicates:values['api_samples']=8
        return {'MetricDataResults':[{'Id':q['Id'],'StatusCode':'PartialData' if self.partial else 'Complete',
            'Timestamps':[] if self.missing and q['Id']=='ledger_samples' else [datetime.fromtimestamp(self.stamp,timezone.utc)],
            'Values':[] if self.missing and q['Id']=='ledger_samples' else [values[q['Id']]]} for q in args['MetricDataQueries']]}

def test_getmetricdata_uses_ten_seconds_and_demo_environment_only():
    stamp=bucket(time.time())-20
    state={'region':'us-east-1','records':[{'bucket_start':iso(stamp),'values':{'db_samples':1}} for _ in range(4)]}
    cw=Reader(stamp);result=collect_demo(state,cw=cw)
    assert result['buckets'][0]['complete'] and result['collection_complete']
    assert all(q['MetricStat']['Period']==10 for q in cw.calls[0]['MetricDataQueries'])
    assert all(any(d['Name']=='Environment' and d['Value']==DEMO_ENVIRONMENT for d in q['MetricStat']['Metric']['Dimensions']) for q in cw.calls[0]['MetricDataQueries'])
    for params in ({'partial':True},{'missing':True},{'duplicates':True}):
        assert not collect_demo(state,cw=Reader(stamp,**params))['buckets'][0]['complete']

def test_control_labels_are_not_detector_inputs():
    state,cloud,now=evidence();baseline=freeze_reference(state,cloud,now)
    expected=analyze_demo(cloud,baseline,now)
    cloud['experiment_label']={'target':'wrong-service','mechanism':'made-up'}
    state['experiment_target']='wrong-service'
    assert analyze_demo(cloud,baseline,now)==expected

def test_public_report_omits_local_source_identifiers():
    report=public_report({'database':'private-path','source_identity':'private-hash','records':[{'trace':'private'}],'status':'prepared'})
    assert report=={'status':'prepared'}

def test_cli_run_requires_all_confirmations(monkeypatch):
    import importlib.util
    root=Path(__file__).resolve().parents[1]
    spec=importlib.util.spec_from_file_location('aws_demo_cli',root/'scripts/aws_banking_demo.py');cli=importlib.util.module_from_spec(spec);spec.loader.exec_module(cli)
    monkeypatch.setattr('sys.argv',['aws_banking_demo.py','--run','--session','test-session'])
    with pytest.raises(SystemExit) as exc:cli.main()
    assert exc.value.code==2
