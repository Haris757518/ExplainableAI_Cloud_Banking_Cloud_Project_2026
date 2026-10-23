"""Resumable SSM evidence export for the final verification instance."""
import argparse,base64,concurrent.futures,hashlib,json,sys,time
from datetime import datetime,timezone
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from final_aws_session import load,guard,save
import boto3
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
parser=argparse.ArgumentParser();parser.add_argument('--stage',choices=['proof','final'],required=True);parser.add_argument('--resume',type=Path);a=parser.parse_args()
record=load();guard(record);instance=record['instance_id'];client=boto3.client('ssm',region_name='us-east-1')
remote='/opt/banking-research/evidence-'+a.stage+'.tar.gz'
def run(script):
    command=client.send_command(InstanceIds=[instance],DocumentName='AWS-RunShellScript',Parameters={'commands':[script],'executionTimeout':['120']},TimeoutSeconds=60)['Command']['CommandId']
    for attempt in range(150):
        try:result=client.get_command_invocation(CommandId=command,InstanceId=instance)
        except client.exceptions.InvocationDoesNotExist:time.sleep(1);continue
        if result['Status'] in ('Pending','InProgress','Delayed'):time.sleep(1);continue
        if result['Status']!='Success':raise RuntimeError(result.get('StandardErrorContent') or result['Status'])
        return result['StandardOutputContent']
    raise RuntimeError('Export command timed out')
def remote_hash():
    return json.loads(run("python3 -c \"import pathlib,hashlib,json;p=pathlib.Path('"+remote+"');print(json.dumps({'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))\""))
if a.resume:
    folder=a.resume;metadata=json.loads((folder/'export-manifest.json').read_text());assert metadata['sha256']==remote_hash()['sha256']
else:
    snapshot='''set -eu
mkdir -p /opt/banking-research/runtime-snapshot
kubectl get nodes -o json > /opt/banking-research/runtime-snapshot/nodes.json
kubectl -n banking-probe-research get pods,deployments,statefulsets,services -o json > /opt/banking-research/runtime-snapshot/workloads.json
systemctl list-timers bank-final-deadline.timer --no-pager > /opt/banking-research/runtime-snapshot/deadline.txt
'''
    if a.stage=='final':snapshot+='''mkdir -p /opt/banking-research/telemetry/database-backup
python3 - <<'PY'
import subprocess,gzip,pathlib
payload=subprocess.check_output(['kubectl','-n','banking-probe-research','exec','statefulset/ledger-db','--','pg_dump','-U','admin','-d','postgresdb','--no-owner','--no-acl'])
assert b'CREATE TABLE public.transactions' in payload and len(payload)>1000
pathlib.Path('/opt/banking-research/telemetry/database-backup/ledger-final.sql.gz').write_bytes(gzip.compress(payload))
PY
'''
    exclude=" --exclude='telemetry/final-controlled-*'" if a.stage=='proof' else ''
    run(snapshot+'\ntar'+exclude+' -czf '+remote+' -C /opt/banking-research telemetry runtime-snapshot k3s-installer.sha256\n')
    metadata=remote_hash();folder=Path(r'D:\BankingResearch\Telemetry')/('final-'+a.stage+'-export-'+datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ'));folder.mkdir()
    metadata.update(hash_verified=False,source_instance=instance,stage=a.stage)
    (folder/'export-manifest.json').write_text(json.dumps(metadata,indent=2))
chunks=folder/'chunks';chunks.mkdir(exist_ok=True);size=12288;count=(metadata['bytes']+size-1)//size
def fetch(index):
    path=chunks/f'{index:05d}.bin';expected=min(size,metadata['bytes']-index*size)
    if path.exists() and path.stat().st_size==expected:return index,path.read_bytes()
    for attempt in range(3):
        try:
            data=base64.b64decode(run(f'dd if={remote} bs={size} skip={index} count=1 status=none | base64 -w0'),validate=True)
            assert len(data)==expected
            path.write_bytes(data);return index,data
        except Exception:
            if attempt==2:raise
            time.sleep(2)
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:parts=dict(pool.map(fetch,range(count)))
payload=b''.join(parts[i] for i in range(count));assert hashlib.sha256(payload).hexdigest()==metadata['sha256']
(folder/'evidence.tar.gz').write_bytes(payload);metadata.update(hash_verified=True,exported_at=datetime.now(timezone.utc).isoformat())
(folder/'export-manifest.json').write_text(json.dumps(metadata,indent=2))
record=load();record.setdefault('exports',[]).append({'stage':a.stage,'folder':str(folder),'sha256':metadata['sha256'],'hash_verified':True});save(record)
print('Checksum-verified export:',folder,metadata['sha256'],flush=True)
