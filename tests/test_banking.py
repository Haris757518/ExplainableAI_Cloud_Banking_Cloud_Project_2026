"""Isolated banking software tests; fixture data is never research telemetry."""
import uuid,json,time
from concurrent.futures import ThreadPoolExecutor
import pytest
from fastapi.testclient import TestClient
from banking import store
from banking.tracing import Span,sql,interval_union

@pytest.fixture(autouse=True)
def isolated_banking(tmp_path,monkeypatch):
    monkeypatch.setenv('BANKING_DATA_DIR',str(tmp_path/'banking'))
    store.initialize()

def plain(db,query,params=()):return db.execute(query,params)

def test_fictitious_seed_is_idempotent_and_money_is_integral():
    before=store.rows('SELECT * FROM accounts ORDER BY id',name='accounts.db');store.initialize()
    assert before==store.rows('SELECT * FROM accounts ORDER BY id',name='accounts.db')
    assert len(before)==2 and sum(a['balance_cents'] for a in before)==20000000

def test_atomic_transfer_duplicate_and_payload_conflict():
    first=store.transfer('test-a','test-b',50,'same-id',plain)
    second=store.transfer('test-a','test-b',50,'same-id',plain)
    assert not first['duplicate'] and second['duplicate']
    balances={r['id']:r['balance_cents'] for r in store.rows('SELECT * FROM accounts',name='accounts.db')}
    assert balances=={'test-a':9999950,'test-b':10000050}
    with pytest.raises(store.BankingError) as e:store.transfer('test-a','test-b',51,'same-id',plain)
    assert e.value.status==409

@pytest.mark.parametrize('amount',[0,-1,True,1.5,1000001])
def test_invalid_amounts_cannot_enter_ledger(amount):
    with pytest.raises(store.BankingError):store.transfer('test-a','test-b',amount,uuid.uuid4().hex,plain)
    assert not store.rows('SELECT * FROM transfers',name='accounts.db')

def test_insufficient_funds_rolls_back_everything():
    with store.connect('accounts.db') as db:db.execute("UPDATE accounts SET balance_cents=1 WHERE id='test-a'")
    with pytest.raises(store.BankingError):store.transfer('test-a','test-b',2,'unfunded',plain)
    assert not store.rows('SELECT * FROM transfers',name='accounts.db')
    assert store.rows("SELECT balance_cents FROM accounts WHERE id='test-a'",name='accounts.db')[0]['balance_cents']==1

def test_concurrent_debits_never_overdraw_and_preserve_total():
    with store.connect('accounts.db') as db:db.execute("UPDATE accounts SET balance_cents=9 WHERE id='test-a'")
    def attempt(i):
        try:store.transfer('test-a','test-b',1,str(i),plain);return True
        except store.BankingError:return False
    with ThreadPoolExecutor(max_workers=6) as pool:success=list(pool.map(attempt,range(18)))
    assert sum(success)==9
    balances=store.rows('SELECT balance_cents FROM accounts',name='accounts.db')
    assert all(r['balance_cents']>=0 for r in balances) and sum(r['balance_cents'] for r in balances)==10000009

def test_concurrent_same_id_is_executed_once():
    with ThreadPoolExecutor(max_workers=5) as pool:result=list(pool.map(lambda _:store.transfer('test-a','test-b',10,'once',plain),range(5)))
    assert sum(not r['duplicate'] for r in result)==1
    assert len(store.rows('SELECT * FROM transfers',name='accounts.db'))==1

def test_child_intervals_are_union_subtracted_not_double_counted():
    assert interval_union([(0,3),(1,4),(5,7)])==6
    with Span('ledger-service','server','transfer') as parent:
        with Span('banking-db','database','transfer'):time.sleep(.005)
    records=[json.loads(r['payload']) for r in store.rows('SELECT payload FROM spans')]
    assert len(records)==2 and 0<=parent.exclusive_ms<parent.duration_ms
    assert next(s for s in records if s['kind']=='database')['parent_id']==parent.id

def test_account_http_service_balance_history_and_real_sql_spans(monkeypatch):
    import banking.service as service
    monkeypatch.setattr(service,'ROLE','account')
    with TestClient(service.app) as client:
        for operation in ('balance','history'):
            r=client.post('/execute',json={'operation':operation},headers={'x-trace-id':uuid.uuid4().hex})
            assert r.status_code==200 and r.json()['service_duration_ms']>0
        assert client.post('/execute',json={'operation':'transfer'},headers={'x-trace-id':uuid.uuid4().hex}).status_code==400
    spans=[json.loads(r['payload']) for r in store.rows('SELECT payload FROM spans')]
    assert any(s['service']=='banking-db' and s['caller']=='account-service' for s in spans)
    assert all(s['duration_ms']>=0 for s in spans)

