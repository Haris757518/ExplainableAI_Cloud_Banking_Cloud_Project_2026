"""Explicitly authorized deployment of the public banking historical data path."""
from pathlib import Path
import sys,os,json,uuid,hashlib
from datetime import datetime,timezone,timedelta
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import boto3
from botocore.config import Config
from dataset.real_banking.store import ROOT,DATA,sources,write_json,read_json

def main():
    session=boto3.Session()
    session.client('sts').get_caller_identity()
    region=session.region_name or 'us-east-1'
    previous=read_json(DATA/'deployment.json',{})
    bucket=previous.get('bucket') or f'xai-public-bank-history-{uuid.uuid4().hex[:12]}'
    s3=session.client('s3',region_name=region,config=Config(connect_timeout=10,read_timeout=30,retries={'max_attempts':1}))
    if not previous:
        args={'Bucket':bucket}
        if region!='us-east-1':args['CreateBucketConfiguration']={'LocationConstraint':region}
        s3.create_bucket(**args)
        write_json(DATA/'deployment.json',{'bucket':bucket,'region':region,'created_at':datetime.now(timezone.utc).isoformat(),'status':'created'})
    s3.put_public_access_block(Bucket=bucket,PublicAccessBlockConfiguration={
        'BlockPublicAcls':True,'IgnorePublicAcls':True,'BlockPublicPolicy':True,'RestrictPublicBuckets':True})
    s3.put_bucket_encryption(Bucket=bucket,ServerSideEncryptionConfiguration={'Rules':[{'ApplyServerSideEncryptionByDefault':{'SSEAlgorithm':'AES256'}}]})
    # This file stores only non-secret settings. Credentials remain in the AWS profile.
    env=ROOT/'.env'
    lines=env.read_text(encoding='utf-8').splitlines() if env.exists() else []
    updates={'BANKING_DATASET_BUCKET':bucket,'AWS_REGION':region,'AWS_PROFILE':session.profile_name or 'default'}
    lines=[line for line in lines if line.split('=',1)[0] not in updates]
    env.write_text('\n'.join(lines+[f'{key}={value}' for key,value in updates.items()])+'\n',encoding='utf-8')
    os.environ['BANKING_DATASET_BUCKET']=bucket
    from common.config import get_settings
    get_settings.cache_clear()
    from aws.banking_dataset_store import upload
    receipts=[]
    for source in sources():
        if not source['manifest']:raise ValueError('Validated bank import unavailable')
        result=upload(source['manifest'],s3)
        for obj in result['objects']:
            response=s3.get_object(Bucket=bucket,Key=obj['key'])
            content=response['Body'].read();response['Body'].close()
            if hashlib.sha256(content).hexdigest()!=obj['sha256']:raise ValueError('Downloaded S3 object checksum differs')
            obj['download_sha256_verified']=True
        result['verification']='S3 HEAD metadata/length and downloaded content SHA-256'
        write_json(DATA/f"{source['bank']}-aws.json",result)
        receipts.append(result)
    from aws.banking_import_health import publish
    health=publish(True,session.client('cloudwatch',region_name=region))
    protection=s3.get_public_access_block(Bucket=bucket)['PublicAccessBlockConfiguration']
    encryption=s3.get_bucket_encryption(Bucket=bucket)['ServerSideEncryptionConfiguration']
    result={'status':'uploaded_and_verified','bucket':bucket,'region':region,'objects':sum(len(r['objects']) for r in receipts),
        'public_access_block':protection,'encryption':encryption,'cloudwatch':health,'verified_at':datetime.now(timezone.utc).isoformat()}
    write_json(DATA/'deployment.json',result)
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
