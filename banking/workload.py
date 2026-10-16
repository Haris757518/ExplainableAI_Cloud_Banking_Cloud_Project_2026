"""Explicit, bounded local workload jobs. No workload or fault starts on import."""
import time,uuid,json,threading,random,platform,os
import httpx
from banking import store

def job_update(identifier,status,payload):
    with store.connect('controls.db') as db:db.execute("UPDATE jobs SET status=CASE WHEN status='stopping' AND ?='running' THEN 'stopping' ELSE ? END,payload=? WHERE id=?",(status,status,json.dumps(payload),identifier))

def cancelled(identifier):
    rows=store.rows('SELECT status FROM jobs WHERE id=?',(identifier,),name='controls.db')
    return not rows or rows[0]['status']=='stopping'

def launch(kind,per_operation=90,duration=12,delay_ms=150):
    store.initialize();identifier=uuid.uuid4().hex
    with store.connect('controls.db') as db:
        db.execute('BEGIN IMMEDIATE')
        existing=db.execute("SELECT payload FROM jobs WHERE status IN ('running','stopping')").fetchall()
        for old in existing:
            if json.loads(old['payload']).get('owner_pid')!=os.getpid():db.execute("UPDATE jobs SET status='stopped' WHERE payload=?",(old['payload'],))
        if db.execute("SELECT 1 FROM jobs WHERE status IN ('running','stopping')").fetchone():db.rollback();raise store.BankingError(409,'Another local workload is running. Stop or await it first.')
        db.execute('INSERT INTO jobs VALUES(?,?,?,?)',(identifier,kind,'running',json.dumps({'started':time.time(),'requests':0,'owner_pid':os.getpid()})));db.commit()
    thread=threading.Thread(target=run,args=(identifier,kind,per_operation,duration,delay_ms),daemon=True);thread.start();return identifier

def run(identifier,kind,per_operation,duration,delay_ms):
    info={'owner_pid':os.getpid(),'started':time.time(),'requests':0,'successes':0,'seed':42,'concurrency':1,'machine':{'os':platform.platform(),'python':platform.python_version(),'logical_cpus':os.cpu_count()},'measurement':'Actual loopback HTTP requests; fictitious test funds only.'}
    fault=None;traces=[];checkpoint=None;rng=random.Random(42);direction=rng.randrange(2)
    def send(client,operation,index):
        body={'operation':operation,'account':'test-a' if (index+direction)%2==0 else 'test-b','recipient':'test-b' if (index+direction)%2==0 else 'test-a','amount_cents':1,'transfer_id':'workload-'+uuid.uuid4().hex}
        start=time.perf_counter();response=client.post('http://127.0.0.1:8000/api/banking/execute',json=body);elapsed=(time.perf_counter()-start)*1000
        response.raise_for_status();data=response.json();trace=data['trace_id'];traces.append(trace)
        with store.connect() as db:db.execute('UPDATE requests SET client_latency_ms=? WHERE trace_id=?',(elapsed,trace))
        info['requests']+=1;info['successes']+=int(data['success']);job_update(identifier,'running',info)
    try:
        with httpx.Client(timeout=10) as client:
            if kind=='normal':
                if store.experiment_labels() and any(e['status']=='active' for e in store.experiment_labels()):raise ValueError('Stop the active local condition before collecting a normal baseline.')
                for i in range(per_operation):
                    for operation in ('balance','transfer','history'):
                        if cancelled(identifier):raise InterruptedError('Workload stopped by operator.')
                        send(client,operation,i)
                from banking.analysis import freeze_baseline
                info['baseline']=freeze_baseline(traces)
            else:
                if store.calibration() is None:raise ValueError('Collect and freeze a normal baseline before an experiment.')
                fault=store.experiment_start(duration,delay_ms);info['experiment_id']=fault;job_update(identifier,'running',info)
                stop_at=time.monotonic()+duration;i=0
                while time.monotonic()<stop_at and i<200:
                    if cancelled(identifier):raise InterruptedError('Experiment stopped by operator.')
                    send(client,'transfer',i);i+=1
                    if i==10:
                        from banking.analysis import investigate
                        checkpoint,_=investigate('transfer');info['prediction_id']=checkpoint['id'];job_update(identifier,'running',info)
                store.stop_experiments()
                if checkpoint is None:
                    from banking.analysis import investigate
                    checkpoint,_=investigate('transfer');info['prediction_id']=checkpoint['id']
                # Subsequent measurements are real requests after the condition ended.
                for j in range(15):send(client,'transfer',j)
                from banking.analysis import recovery
                info['recovery']=recovery(checkpoint,'transfer')
        info['finished']=time.time();job_update(identifier,'completed',info)
    except Exception as exc:
        info['finished']=time.time();info['error']=str(exc);job_update(identifier,'stopped' if isinstance(exc,InterruptedError) else 'failed',info)
    finally:
        if fault:store.stop_experiments()

def verify(identifier):
    jobs=store.rows('SELECT * FROM jobs WHERE id=?',(identifier,),name='controls.db')
    if not jobs:raise store.BankingError(404,'Local job not found.')
    job=jobs[0];info=json.loads(job['payload'])
    if job['status']!='completed':raise store.BankingError(409,'Complete the measured experiment before revealing its annotation.')
    if 'prediction_id' not in info:raise store.BankingError(409,'This normal workload has no controlled fault annotation.')
    snapshots=store.rows('SELECT payload FROM snapshots WHERE id=?',(info['prediction_id'],))
    if not snapshots:raise store.BankingError(424,'Prediction snapshot unavailable.')
    prediction=json.loads(snapshots[0]['payload']) # frozen prediction read before independent labels
    labels=next((e for e in store.experiment_labels() if e['id']==info['experiment_id']),None)
    if labels is None:raise store.BankingError(424,'Independent control annotation unavailable.')
    order=[c['resource'] for c in prediction['candidates']];mechanism=prediction['explanation']['diagnosis']['mechanism']
    return {'prediction_id':prediction['id'],'prediction_timestamp':prediction['observation_time'],'detection_status':prediction['status'],'service_ranking':order,'service_top3_match':labels['target'] in order[:3],'predicted_service':order[0] if order else None,'predicted_mechanism':mechanism,'published_control':labels,'service_match':bool(order and order[0]==labels['target']),'mechanism_match':mechanism==labels['kind'],'abstained':mechanism=='unknown','recovery':info.get('recovery'),'graph_evidence':prediction['explanation'].get('banking_gnn'),'tc_cfao':prediction['investigation'],'verification_scope':'Independent local controlled-experiment annotation; not proof of production causality.'}
