"""Explicit historical artifact upload; never publish old bank metric timestamps."""
import os
import hashlib
from datetime import datetime, timezone
from dataset.real_banking.store import ROOT, DATA, write_json, read_json

def configuration():
    from common.config import get_settings
    settings=get_settings()
    return os.environ.get('BANKING_DATASET_BUCKET') or settings.banking_dataset_bucket

def aws_client(service):
    import boto3
    from common.config import get_settings
    settings=get_settings()
    return boto3.Session(profile_name=settings.profile,region_name=settings.aws_region).client(service)

def upload(manifest, client=None):
    bucket=configuration()
    if not bucket: raise ValueError('BANKING_DATASET_BUCKET is not configured; local import remains available')
    if client is None:
        client=aws_client('s3')
    receipts=[]
    for kind,path in [('raw',manifest['snapshot']),('normalized',manifest['normalized_csv'])]:
        content=(ROOT/path).read_bytes(); checksum=hashlib.sha256(content).hexdigest()
        key=f"public-bank-history/{manifest['bank']}/{manifest['snapshot_sha256']}/{kind}/{__import__('pathlib').Path(path).name}"
        client.put_object(Bucket=bucket,Key=key,Body=content,Metadata={'sha256':checksum})
        head=client.head_object(Bucket=bucket,Key=key)
        if head.get('Metadata',{}).get('sha256')!=checksum or head['ContentLength']!=len(content):
            raise ValueError('S3 metadata/length verification failed')
        receipts.append({'bucket':bucket,'key':key,'sha256':checksum,'verified':True})
    result={'status':'verified','verified_at':datetime.now(timezone.utc).isoformat(),
            'bank':manifest['bank'],'snapshot_sha256':manifest['snapshot_sha256'],'verification':'S3 HEAD metadata and content length','objects':receipts}
    write_json(DATA/f"{manifest['bank']}-aws.json",result)
    return result

def status():
    from dataset.real_banking.schema import SOURCES
    storage={}
    for bank in SOURCES:
        receipt=read_json(DATA/f'{bank}-aws.json',{'status':'not_executed'})
        current=read_json(DATA/f'{bank}-current.json',{})
        if receipt.get('status')=='verified':
            receipt['matches_current_source']=receipt.get('snapshot_sha256')==current.get('snapshot_sha256')
            if not receipt['matches_current_source']: receipt['status']='verified_prior_snapshot_only'
        storage[bank]=receipt
    return {'configured':bool(configuration()),'bucket':configuration(),
        'storage':storage,
        'cloudwatch':read_json(DATA/'cloudwatch.json',{'status':'not_executed'}),
        'message':'Historical uploads target S3. CloudWatch writes contain current importer health only. Saved receipts describe prior verification, not a fresh permission check.'}
