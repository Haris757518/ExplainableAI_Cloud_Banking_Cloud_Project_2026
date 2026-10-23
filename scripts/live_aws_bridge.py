"""Read one explicitly tagged AWS research instance through SSM into the live UI.

No provisioning or fault injection. The deployment manifest must be created by
the approved launch procedure; unrelated existing instances are refused.
"""
import argparse,json,sys,time
from pathlib import Path
import boto3
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--manifest',type=Path,required=True);args=parser.parse_args()
    record=json.loads(args.manifest.read_text());instance=record['instance_id'];run=record['run']
    if instance=='i-03adf941e75dd8ac1':raise ValueError('Existing payment server is excluded')
    ec2=boto3.client('ec2',region_name='us-east-1');ssm=boto3.client('ssm',region_name='us-east-1')
    vm=ec2.describe_instances(InstanceIds=[instance])['Reservations'][0]['Instances'][0]
    if {t['Key']:t['Value'] for t in vm.get('Tags',[])}.get('ResearchRun')!=run:raise ValueError('Research tag mismatch')
    destination=ROOT/'results/runtime/live-aws';destination.mkdir(parents=True,exist_ok=True)
    last_finding=None;last_run=None
    while True:
        try:
            command=ssm.send_command(InstanceIds=[instance],DocumentName='AWS-RunShellScript',Parameters={'commands':["python3 -c \"import json; p=json.load(open('/opt/banking-research/live/snapshot.json')); p['requests']=p['requests'][-30:]; print(json.dumps(p,separators=(',',':')))\""],'executionTimeout':['15']})['Command']['CommandId']
            until=time.monotonic()+20
            while time.monotonic()<until:
                try:response=ssm.get_command_invocation(CommandId=command,InstanceId=instance)
                except ssm.exceptions.InvocationDoesNotExist:time.sleep(1);continue
                if response['Status'] in ('Pending','Delayed','InProgress'):time.sleep(1);continue
                if response['Status']!='Success':raise RuntimeError('AWS live snapshot collection failed')
                value=json.loads(response['StandardOutputContent'])
                if value.get('source')!='executed-aws-bank-of-anthos':raise ValueError('Invalid measurement source')
                value.update(instance_id=instance,received_at=time.time())
                from analysis.live_banking import assess
                from analysis.live_investigation import investigate_live
                if last_run!=value['started_at']:last_finding=None;last_run=value['started_at']
                if assess(value['requests'],value['baseline'],now=time.time())['status']=='anomaly':
                    candidate=investigate_live(value,now=time.time())
                    if last_finding is None or candidate['probe_xai']['causes']:last_finding=candidate
                value['investigation']=last_finding
                temporary=destination/'snapshot.partial';temporary.write_text(json.dumps(value));temporary.replace(destination/'snapshot.json')
                with (destination/'received-snapshots.jsonl').open('a') as journal:journal.write(json.dumps(value)+'\n')
                print('Received AWS measurements',instance,len(value['requests']),flush=True);break
            else:raise TimeoutError('Live SSM collection timed out; dashboard will mark data stale')
        except Exception as error:
            print('Live connection interrupted:',type(error).__name__,flush=True)
        time.sleep(5)

if __name__=='__main__':main()
