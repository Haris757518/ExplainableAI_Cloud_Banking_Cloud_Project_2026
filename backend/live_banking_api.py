"""Loopback-only live view and fixed, guarded faculty demonstration controls."""
import json,time
from pathlib import Path
from fastapi import APIRouter,Request,HTTPException
from threading import Lock
from analysis.live_banking import assess

router=APIRouter(prefix='/api/live-banking',tags=['Live AWS demonstration'])
ROOT=Path(__file__).resolve().parents[1]/'results/runtime/live-aws'
PROJECT=Path(__file__).resolve().parents[1]
ACTION={}
ACTION_LOCK=Lock()

def aws(name):
    import boto3
    from botocore.config import Config
    return boto3.client(name,region_name='us-east-1',config=Config(connect_timeout=5,read_timeout=8,retries={'max_attempts':0}))

def guarded_instance():
    record=json.loads((ROOT/'session.json').read_text())
    if record['instance_id']=='i-03adf941e75dd8ac1':raise ValueError('Existing server excluded')
    if aws('sts').get_caller_identity()['Account']!=record['account']:raise ValueError('Account mismatch')
    vm=aws('ec2').describe_instances(InstanceIds=[record['instance_id']])['Reservations'][0]['Instances'][0]
    if vm['State']['Name']!='running' or {t['Key']:t['Value'] for t in vm.get('Tags',[])}.get('ResearchRun')!=record['run']:raise ValueError('Research instance unavailable')
    return record['instance_id']

@router.get('/action')
def action_status():
    with ACTION_LOCK:
        if ACTION.get('status')!='running':return dict(ACTION)
        try:
            value=aws('ssm').get_command_invocation(CommandId=ACTION['command_id'],InstanceId=ACTION['instance_id'])
            if value['Status'] in ('Pending','InProgress','Delayed'):return dict(ACTION)
            ACTION['status']='passed' if value['Status']=='Success' else 'failed'
            ACTION['message']='Complete' if ACTION['status']=='passed' else 'Could not complete. Check the AWS connection.'
            if ACTION['operation']=='verify' and ACTION['status']=='passed':
                proof=json.loads(value['StandardOutputContent'])
                passed=all(a['balance_matches'] and a['history_unique_ids'] for a in proof['accounts']) and proof['blocked_database_sessions']==0
                ACTION.update(status='passed' if passed else 'failed',message='Balances match the ledger. No duplicate history IDs or database blocking.' if passed else 'Integrity check failed.')
                (ROOT/'latest-ui-recovery.json').write_text(json.dumps(proof,indent=2))
            return dict(ACTION)
        except Exception:
            return {**ACTION,'message':'Waiting for AWS confirmation.'}

@router.post('/action/{operation}')
def run_action(operation:str,request:Request):
    if request.client.host not in ('127.0.0.1','::1') or request.headers.get('origin') not in ('http://127.0.0.1:8012','http://localhost:8012'):
        raise HTTPException(403,'Use the local demo dashboard.')
    if operation not in ('run','fault','fault-cpu','verify'):raise HTTPException(404,'Unknown demo control')
    action_status()
    with ACTION_LOCK:
        if ACTION.get('status')=='running':raise HTTPException(409,'Wait for the current action to finish.')
        try:
            instance=guarded_instance()
            if operation in ('fault','fault-cpu') and status().get('status')!='normal':raise ValueError('Wait for fresh normal readings before injecting the fault')
            if operation=='run' and status().get('status')=='anomaly':raise ValueError('Wait for the current anomaly to clear before collecting a new baseline')
            script={'run':'systemctl restart bank-live-agent.service\nsystemctl is-active bank-live-agent.service',
                    'fault':(PROJECT/'deploy/live_database_fault.sh').read_text(),
                    'fault-cpu':(PROJECT/'deploy/live_cpu_fault.sh').read_text(),
                    'verify':(PROJECT/'deploy/live_verify_recovery.sh').read_text()}[operation]
            command=aws('ssm').send_command(InstanceIds=[instance],DocumentName='AWS-RunShellScript',Parameters={'commands':[script],'executionTimeout':['100']})['Command']['CommandId']
            ACTION.clear();ACTION.update(requested_at=time.time(),status='running',operation=operation,command_id=command,instance_id=instance,message={'run':'Starting payments…','fault':'Database lock running for 30 seconds.','fault-cpu':'Reduced CPU running for 30 seconds.','verify':'Checking balances and ledger…'}[operation])
            with (ROOT/'ui-actions.jsonl').open('a') as journal:journal.write(json.dumps({**ACTION,'requested_at':time.time()})+'\n')
            return dict(ACTION)
        except ValueError as exc:raise HTTPException(409,str(exc)) from exc
        except Exception as exc:raise HTTPException(503,'AWS demo control unavailable. No success was assumed.') from exc

@router.get('/status')
def status():
    try:
        value=json.loads((ROOT/'snapshot.json').read_text())
        if value.get('source')!='executed-aws-bank-of-anthos':raise ValueError('Wrong source')
        now=time.time()
        if ACTION.get('operation')=='run' and value.get('started_at',0)<ACTION.get('requested_at',0)-2:
            return {'status':'warming_up','explanation':'Waiting for the new baseline.'}
        if not 0<=now-value['received_at']<=25:
            return {'status':'stale','explanation':'The AWS collector has stopped updating. Retained data is not live health.'}
        result=assess(value['requests'],value['baseline'],now=now)
        database=value.get('database',{})
        if result['status']=='anomaly' and 0<=now-database.get('timestamp',0)<=25 and database.get('blocked_sessions',0)>0:
            result['cause']=f"Database blocking is measured: {database['blocked_sessions']} sessions are waiting on other sessions. This supports database contention; the actor and underlying change are not established by these measurements."
        return {**result,'instance_id':value['instance_id'],'received_at':value['received_at'],'source':value['source'],'investigation':value.get('investigation')}
    except (OSError,ValueError,KeyError,TypeError):
        return {'status':'not_connected','explanation':'No verified live AWS collector is connected.'}
