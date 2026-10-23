"""Verify final retained evidence and terminate only the tagged final instance."""
import argparse,gzip,hashlib,json,sys,tarfile,time
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from final_aws_session import load,guard,save,ec2
parser=argparse.ArgumentParser();parser.add_argument('--export',type=Path,required=True);args=parser.parse_args()
metadata=json.loads((args.export/'export-manifest.json').read_text());payload=(args.export/'evidence.tar.gz').read_bytes()
assert metadata['stage']=='final' and metadata['hash_verified'] and hashlib.sha256(payload).hexdigest()==metadata['sha256']
record=load();assert metadata['source_instance']==record['instance_id']
with tarfile.open(args.export/'evidence.tar.gz') as archive:
    names=archive.getnames()
    summary_name=next(n for n in names if '/final-controlled-' in n and n.endswith('/summary.json'))
    folder=summary_name.rsplit('/',1)[0];summary=json.load(archive.extractfile(summary_name))
    for name,sha in summary['files_sha256'].items():assert hashlib.sha256(archive.extractfile(folder+'/'+name).read()).hexdigest()==sha,name
    for name in ['telemetry/final-integrity/baseline/trials.json','telemetry/final-integrity/patched/trials.json','telemetry/final-integrity/patched/after-restart.json','telemetry/correctness-fix/deployed-class-checksums.json']:
        assert name in names,name
    receipts=[n for n in names if n.startswith('telemetry/final-recovery/') and n.endswith('/verification.json')]
    assert len(receipts)>=3,'Three later application-transfer receipts must be retained before cleanup'
    for name in receipts:
        proof=json.load(archive.extractfile(name));assert proof['status']=='verified' and proof['ledger_new_records']==1 and proof['history_record_found']
    sql=archive.extractfile('telemetry/database-backup/ledger-final.sql.gz').read()
    assert b'CREATE TABLE public.transactions' in gzip.decompress(sql)
    backup=Path(r'D:\BankingResearch\Backups\ledger-final-validation-20261023.sql.gz');backup.write_bytes(sql)
print('Final archive, raw measurements, later transfers and SQL backup verified.',flush=True)
vm=guard(record);volumes=[d['Ebs']['VolumeId'] for d in vm['BlockDeviceMappings'] if 'Ebs' in d]
assert len(volumes)==1 and all(d['Ebs']['DeleteOnTermination'] for d in vm['BlockDeviceMappings'] if 'Ebs' in d)
client=ec2();client.terminate_instances(InstanceIds=[record['instance_id']]);print('Final research instance termination requested.',flush=True)
state='shutting-down'
for attempt in range(60):
    state=client.describe_instances(InstanceIds=[record['instance_id']])['Reservations'][0]['Instances'][0]['State']['Name']
    if state=='terminated':break
    time.sleep(5)
assert state=='terminated'
deleted=False
for attempt in range(20):
    try:client.describe_volumes(VolumeIds=volumes)
    except client.exceptions.ClientError as error:
        if error.response['Error']['Code']=='InvalidVolume.NotFound':deleted=True;break
        raise
    time.sleep(3)
assert deleted,'Root disk deletion must be confirmed'
preserved=client.describe_instances(InstanceIds=[record['preserve_instance']])['Reservations'][0]['Instances'][0]['State']['Name']
record.update(status='terminated',state='terminated',root_volume_deleted=deleted,final_export=str(args.export),final_export_sha256=metadata['sha256'],
              sql_backup=str(backup),cleanup_verified_at=datetime.now(timezone.utc).isoformat(),preserved_payment_server_state=preserved)
save(record)
report={k:record[k] for k in ['instance_id','run','status','root_volume_deleted','final_export_sha256','cleanup_verified_at','preserved_payment_server_state','sql_backup','launch_time','deadline_utc']}
root=Path(__file__).resolve().parents[1]
(root/'results/final_validation/aws-cleanup.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2),flush=True)
