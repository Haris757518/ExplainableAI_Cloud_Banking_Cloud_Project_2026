"""Explicit opt-in, bounded high-resolution local banking / AWS demonstration."""
from pathlib import Path
import argparse,hashlib,json,math,os,sys,time,uuid
from contextlib import closing
import httpx

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from common.config import get_settings
from aws.banking_publisher import connect_readonly,safe_error
from aws.banking_demo import (create_session,load_session,session_dir,atomic_json,iso,bucket,
    record_request,validate_source_windows,publish_new,collect_demo,freeze_reference,
    analyze_demo,trace_corroboration,public_report,MAX_REQUESTS,SAMPLES,PERIOD)

DEMO_ROOT=ROOT/'results/runtime/aws-demo'

def save(directory,state):
    state['observed_request_totals']={phase:sum(r['phase']==phase for r in state['records']) for phase in ('normal','condition','followup')}
    state['published_request_total']=sum(x['published_requests'] for x in state['publication'])
    state['published_metric_total']=sum(x['published_metric_values'] for x in state['publication'])
    atomic_json(directory/'session.json',state)
    atomic_json(directory/'report.json',public_report(state))
    # This pointer is for the optional dashboard only; it never selects research results.
    atomic_json(DEMO_ROOT/'LATEST.json',{'session':state['session']})

def wait_until(stamp):
    while time.time()<stamp:time.sleep(max(0,min(.25,stamp-time.time())))

def preflight(state,url):
    from aws.discovery import AWSDiscovery
    identity=AWSDiscovery(state['region'],get_settings().profile).status()
    if not identity['connected']:
        raise ValueError('AWS authentication unavailable before any transfers: '+str(identity.get('error')))
    if url not in ('http://127.0.0.1:8000','http://localhost:8000'):
        raise ValueError('Use the existing local banking gateway on port 8000; remote or review gateways are not demo transfer targets.')
    if Path(state['database']).resolve()!=Path(os.environ.get('BANKING_DATA_DIR',ROOT/'results/runtime/banking')).resolve()/'telemetry.db':
        raise ValueError('Telemetry and the existing banking control directory must match.')
    with httpx.Client(timeout=5,trust_env=False) as client:
        health=client.get(url+'/api/health');health.raise_for_status()
        ledger=client.get('http://127.0.0.1:8102/health');ledger.raise_for_status()
        if ledger.json().get('role')!='ledger' or ledger.json().get('cloud') is not False:
            raise ValueError('A verified local academic Ledger Service is required.')
    directory=Path(state['database']).parent
    with closing(connect_readonly(directory/'controls.db')) as db:
        if db.execute('SELECT 1 FROM experiments WHERE ended IS NULL AND expires>?',(time.time(),)).fetchone():
            raise ValueError('Another local condition is active; no demo was started.')
        if db.execute("SELECT 1 FROM jobs WHERE status IN ('running','stopping')").fetchone():
            raise ValueError('Another banking workload is active; no demo was started.')

def collect_windows(state,directory,phase,start,count,url,profile):
    with httpx.Client(timeout=4,trust_env=False) as client:
        for offset in range(count):
            window=start+PERIOD*offset
            for position in range(SAMPLES):
                if len(state['records'])>=MAX_REQUESTS:raise ValueError('Maximum sixty demo transfers reached.')
                previous=__import__('datetime').datetime.fromisoformat(state['records'][-1]['timestamp']).timestamp() if state['records'] else 0
                wait_until(max(window+1+2*position,previous+.6))
                if time.time()>window+8.2:raise ValueError('Scheduling deadline missed; no partial bucket was accepted.')
                index=len(state['records'])
                account,recipient=('test-a','test-b') if index%2==0 else ('test-b','test-a')
                body={'operation':'transfer','account':account,'recipient':recipient,'amount_cents':1,
                      'transfer_id':'aws-demo-'+uuid.uuid4().hex}
                state['attempted_requests']=state.get('attempted_requests',0)+1
                save(directory,state)
                response=client.post(url+'/api/banking/execute',json=body)
                response.raise_for_status();payload=response.json()
                if not payload.get('success'):raise ValueError('Measured test transfer did not succeed.')
                # Abort if this API writes to a different source: never copy or invent rows.
                record_request(state,payload['trace_id'],window,phase)
                save(directory,state)
            wait_until(window+PERIOD+.05)
            state['windows']=[w for w in state['windows'] if w.get('phase')!=phase]+[
                {**w,'phase':phase} for w in validate_source_windows(state,phase)]
            save(directory,state)
            print(f'{phase}: {offset+1}/{count} complete measured windows; {len(state["records"])} requests',flush=True)

