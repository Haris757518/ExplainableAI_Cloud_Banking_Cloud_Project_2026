"""Verify the final retained archive before terminating only the approved instance."""
import hashlib, json, tarfile, time
from datetime import datetime, timezone
from pathlib import Path
import boto3

folder = Path(r'D:\BankingResearch\Telemetry\aws-export-20261022T182441Z')
manifest = json.loads((folder / 'export-manifest.json').read_text())
archive = folder / 'evidence.tar.gz'
assert manifest['hash_verified'] is True
assert hashlib.sha256(archive.read_bytes()).hexdigest() == manifest['sha256']
with tarfile.open(archive) as tar:
    names = tar.getnames()
    backup = next(n for n in names if n.endswith('/ledger-final.sql.gz'))
    payload = tar.extractfile(backup).read()
    assert hashlib.sha256(payload).hexdigest() == '0f1a41e838de43ef70a7d1c33395027e6957a1649f3edf2225d3c50f0f2212d6'
    assert any('recovery-after-cache-resync/' in n and n.endswith('verification.json') for n in names)
    tar.extractall(folder / 'verified-files', filter='data')
    backups = Path(r'D:\BankingResearch\Backups')
    backups.mkdir(exist_ok=True)
    (backups / 'aws-ledger-final-20261022.sql.gz').write_bytes(payload)
print('Final archive and database backup verified.', flush=True)
active_path = Path(r'D:\BankingResearch\Reports\aws-active-experiment.json')
active = json.loads(active_path.read_text())
instance = active['instance_id']
assert instance == 'i-0aefecc39f02f2727'
assert boto3.client('sts').get_caller_identity()['Account'] == '047856835753'
ec2 = boto3.client('ec2', region_name='us-east-1')
vm = ec2.describe_instances(InstanceIds=[instance])['Reservations'][0]['Instances'][0]
tags = {t['Key']:t['Value'] for t in vm.get('Tags', [])}
assert tags.get('ResearchRun') == active['run'], tags.get('ResearchRun')
ec2.terminate_instances(InstanceIds=[instance])
print('Termination requested for the approved research instance.', flush=True)
for _ in range(60):
    state = ec2.describe_instances(InstanceIds=[instance])['Reservations'][0]['Instances'][0]['State']['Name']
    if state == 'terminated': break
    time.sleep(5)
assert state == 'terminated', state
volume_deleted = False
for _ in range(12):
    try: ec2.describe_volumes(VolumeIds=['vol-052d04d0a053ba06d'])
    except ec2.exceptions.ClientError as error:
        if error.response['Error']['Code'] == 'InvalidVolume.NotFound':
            volume_deleted = True
            break
        raise
    time.sleep(5)
active.update(status='terminated', state='terminated', terminated_verified_at=datetime.now(timezone.utc).isoformat(), final_export=str(folder), final_export_sha256=manifest['sha256'], root_volume_deleted=volume_deleted)
active_path.write_text(json.dumps(active, indent=2))
Path(r'D:\BankingResearch\Reports\aws-cleanup-verification.json').write_text(json.dumps(active, indent=2))
status_path = Path('results/aws_workload/status.json')
status = json.loads(status_path.read_text())
status.update(compute_state='terminated', final_export=str(folder), final_export_sha256=manifest['sha256'], root_volume_deleted=volume_deleted, experiment_status='Controlled workload completed: 3,025 unique ledger transfers. Recovery checks passed after reader resynchronization. Final archive and database backup verified on D:. Research instance terminated.')
status_path.write_text(json.dumps(status, indent=2))
print(json.dumps({'research_instance':state, 'root_volume_deleted':volume_deleted, 'final_export':str(folder)}), flush=True)
