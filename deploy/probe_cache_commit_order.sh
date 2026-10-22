#!/bin/bash
set -euo pipefail
mkdir -p /opt/banking-research/telemetry/integrity_probe
kubectl -n banking-probe-research logs deployment/balancereader --since=30m > /opt/banking-research/telemetry/integrity_probe/balancereader-before.log
kubectl -n banking-probe-research rollout restart deployment/balancereader
kubectl -n banking-probe-research rollout status deployment/balancereader --timeout=120s
python3 - <<'PY'
import json,time,subprocess,urllib.request,urllib.parse
from pathlib import Path
root=Path('/opt/banking-research/telemetry/integrity_probe')
def kube(*a):return subprocess.check_output(['kubectl','-n','banking-probe-research',*a],text=True)
def sql(q):return kube('exec','statefulset/ledger-db','--','psql','-U','admin','-d','postgresdb','-At','-v','ON_ERROR_STOP=1','-c',q).strip()
items=json.loads(kube('get','services','-o','json'))['items'];ips={x['metadata']['name']:x['spec']['clusterIP'] for x in items}
with urllib.request.urlopen('http://'+ips['userservice']+':8080/login?'+urllib.parse.urlencode({'username':'testuser','password':'bankofanthos'}),timeout=15) as response:token=json.load(response)['token']
def balance():
 request=urllib.request.Request('http://'+ips['balancereader']+':8080/balances/1011226111',headers={'Authorization':'Bearer '+token})
 with urllib.request.urlopen(request,timeout=15) as response:api=json.load(response)
 expected=int(sql("SELECT COALESCE(SUM(CASE WHEN to_acct='1011226111' AND to_route='883745000' THEN amount ELSE 0 END),0)-COALESCE(SUM(CASE WHEN from_acct='1011226111' AND from_route='883745000' THEN amount ELSE 0 END),0) FROM transactions;"))
 return {'timestamp':time.time(),'api_cents':api,'ledger_cents':expected,'difference_cents':api-expected}
result={'source':'executed-aws-controlled-database-commit-order-probe','scope':'Two isolated diagnostic SQL transfers, not application traffic','before_probe':balance()}
(root/'commit-order-probe.json').write_text(json.dumps(result,indent=2))
assert result['before_probe']['difference_cents']==0,'Reader did not resynchronize after restart'
insert="INSERT INTO transactions (from_acct,to_acct,from_route,to_route,amount,timestamp) VALUES ('1011226111','1033623433','883745000','883745000',AMOUNT,clock_timestamp()) RETURNING transaction_id;"
held_file=(root/'held-transaction.stdout').open('w')
held=subprocess.Popen(['kubectl','-n','banking-probe-research','exec','statefulset/ledger-db','--','psql','-U','admin','-d','postgresdb','-At','-v','ON_ERROR_STOP=1','-c',"SET application_name='research-order-held'; BEGIN; "+insert.replace('AMOUNT','17')+" SELECT pg_sleep(12); COMMIT;"],stdout=held_file,stderr=subprocess.STDOUT)
for attempt in range(20):
 if int(sql("SELECT COUNT(*) FROM pg_stat_activity WHERE application_name='research-order-held' AND wait_event='PgSleep';"))==1:break
 time.sleep(.2)
else:raise RuntimeError('Held diagnostic transaction did not reach its measured pause')
result['later_id_committed_first_output']=sql(insert.replace('AMOUNT','19'))
time.sleep(2);result['while_earlier_id_uncommitted']=balance()
held.wait(timeout=20);held_file.close();result['held_process_exit']=held.returncode
time.sleep(2);result['after_earlier_id_commit']=balance()
result['observed_skipped_earlier_amount_cents']=result['after_earlier_id_commit']['difference_cents']-result['before_probe']['difference_cents']
(root/'commit-order-probe.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
PY
kubectl -n banking-probe-research rollout restart deployment/balancereader deployment/transactionhistory
kubectl -n banking-probe-research rollout status deployment/balancereader --timeout=120s
kubectl -n banking-probe-research rollout status deployment/transactionhistory --timeout=120s
kubectl -n banking-probe-research get pods -o wide > /opt/banking-research/telemetry/integrity_probe/pods-after.txt
