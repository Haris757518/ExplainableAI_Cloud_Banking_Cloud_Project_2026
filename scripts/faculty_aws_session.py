"""Approved $5 / 120 total running minutes faculty demonstration, exact-instance guard."""
import argparse,json,time,uuid,sys
from datetime import datetime,timezone
from pathlib import Path
import boto3
ROOT=Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
RECORD=ROOT/'results/runtime/live-aws/session.json'
def save(r):RECORD.parent.mkdir(parents=True,exist_ok=True);RECORD.write_text(json.dumps(r,indent=2,default=str))
def client(name):return boto3.client(name,region_name='us-east-1')
def guard(r):
    assert client('sts').get_caller_identity()['Account']==r['account']
    if r['instance_id']=='i-03adf941e75dd8ac1':raise ValueError('Existing server excluded')
    vm=client('ec2').describe_instances(InstanceIds=[r['instance_id']])['Reservations'][0]['Instances'][0]
    assert {t['Key']:t['Value'] for t in vm.get('Tags',[])}.get('ResearchRun')==r['run']
    return vm
def launch():
    if RECORD.exists():raise RuntimeError('Existing launch manifest: reconcile before retrying')
    ec2=client('ec2');account=client('sts').get_caller_identity()['Account']
    vpc=ec2.describe_vpcs(Filters=[{'Name':'is-default','Values':['true']}])['Vpcs'][0]
    subnet=sorted(ec2.describe_subnets(Filters=[{'Name':'vpc-id','Values':[vpc['VpcId']]},{'Name':'default-for-az','Values':['true']}])['Subnets'],key=lambda s:s['AvailabilityZone'])[0]
    image=ec2.describe_images(ImageIds=['ami-02a9cdd4e98bc3c78'])['Images'][0]
    assert image['OwnerId']=='099720109477' and 'ubuntu-noble-24.04' in image['Name']
    run='faculty-live-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    r={'run':run,'account':account,'instance_id':None,'client_token':uuid.uuid4().hex,'budget_usd':5,'total_running_minutes':120,'status':'preparing','approval':'User approved $5/two hours, rehearsal now, stop and restart for review; existing payment server excluded.'};save(r)
    tags=[{'Key':'Name','Value':'bank-faculty-live'},{'Key':'ResearchRun','Value':run}]
    sg=ec2.create_security_group(GroupName=run,Description='Private faculty banking demo; SSM only, no inbound ports',VpcId=vpc['VpcId'],TagSpecifications=[{'ResourceType':'security-group','Tags':tags}])['GroupId'];r['security_group_id']=sg;save(r)
    userdata='''#!/bin/bash
set -eu
mkdir -p /opt/banking-research
echo 35 > /opt/banking-research/boot-cap-minutes
cat > /opt/banking-research/runtime-guard.py <<'PY'
import pathlib,time,subprocess
p=pathlib.Path('/opt/banking-research/total-running-seconds')
total=float(p.read_text()) if p.exists() else 0
cap=float(pathlib.Path('/opt/banking-research/boot-cap-minutes').read_text())*60
started=time.monotonic();last=started
while True:
 time.sleep(5);now=time.monotonic();total+=now-last;last=now;p.write_text(str(total))
 if total>=6900 or now-started>=cap:
  subprocess.run(['/sbin/poweroff']);break
PY
cat > /etc/systemd/system/bank-runtime-guard.service <<'UNIT'
[Unit]
Description=Bound aggregate approved research runtime
After=local-fs.target
[Service]
ExecStart=/usr/bin/python3 /opt/banking-research/runtime-guard.py
Restart=on-failure
[Install]
WantedBy=multi-user.target
UNIT
systemctl daemon-reload
systemctl enable --now bank-runtime-guard.service
snap start amazon-ssm-agent || true
'''
    result=ec2.run_instances(ImageId=image['ImageId'],InstanceType='t3.large',MinCount=1,MaxCount=1,ClientToken=r['client_token'],IamInstanceProfile={'Name':'LabInstanceProfile'},NetworkInterfaces=[{'DeviceIndex':0,'SubnetId':subnet['SubnetId'],'Groups':[sg],'AssociatePublicIpAddress':True,'DeleteOnTermination':True}],BlockDeviceMappings=[{'DeviceName':image['RootDeviceName'],'Ebs':{'VolumeSize':40,'VolumeType':'gp3','DeleteOnTermination':True}}],InstanceInitiatedShutdownBehavior='stop',MetadataOptions={'HttpTokens':'required','HttpEndpoint':'enabled'},CreditSpecification={'CpuCredits':'standard'},UserData=userdata,TagSpecifications=[{'ResourceType':'instance','Tags':tags},{'ResourceType':'volume','Tags':tags}])
    vm=result['Instances'][0];r.update(instance_id=vm['InstanceId'],status='launched',launch_time=vm['LaunchTime'].isoformat());save(r);print(json.dumps(r))
def command(path,name,timeout):
    r=json.loads(RECORD.read_text());guard(r)
    ssm=client('ssm');cid=ssm.send_command(InstanceIds=[r['instance_id']],DocumentName='AWS-RunShellScript',Parameters={'commands':[path.read_text()],'executionTimeout':[str(timeout)]})['Command']['CommandId']
    r.setdefault('commands',[]).append({'id':cid,'name':name});save(r);print('Submitted',cid,flush=True)
    end=time.monotonic()+timeout+60
    while time.monotonic()<end:
        try:response=ssm.get_command_invocation(CommandId=cid,InstanceId=r['instance_id'])
        except ssm.exceptions.InvocationDoesNotExist:time.sleep(2);continue
        if response['Status'] in ('Pending','InProgress','Delayed'):time.sleep(3);continue
        (RECORD.parent/(name+'.json')).write_text(json.dumps(response,default=str))
        print(response['Status'],response.get('StandardOutputContent',''),response.get('StandardErrorContent',''),flush=True)
        if response['Status']!='Success':raise RuntimeError('Remote command failed')
        return
    raise TimeoutError('Remote status pending; inspect stored command ID before retry')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('action',choices=['launch','command','stop','start','terminate']);p.add_argument('--script',type=Path);p.add_argument('--name',default='command');p.add_argument('--timeout',type=int,default=900);a=p.parse_args()
    if a.action=='launch':launch()
    elif a.action=='command':command(a.script,a.name,a.timeout)
    else:
        r=json.loads(RECORD.read_text());vm=guard(r);ec2=client('ec2')
        if a.action=='stop':
            ec2.stop_instances(InstanceIds=[r['instance_id']]);r['status']='stopping'
        elif a.action=='start':
            assert vm['State']['Name']=='stopped','Instance must be stopped before review restart'
            ec2.start_instances(InstanceIds=[r['instance_id']]);r['status']='restarting'
        else:
            ec2.terminate_instances(InstanceIds=[r['instance_id']]);r['status']='terminating'
        save(r);print(r['instance_id'],r['status'])