def read_until(state,directory,profile,require_baseline=False):
    for attempt in range(1,7):
        cloud=collect_demo(state,profile)
        state['cloudwatch']=cloud
        state['collection_attempt']=attempt
        if require_baseline:
            try:
                baseline=freeze_reference(state,cloud)
                target=directory/'baseline.json'
                if target.exists():raise ValueError('Frozen baseline already exists; it must not be overwritten.')
                # Frozen evidence is written before any controlled condition is started.
                atomic_json(target,baseline);state['baseline']=baseline
                state['status']='baseline_frozen';save(directory,state);return True
            except ValueError as exc:
                state['baseline_pending_reason']=str(exc)
        else:
            state['analysis']=analyze_demo(cloud,state.get('baseline'))
            state['local_trace_corroboration']=trace_corroboration(state,state['analysis'])
            if all(b['complete'] for b in cloud['buckets']) and cloud['collection_complete']:
                save(directory,state);return True
        save(directory,state)
        if cloud['errors']:
            # Permission/session problems should not be retried for a minute.
            codes={e['code'] for e in cloud['errors']}
            if codes & {'AccessDenied','AccessDeniedException','ExpiredToken','InvalidClientTokenId','NoCredentialsError'}:return False
        if attempt<6:
            print('Waiting for complete CloudWatch observations; no republishing.',flush=True)
            time.sleep(10)
    return False

def stop_owned(condition_id,database):
    if not condition_id:return
    with closing(connect_readonly(Path(database).parent/'controls.db')) as db:
        active=db.execute('SELECT id,expires FROM experiments WHERE ended IS NULL AND expires>?',(time.time(),)).fetchall()
    # Reuse the existing stop operation only while this run owns the active condition.
    if len(active)==1 and active[0]['id']==condition_id and active[0]['expires']>time.time()+.5:
        from banking import store
        store.stop_experiments()

def run(state,directory,url,profile):
    preflight(state,url)
    state['note']='Explicitly authorized measured session; actual progress and limitations are recorded below.'
    if state['status']=='prepared':
        state['status']='collecting_baseline';save(directory,state)
        start=bucket(time.time())+PERIOD
        collect_windows(state,directory,'normal',start,10,url,profile)
        publish_new(state,directory,profile)
        state['status']='baseline_collected';save(directory,state)
    if state['status'] in ('baseline_collected','awaiting_baseline_cloudwatch'):
        if not read_until(state,directory,profile,require_baseline=True):
            state['status']='awaiting_baseline_cloudwatch';save(directory,state);return
    if state['status']!='baseline_frozen':
        raise ValueError('This session cannot repeat transfers. Use --refresh for evidence; start a new explicitly authorized session if needed.')
    baseline=state['baseline']
    if time.time()-__import__('datetime').datetime.fromisoformat(baseline['end']).timestamp()>180:
        raise ValueError('Frozen baseline is stale for a new live condition. Create a new session rather than rewriting timestamps.')
    baseline_hash=hashlib.sha256((directory/'baseline.json').read_bytes()).hexdigest()
    state['baseline_file_sha256_before_condition']=baseline_hash
    from banking import store
    condition=None
    # Start one second before a future aligned window, then record two complete windows.
    start=bucket(time.time())+2*PERIOD
    wait_until(start-1)
    try:
        condition=store.experiment_start(duration=30,delay_ms=200)
        # Labels stay in a separate audit file and are not passed to the predictor.
        atomic_json(directory/'control_audit.json',{'id':condition,'started_at':iso(time.time()),'duration_limit_seconds':30,'delay_ms':200,
                    'scope':'Explicitly authorized local academic Ledger Service only; no AWS resource fault.'})
        state['status']='collecting_condition';save(directory,state)
        collect_windows(state,directory,'condition',start,2,url,profile)
    finally:
        stop_owned(condition,state['database'])
    state['status']='collecting_followup';save(directory,state)
    follow_start=bucket(time.time())
    if time.time()>follow_start+1:follow_start+=PERIOD
    collect_windows(state,directory,'followup',follow_start,3,url,profile)
    publish_new(state,directory,profile)
    assert hashlib.sha256((directory/'baseline.json').read_bytes()).hexdigest()==baseline_hash,'Frozen reference changed.'
    state['status']='awaiting_cloudwatch_verification';save(directory,state)
    complete=read_until(state,directory,profile)
    state['status']='completed' if complete else 'awaiting_cloudwatch_verification'
    state['verified_at']=iso(time.time())
    state['observed_request_totals']={phase:sum(r['phase']==phase for r in state['records']) for phase in ('normal','condition','followup')}
    state['published_request_total']=sum(x['published_requests'] for x in state['publication'])
    state['published_metric_total']=sum(x['published_metric_values'] for x in state['publication'])
    state['note']='All readings are observed; no experiment label is an input to the AWS detector. CloudWatch storage does not establish AWS banking hosting.'
    save(directory,state)

