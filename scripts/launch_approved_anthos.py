"""One specifically approved Academy instance; no EKS or managed database."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import uuid
import boto3

REPORTS=Path(r'D:\BankingResearch\Reports')
MANIFEST=REPORTS/'aws-active-experiment.json'

def main():
    if MANIFEST.exists():
        raise SystemExit('An experiment manifest already exists. Inspect it before any retry.')
    now=datetime.now(timezone.utc)
    deadline=now+timedelta(minutes=110)
    run='bank-anthos-'+now.strftime('%Y%m%dT%H%M%SZ')
    record={'run':run,'created_at':now.isoformat(),'terminate_by':deadline.isoformat(),
        'approval':'User replied contineuw to the explicit $5, one t3.xlarge, maximum two-hour approval question.',
        'budget_usd':5,'maximum_runtime_hours':2,'region':'us-east-1','status':'preparing',
        'instance_id':None,'security_group_id':None,'key_name':'bank-anthos-key',
        'key_path':r'D:\BankingResearch\AWS-Keys\bank-anthos-key.pem',
        'image_id':'ami-02a9cdd4e98bc3c78','instance_type':'t3.xlarge',
        'preserve_existing_instance':'i-03adf941e75dd8ac1','client_token':uuid.uuid4().hex}
    def save():MANIFEST.write_text(json.dumps(record,indent=2),encoding='utf-8')
    save()
    ec2=boto3.client('ec2',region_name=record['region'])
    tags=[{'Key':'Name','Value':'bank-anthos-research'},{'Key':'ResearchRun','Value':run},
          {'Key':'ExpiresAtUTC','Value':deadline.isoformat()}]
    # Public address comes from the inspected Chrome My IP selector, never 0/0.
    ssh_source='182.156.30.27/32'
    vpcs=ec2.describe_vpcs(Filters=[{'Name':'is-default','Values':['true']}])['Vpcs']
    if len(vpcs)!=1:raise RuntimeError('Expected exactly one existing default VPC')
    vpc=vpcs[0]['VpcId']
    subnets=ec2.describe_subnets(Filters=[{'Name':'vpc-id','Values':[vpc]},{'Name':'default-for-az','Values':['true']}])['Subnets']
    subnets=sorted([s for s in subnets if s['State']=='available' and s['AvailableIpAddressCount']>5],key=lambda s:s['AvailabilityZone'])
    if not subnets:raise RuntimeError('No available default subnet')
    image=ec2.describe_images(ImageIds=[record['image_id']])['Images'][0]
    assert image['OwnerId']=='099720109477' and image['Architecture']=='x86_64'
    assert 'ubuntu-noble-24.04' in image['Name']
    ec2.describe_key_pairs(KeyNames=[record['key_name']])
    # Guest shutdown terminates this instance and its disposable root disk.
    user_data='''#!/bin/bash
set -eu
cat > /etc/systemd/system/bank-research-deadline.service <<'UNIT'
[Unit]
Description=Terminate disposable approved banking research instance
[Service]
Type=oneshot
ExecStart=/sbin/poweroff
UNIT
cat > /etc/systemd/system/bank-research-deadline.timer <<'TIMER'
[Unit]
Description=Research runtime safety deadline
[Timer]
OnBootSec=100min
AccuracySec=1s
Unit=bank-research-deadline.service
[Install]
WantedBy=timers.target
TIMER
systemctl daemon-reload
systemctl enable --now bank-research-deadline.timer
'''
    try:
        sg=ec2.create_security_group(GroupName=run,Description='Disposable banking experiment; SSH from approved My IP only',VpcId=vpc,
            TagSpecifications=[{'ResourceType':'security-group','Tags':tags}])['GroupId']
        record['security_group_id']=sg;record['ssh_source']=ssh_source;save()
        ec2.authorize_security_group_ingress(GroupId=sg,IpPermissions=[{'IpProtocol':'tcp','FromPort':22,'ToPort':22,
            'IpRanges':[{'CidrIp':ssh_source,'Description':'Research operator My IP only'}]}])
        response=ec2.run_instances(ImageId=record['image_id'],InstanceType='t3.xlarge',MinCount=1,MaxCount=1,
            KeyName=record['key_name'],ClientToken=record['client_token'],
            NetworkInterfaces=[{'DeviceIndex':0,'SubnetId':subnets[0]['SubnetId'],'Groups':[sg],
                'AssociatePublicIpAddress':True,'DeleteOnTermination':True}],
            BlockDeviceMappings=[{'DeviceName':image['RootDeviceName'],'Ebs':{'VolumeSize':40,'VolumeType':'gp3',
                'DeleteOnTermination':True,'Iops':3000,'Throughput':125}}],
            InstanceInitiatedShutdownBehavior='terminate',MetadataOptions={'HttpTokens':'required','HttpEndpoint':'enabled'},
            Monitoring={'Enabled':False},CreditSpecification={'CpuCredits':'unlimited'},UserData=user_data,
            TagSpecifications=[{'ResourceType':'instance','Tags':tags},{'ResourceType':'volume','Tags':tags}])
        instance=response['Instances'][0]
        record.update(instance_id=instance['InstanceId'],launch_time=instance['LaunchTime'].isoformat(),status='launched')
        save()
        print(json.dumps({'instance_id':record['instance_id'],'terminate_by':record['terminate_by'],'manifest':str(MANIFEST)}))
    except Exception as error:
        record['error']=type(error).__name__+': '+str(error);record['status']='launch_error';save()
        # Do not guess whether a timed-out launch succeeded. Reconcile the client
        # token and run tag before any cleanup or retry.
        raise

if __name__=='__main__':main()
