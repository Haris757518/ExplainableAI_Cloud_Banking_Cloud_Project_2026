"""Export actual research files over SSM without opening ports or using S3."""
import base64,concurrent.futures,hashlib,json,time,sys,argparse
from datetime import datetime,timezone
from pathlib import Path
import boto3
sys.stdout.reconfigure(encoding='utf-8',errors='replace')
r=json.loads(Path(r'D:\BankingResearch\Reports\aws-active-experiment.json').read_text())
parser=argparse.ArgumentParser();parser.add_argument('--resume',type=Path);args=parser.parse_args()
instance=r['instance_id'];assert instance=='i-0aefecc39f02f2727'
client=boto3.client('ssm',region_name='us-east-1')
def run(script):
    command=client.send_command(InstanceIds=[instance],DocumentName='AWS-RunShellScript',Parameters={'commands':[script],'executionTimeout':['90']},TimeoutSeconds=60)['Command']['CommandId']
    for attempt in range(180):
        try:result=client.get_command_invocation(CommandId=command,InstanceId=instance)
        except client.exceptions.InvocationDoesNotExist:time.sleep(1);continue
        if result['Status'] in ('Pending','InProgress','Delayed'):time.sleep(1);continue
        if result['Status']!='Success':raise RuntimeError(result.get('StandardErrorContent') or result['Status'])
        return result['StandardOutputContent']
    raise RuntimeError('Export command timeout')
snapshot='''set -eu
mkdir -p /opt/banking-research/runtime-snapshot
kubectl get nodes -o json > /opt/banking-research/runtime-snapshot/nodes.json
kubectl -n banking-probe-research get pods,deployments,statefulsets,services -o json > /opt/banking-research/runtime-snapshot/workloads.json
systemctl list-timers bank-research-deadline.timer --no-pager > /opt/banking-research/runtime-snapshot/deadline.txt
k3s --version > /opt/banking-research/runtime-snapshot/k3s-version.txt
tar -czf /opt/banking-research/evidence-export.tar.gz -C /opt/banking-research telemetry runtime-snapshot k3s-installer.sha256
python3 - <<'PY'
import hashlib,json
from pathlib import Path
p=Path('/opt/banking-research/evidence-export.tar.gz');print(json.dumps({'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))
PY
'''
if args.resume:
    folder=args.resume;metadata=json.loads((folder/'export-manifest.json').read_text())
    observed=json.loads(run("python3 -c \"import pathlib,hashlib,json;p=pathlib.Path('/opt/banking-research/evidence-export.tar.gz');print(json.dumps({'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}))\""))
    assert observed['sha256']==metadata['sha256'],'Remote export changed; refusing to mix chunks'
else:
    metadata=json.loads(run(snapshot));stamp=datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')
    folder=Path(r'D:\BankingResearch\Telemetry')/('aws-export-'+stamp);folder.mkdir(exist_ok=False)
    (folder/'export-manifest.json').write_text(json.dumps({**metadata,'hash_verified':False},indent=2))
chunks=folder/'chunks';chunks.mkdir(exist_ok=True)
chunk_size=12288;count=(metadata['bytes']+chunk_size-1)//chunk_size
def fetch(index):
    target=chunks/f'{index:05d}.bin'
    expected=min(chunk_size,metadata['bytes']-index*chunk_size)
    if target.exists() and target.stat().st_size==expected:return index,target.read_bytes()
    text=run(f'dd if=/opt/banking-research/evidence-export.tar.gz bs={chunk_size} skip={index} count=1 status=none | base64 -w0')
    data=base64.b64decode(text,validate=True)
    if len(data)!=expected:raise RuntimeError('Truncated export chunk')
    target.write_bytes(data)
    return index,data
parts={}
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:
    for index,data in pool.map(fetch,range(count)):parts[index]=data
payload=b''.join(parts[i] for i in range(count))
assert hashlib.sha256(payload).hexdigest()==metadata['sha256'],'Export hash mismatch'
path=folder/'evidence.tar.gz';path.write_bytes(payload)
metadata.update(source_instance=instance,source='Executed AWS Bank of Anthos; retrieved over SSM',exported_at=datetime.now(timezone.utc).isoformat(),chunks=count,hash_verified=True)
(folder/'export-manifest.json').write_text(json.dumps(metadata,indent=2))
print('Verified AWS evidence export:',folder,'bytes:',len(payload),'SHA256:',metadata['sha256'])
