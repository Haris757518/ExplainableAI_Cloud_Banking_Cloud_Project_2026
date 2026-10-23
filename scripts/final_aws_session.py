"""Bounded final verification on one tagged disposable Academy instance."""
import argparse,json,time,uuid,sys
from pathlib import Path
from datetime import datetime,timedelta,timezone
import boto3
sys.stdout.reconfigure(encoding='utf-8',errors='replace')

RECORD=Path(r'D:\BankingResearch\Reports\aws-final-validation.json')
def now():return datetime.now(timezone.utc)
def save(record):RECORD.write_text(json.dumps(record,indent=2,default=str))
def ec2():return boto3.client('ec2',region_name='us-east-1')
def load():return json.loads(RECORD.read_text())

def launch():
    if RECORD.exists():raise RuntimeError('Final-validation manifest already exists; inspect before retrying')
    old=json.loads(Path(r'D:\BankingResearch\Reports\aws-cleanup-verification.json').read_text())
    assert old['state']=='terminated' and old['root_volume_deleted']
    client=ec2();run='bank-final-'+now().strftime('%Y%m%dT%H%M%SZ')
    deadline=now()+timedelta(minutes=90)
    group=client.describe_security_groups(GroupIds=[old['security_group_id']])['SecurityGroups'][0]
    subnets=client.describe_subnets(Filters=[{'Name':'vpc-id','Values':[group['VpcId']]},{'Name':'default-for-az','Values':['true']}])['Subnets']
    subnet=sorted(subnets,key=lambda s:s['AvailabilityZone'])[0]
    image=client.describe_images(ImageIds=['ami-02a9cdd4e98bc3c78'])['Images'][0]
    assert image['OwnerId']=='099720109477' and 'ubuntu-noble-24.04' in image['Name']
    account=boto3.client('sts').get_caller_identity()['Account']
    record={'run':run,'instance_id':None,'deadline_utc':deadline.isoformat(),'created_at':now().isoformat(),'client_token':uuid.uuid4().hex,
            'status':'preparing','region':'us-east-1','account':account,'budget_usd':5,'maximum_runtime_minutes':90,
            'approval':'User authorized AWS if needed to finish the project; bounded by the prior $5 ceiling and below the approved two-hour runtime.',
            'preserve_instance':old['preserve_existing_instance'],'commands':[]}
    save(record)
    user_data='''#!/bin/bash
set -eu
cat >/etc/systemd/system/bank-final-deadline.service <<'UNIT'
[Service]
Type=oneshot
ExecStart=/sbin/poweroff
UNIT
cat >/etc/systemd/system/bank-final-deadline.timer <<'TIMER'
[Timer]
OnBootSec=80min
AccuracySec=1s
Unit=bank-final-deadline.service
[Install]
WantedBy=timers.target
TIMER
systemctl daemon-reload
systemctl enable --now bank-final-deadline.timer
'''
    tags=[{'Key':'Name','Value':'bank-final-verification'},{'Key':'ResearchRun','Value':run},{'Key':'ExpiresAtUTC','Value':deadline.isoformat()}]
    try:
        result=client.run_instances(ImageId=image['ImageId'],InstanceType='t3.large',MinCount=1,MaxCount=1,
            ClientToken=record['client_token'],KeyName=old['key_name'],IamInstanceProfile={'Name':'LabInstanceProfile'},
            NetworkInterfaces=[{'DeviceIndex':0,'SubnetId':subnet['SubnetId'],'Groups':[group['GroupId']],'AssociatePublicIpAddress':True,'DeleteOnTermination':True}],
            BlockDeviceMappings=[{'DeviceName':image['RootDeviceName'],'Ebs':{'VolumeSize':40,'VolumeType':'gp3','DeleteOnTermination':True}}],
            InstanceInitiatedShutdownBehavior='terminate',MetadataOptions={'HttpTokens':'required','HttpEndpoint':'enabled'},
            UserData=user_data,Monitoring={'Enabled':False},CreditSpecification={'CpuCredits':'unlimited'},
            TagSpecifications=[{'ResourceType':'instance','Tags':tags},{'ResourceType':'volume','Tags':tags}])
        vm=result['Instances'][0];record.update(instance_id=vm['InstanceId'],status='launched',launch_time=vm['LaunchTime'].isoformat())
        save(record);print(json.dumps({'instance_id':record['instance_id'],'deadline':record['deadline_utc']}),flush=True)
    except Exception as error:
        record.update(status='launch_failed',error=str(error));save(record);raise

def guard(record):
    assert record['instance_id'] and record['instance_id']!=record['preserve_instance']
    assert boto3.client('sts').get_caller_identity()['Account']==record['account']
    vm=ec2().describe_instances(InstanceIds=[record['instance_id']])['Reservations'][0]['Instances'][0]
    assert {t['Key']:t['Value'] for t in vm.get('Tags',[])}.get('ResearchRun')==record['run']
    return vm

def command(script,name,timeout=900):
    record=load();guard(record)
    assert now()<datetime.fromisoformat(record['deadline_utc'])
    client=boto3.client('ssm',region_name='us-east-1')
    command_id=client.send_command(InstanceIds=[record['instance_id']],DocumentName='AWS-RunShellScript',Parameters={'commands':[script],'executionTimeout':[str(timeout)]},TimeoutSeconds=60)['Command']['CommandId']
    record['commands'].append({'name':name,'id':command_id,'sent_at':now().isoformat()});save(record)
    print('Submitted',name,command_id,flush=True)
    while True:
        try:result=client.get_command_invocation(CommandId=command_id,InstanceId=record['instance_id'])
        except client.exceptions.InvocationDoesNotExist:time.sleep(2);continue
        if result['Status'] in ('Pending','InProgress','Delayed'):time.sleep(4);continue
        target=RECORD.parent/('final-'+name+'.json');target.write_text(json.dumps(result,default=str,indent=2))
        print(result['Status'],result.get('StandardOutputContent',''),result.get('StandardErrorContent',''),flush=True)
        if result['Status']!='Success':raise RuntimeError('Remote command failed: '+name)
        return result

def watchdog():
    while True:
        record=load()
        try:
            vm=guard(record)
            if vm['State']['Name'] in ('shutting-down','terminated'):return
            if now()>=datetime.fromisoformat(record['deadline_utc']):
                ec2().terminate_instances(InstanceIds=[record['instance_id']]);return
        except Exception as error:
            # Retry transient API/credential errors; guest deadline remains independent.
            (RECORD.parent/'final-watchdog-error.txt').write_text(type(error).__name__)
        time.sleep(20)

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['launch','command','watchdog']);parser.add_argument('--script',type=Path);parser.add_argument('--name');parser.add_argument('--timeout',type=int,default=900);a=parser.parse_args()
    if a.action=='launch':launch()
    elif a.action=='watchdog':watchdog()
    else:command(a.script.read_text(),a.name,a.timeout)
