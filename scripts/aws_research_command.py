"""Run an approved setup/measurement script on the exact disposable instance."""
import argparse,json,time,sys
from datetime import datetime,timezone
from pathlib import Path
import boto3
sys.stdout.reconfigure(encoding='utf-8',errors='replace')

p=argparse.ArgumentParser();p.add_argument('--script',type=Path);p.add_argument('--name',required=True);p.add_argument('--timeout',type=int,default=900);p.add_argument('--command-id');a=p.parse_args()
root=Path(r'D:\BankingResearch\Reports');manifest=json.loads((root/'aws-active-experiment.json').read_text())
instance=manifest['instance_id']
assert instance=='i-0aefecc39f02f2727' and instance!=manifest['preserve_existing_instance']
s=boto3.Session(region_name='us-east-1');ssm=s.client('ssm')
if a.command_id:command=a.command_id
else:
    assert a.script and datetime.now(timezone.utc)<datetime.fromisoformat(manifest['terminate_by'])
    command=ssm.send_command(InstanceIds=[instance],DocumentName='AWS-RunShellScript',
        Parameters={'commands':[a.script.read_text(encoding='utf-8')],'executionTimeout':[str(a.timeout)]},
        TimeoutSeconds=60,Comment='Approved banking research: '+a.name)['Command']['CommandId']
    (root/(a.name+'.command.json')).write_text(json.dumps({'command_id':command,'instance_id':instance,'script':str(a.script),'sent_at':datetime.now(timezone.utc).isoformat()},indent=2))
    print('Command submitted:',command,flush=True)
while True:
    try:r=ssm.get_command_invocation(CommandId=command,InstanceId=instance)
    except ssm.exceptions.InvocationDoesNotExist:time.sleep(2);continue
    if r['Status'] not in ('Pending','InProgress','Delayed'):break
    time.sleep(5)
(root/(a.name+'.result.json')).write_text(json.dumps(r,default=str,indent=2))
print('Status:',r['Status']);print(r.get('StandardOutputContent',''));print(r.get('StandardErrorContent',''))
if r['Status']!='Success':raise SystemExit(1)