def test_ledger_service_transfer_and_trace_identity(monkeypatch):
    import banking.service as service
    monkeypatch.setattr(service,'ROLE','ledger');trace=uuid.uuid4().hex
    with TestClient(service.app) as client:
        r=client.post('/execute',json={'operation':'transfer','transfer_id':'http-transfer'},headers={'x-trace-id':trace})
    assert r.status_code==200 and r.json()['result']['amount_cents']==1
    spans=store.rows('SELECT * FROM spans')
    assert spans and {s['trace_id'] for s in spans}=={trace}
    assert any(s['kind']=='connection' for s in spans)

def test_control_is_bounded_expires_and_can_be_stopped(monkeypatch):
    now=[1000.];monkeypatch.setattr(store.time,'time',lambda:now[0])
    identifier=store.experiment_start(3,150);assert 0<store.active_delay()<=.15
    with pytest.raises(store.BankingError):store.experiment_start(3,150)
    now[0]=1004;assert store.active_delay()==0
    assert store.experiment_labels()[0]['status']=='expired'
    store.experiment_start(3,150);store.stop_experiments();assert store.active_delay()==0

def test_no_fault_is_started_by_database_initialization():
    assert store.experiment_labels()==[] and store.active_delay()==0

def test_stop_flag_survives_inflight_progress_update():
    from banking.workload import job_update,cancelled
    with store.connect('controls.db') as db:db.execute('INSERT INTO jobs VALUES(?,?,?,?)',('job','normal','stopping','{}'))
    job_update('job','running',{'requests':1})
    assert cancelled('job')

def measured_fixture():
    from common.research import DataSource,TelemetryCase,TelemetrySeries,TelemetryObservation,DependencyEdge
    series=[]
    for resource,metric,base,fault in [('banking-api','latency_ms',8,158),('banking-api','processing_ms',1,1),('ledger-service','latency_ms',7,157),('ledger-service','processing_ms',3,153),('banking-db','db_latency_ms',4,4)]:
        series.append(TelemetrySeries(id=resource+':'+metric,resource=resource,metric=metric,original_metric=metric,unit='milliseconds',observations=[TelemetryObservation(timestamp=i,value=base if i<90 else fault) for i in range(121)]))
    return TelemetryCase(id='isolated-unit-case',source=DataSource(id='banking-local',kind='academic_test_application',reference='isolated software fixture'),collection='fixture',series=series,edges=[DependencyEdge(source='banking-api',target='ledger-service',provenance='isolated fixture'),DependencyEdge(source='ledger-service',target='banking-db',provenance='isolated fixture')],provenance={'calibration_id':'test-calibration','baseline_end':60,'detector_threshold':3.5,'transaction_path':['banking-api','ledger-service','banking-db'],'operation':'transfer'})

def test_trace_localization_distinguishes_caller_symptom_and_own_processing(monkeypatch):
    from banking import analysis
    monkeypatch.setattr(analysis,'case_for',lambda *args,**kwargs:(measured_fixture(),[]))
    result,_=analysis.investigate('transfer',100,persist=False)
    assert result['candidates'][0]['resource']=='ledger-service'
    assert result['explanation']['diagnosis']['mechanism']=='application_processing_delay'
    assert result['recommendations'][0]['category']=='application_processing_delay'
    assert not result['cause_verified']
    assert result['investigation']['focused_metric_fields']<=result['investigation']['broad_metric_fields']

def test_inference_never_reads_control_labels(monkeypatch):
    from banking import analysis
    monkeypatch.setattr(analysis,'case_for',lambda *args,**kwargs:(measured_fixture(),[]))
    def forbidden():raise AssertionError('Labels entered inference')
    monkeypatch.setattr(store,'experiment_labels',forbidden)
    assert analysis.investigate('transfer',100,persist=False)[0]['explanation']['diagnosis']['mechanism']=='application_processing_delay'

def test_gnn_rejects_nonbanking_domain():
    from banking.graph_model import infer
    case=measured_fixture();case.source.id='alibaba'
    assert infer(case)['status']=='domain_not_compatible'

def test_snapshot_preserves_first_measurement_payload():
    payload={'id':'same','observation_time':1,'evidence':[1]};store.save_snapshot(payload,'transfer')
    store.save_snapshot({**payload,'evidence':[999]},'transfer')
    assert json.loads(store.rows('SELECT payload FROM snapshots')[0]['payload'])['evidence']==[1]

