"""Local backup deadline for exactly the tagged, approved research instance."""
from datetime import datetime,timezone
import json,time
from pathlib import Path
import boto3

p=Path(r'D:\BankingResearch\Reports\aws-active-experiment.json')
r=json.loads(p.read_text());instance=r['instance_id']
if not instance or instance==r['preserve_existing_instance']:raise SystemExit('No valid disposable instance')
ec2=boto3.client('ec2',region_name=r['region'])
deadline=datetime.fromisoformat(r['terminate_by'])
receipt=p.with_name('aws-termination-watchdog.json')
while True:
    data=ec2.describe_instances(InstanceIds=[instance])['Reservations'][0]['Instances'][0]
    assert {t['Key']:t['Value'] for t in data.get('Tags',[])}.get('ResearchRun')==r['run']
    state=data['State']['Name']
    if state in ('terminated','shutting-down'):
        receipt.write_text(json.dumps({'instance_id':instance,'observed_state':state,'at':datetime.now(timezone.utc).isoformat()}));break
    if datetime.now(timezone.utc)>=deadline:
        ec2.terminate_instances(InstanceIds=[instance])
        receipt.write_text(json.dumps({'instance_id':instance,'action':'terminate_instances','at':datetime.now(timezone.utc).isoformat()}));break
    time.sleep(min(30,max(1,(deadline-datetime.now(timezone.utc)).total_seconds())))
