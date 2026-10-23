"""Prepare ConfigMap class overrides for the two validated Java readers."""
import base64,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'deploy/correctness-fix/patch-manifest.json').read_text())
validation=json.loads((ROOT/'results/correctness_fix/local-validation.json').read_text())
assert validation['status']=='validated_locally' and validation['patch_sha256']==manifest['patch_sha256']
tree=Path(manifest['validation_tree']);documents=[];patches={};checksums={}
for service,controller in [('balancereader','BalanceReaderController'),('transactionhistory','TransactionHistoryController')]:
    folder=tree/f'src/ledger/{service}/target/classes/anthos/samples/bankofanthos/{service}'
    files={name+'.class':(folder/(name+'.class')).read_bytes() for name in (controller,'TransactionRepository')}
    checksums[service]={name:hashlib.sha256(data).hexdigest() for name,data in files.items()}
    documents.append({'apiVersion':'v1','kind':'ConfigMap','metadata':{'name':'correctness-'+service,'namespace':'banking-probe-research'},'binaryData':{name:base64.b64encode(data).decode() for name,data in files.items()}})
    volume='correctness-classes'
    mounts=[{'name':volume,'mountPath':f'/app/classes/anthos/samples/bankofanthos/{service}/{name}','subPath':name,'readOnly':True} for name in files]
    patches[service]={'spec':{'template':{'metadata':{'annotations':{'research.correctness/patch-sha256':manifest['patch_sha256']}},'spec':{'containers':[{'name':service,'volumeMounts':mounts}],'volumes':[{'name':volume,'configMap':{'name':'correctness-'+service}}]}}}}
payload=base64.b64encode(json.dumps({'documents':documents,'patches':patches,'checksums':checksums}).encode()).decode()
script='''#!/bin/bash
set -euo pipefail
mkdir -p /opt/banking-research/telemetry/correctness-fix
python3 - <<'PY'
import base64,json,subprocess
from pathlib import Path
bundle=json.loads(base64.b64decode('''+repr(payload)+'''))
for doc in bundle['documents']:
 subprocess.run(['kubectl','apply','-f','-'],input=json.dumps(doc),text=True,check=True)
for service,patch in bundle['patches'].items():
 subprocess.run(['kubectl','-n','banking-probe-research','patch','deployment',service,'--type=strategic','-p',json.dumps(patch)],check=True)
 subprocess.run(['kubectl','-n','banking-probe-research','rollout','status','deployment/'+service,'--timeout=180s'],check=True)
observed={}
for service,files in bundle['checksums'].items():
 observed[service]={}
 for name,expected in files.items():
  path='/app/classes/anthos/samples/bankofanthos/'+service+'/'+name
  actual=subprocess.check_output(['kubectl','-n','banking-probe-research','exec','deployment/'+service,'--','sha256sum',path],text=True).split()[0]
  assert actual==expected,'Deployed class differs from validated build'
  observed[service][name]=actual
Path('/opt/banking-research/telemetry/correctness-fix/deployed-class-checksums.json').write_text(json.dumps({'expected':bundle['checksums'],'observed':observed,'hashes_match':True},indent=2))
PY
kubectl -n banking-probe-research get pods -o wide
'''
(ROOT/'deploy/apply_correctness_fix.sh').write_text(script)
(ROOT/'deploy/correctness-fix/class-checksums.json').write_text(json.dumps(checksums,indent=2))
print('Prepared validated class overrides; no deployment performed.')