def test_local_controls_require_explicit_trigger_and_postgres_remains_blocked():
    from backend.main import app
    with TestClient(app) as client:
        assert client.post('/api/banking/experiments/application-delay',json={}).status_code==422
        assert client.post('/api/banking/experiments/database-lock').status_code==409
        assert client.post('/api/banking/workload',json={'confirm_local_test':True},headers={'Origin':'https://unrelated.example'}).status_code==403
    assert not store.experiment_labels()


def test_banking_adapter_excludes_future_values_and_control_labels():
    from banking.analysis import case_for
    for i in range(1,16):
        payload={'id':f'span-{i}','trace_id':f'trace-{i}','parent_id':None,'service':'banking-api','caller':None,'kind':'server','operation':'transfer','start':i-.01,'end':i,'duration_ms':10.,'exclusive_ms':2.,'status':200,'pid':0,'metrics':{}}
        store.insert_span(payload)
        with store.connect() as db:db.execute('INSERT INTO requests(trace_id,operation,ts,duration_ms,success,status) VALUES(?,?,?,?,?,?)',(f'trace-{i}','transfer',i,10.,1,200))
    cal={'id':'isolated','recording_start':1,'reference_end':5,'threshold':3.5}
    before,_=case_for('transfer',10,calibration=cal)
    with store.connect() as db:
        for i in range(11,16):
            row=json.loads(db.execute('SELECT payload FROM spans WHERE id=?',(f'span-{i}',)).fetchone()['payload']);row['duration_ms']=999999
            db.execute('UPDATE spans SET payload=? WHERE id=?',(json.dumps(row),f'span-{i}'))
    after,_=case_for('transfer',10,calibration=cal)
    assert before.model_dump()==after.model_dump()
    assert all(p.timestamp<=10 for s in after.series for p in s.observations)
    assert not {'fault','target','experiment_id','ground_truth','started'} & after.provenance.keys()

def test_recovery_requires_genuinely_new_observations(monkeypatch):
    from banking import analysis
    c=measured_fixture()
    for s in c.series:
        s.observations=[p for p in s.observations if p.timestamp<=100]
    monkeypatch.setattr(analysis,'case_for',lambda *args,**kwargs:(c,[]))
    incident={'observation_time':100,'explanation':{'detector_threshold':3.5},'evidence':[{'resource':'ledger-service','metric':'processing_ms','value':153,'reference':3,'scale':1,'score':150}]}
    assert analysis.recovery(incident,'transfer')['status']=='persists_or_insufficient_followup'
    from common.research import TelemetryObservation
    next(s for s in c.series if s.resource=='ledger-service' and s.metric=='processing_ms').observations.extend(TelemetryObservation(timestamp=i,value=3) for i in (101,102,103))
    assert analysis.recovery(incident,'transfer')['status']=='returned_toward_frozen_reference'

def test_banking_model_cannot_use_future_training_prefix(monkeypatch):
    from banking import graph_model
    c=measured_fixture()
    for name in ('identity','graph'):(store.root()/f'test-calibration-{name}.pt').write_bytes(b'isolated-test-placeholder')
    monkeypatch.setattr(graph_model.torch,'load',lambda *a,**kw:{'train_end':1000})
    assert graph_model.infer(c)['status']=='prefix_precedes_training_completion'

def test_without_frozen_baseline_no_operational_diagnosis_is_claimed(monkeypatch):
    from banking import analysis
    c=measured_fixture();c.provenance['calibration_id']=None
    monkeypatch.setattr(analysis,'case_for',lambda *args,**kwargs:(c,[]))
    result,_=analysis.investigate('transfer',100,persist=False)
    assert result['status']=='insufficient_evidence' and not result['candidates'] and not result['recommendations']


def test_frozen_report_survives_windows_newlines_but_detects_tampering(tmp_path,monkeypatch):
    import hashlib
    from backend import banking_api
    from fastapi import HTTPException
    project=tmp_path/'report-project';report=project/'results/banking/isolated/report.json';report.parent.mkdir(parents=True)
    canonical=b'{"summary":{"cases":3}}\n';report.write_bytes(canonical.replace(b'\n',b'\r\n'))
    (project/'results/banking/FINAL.json').write_text(json.dumps({'report':'results/banking/isolated/report.json','sha256':hashlib.sha256(canonical).hexdigest()}))
    monkeypatch.setattr(banking_api,'__file__',str(project/'backend/banking_api.py'))
    assert banking_api.banking_results()['report']['summary']['cases']==3
    report.write_bytes(b'{"summary":{"cases":99}}\n')
    with pytest.raises(HTTPException) as error:banking_api.banking_results()
    assert error.value.status_code==424