def main():
    settings=get_settings()
    parser=argparse.ArgumentParser(description=__doc__)
    mode=parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--prepare',action='store_true');mode.add_argument('--run',action='store_true');mode.add_argument('--refresh',action='store_true')
    parser.add_argument('--session',required=True)
    parser.add_argument('--database',type=Path,default=Path(os.environ.get('BANKING_DATA_DIR',ROOT/'results/runtime/banking'))/'telemetry.db')
    parser.add_argument('--region',default=settings.aws_region)
    parser.add_argument('--base-url',default='http://127.0.0.1:8000')
    parser.add_argument('--confirm-test-transfers',action='store_true')
    parser.add_argument('--confirm-publish',action='store_true')
    parser.add_argument('--confirm-local-delay',action='store_true')
    args=parser.parse_args()
    if args.run and not (args.confirm_test_transfers and args.confirm_publish and args.confirm_local_delay):
        parser.error('--run requires all three explicit confirmations: test transfers, chargeable metrics, and bounded local delay.')
    directory=session_dir(DEMO_ROOT,args.session)
    if args.prepare:
        state=create_session(DEMO_ROOT,args.session,args.database,args.region);save(directory,state)
        print(json.dumps(public_report(state),indent=2));return 0
    DEMO_ROOT.mkdir(parents=True,exist_ok=True)
    lock=DEMO_ROOT/'active.lock'
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError:
        print(json.dumps({'status':'blocked','reason':'Another demo is active or interrupted. Inspect existing evidence before removing a stale lock.'}));return 2
    state=None
    try:
        os.write(fd,str(os.getpid()).encode());state=load_session(directory)
        if args.refresh:
            state['cloudwatch']=collect_demo(state,settings.profile)
            state['analysis']=analyze_demo(state['cloudwatch'],state.get('baseline'))
            state['local_trace_corroboration']=trace_corroboration(state,state['analysis']);save(directory,state)
        else:
            run(state,directory,args.base_url,settings.profile)
        print(json.dumps({'session':args.session,'status':state['status'],'analysis':state['analysis'],'report':str(directory/'report.json')},indent=2))
        return 0 if state['status']=='completed' else 2
    except (Exception,KeyboardInterrupt) as exc:
        if state is not None:
            state['status']='blocked_or_interrupted';state['blocker']={'code':safe_error(exc),'reason':str(exc)[:250]}
            state['note']='Execution stopped. Only observed requests and confirmed publication are counted; no completed demonstration is asserted.'
            save(directory,state)
        print(json.dumps({'status':'blocked_or_interrupted','reason':str(exc)[:250]}));return 2
    finally:
        os.close(fd);lock.unlink()

if __name__=='__main__':raise SystemExit(main())
