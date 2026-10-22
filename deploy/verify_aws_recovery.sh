#!/bin/bash
set -euo pipefail
python3 /opt/banking-research/anthos/verify_anthos_transfer.py --environment aws --source-instance i-0aefecc39f02f2727 --out /opt/banking-research/telemetry/recovery
python3 - <<'PY'
import subprocess,json,urllib.request,time
from pathlib import Path
root=Path('/opt/banking-research/telemetry/recovery');root.mkdir(exist_ok=True)
def kube(*args):return subprocess.check_output(['kubectl','-n','banking-probe-research',*args],text=True)
def sql(q):return kube('exec','statefulset/ledger-db','--','psql','-U','admin','-d','postgresdb','-At','-c',q).strip()
services=json.loads(kube('get','services','-o','json'))['items'];ips={s['metadata']['name']:s['spec']['clusterIP'] for s in services}
def get(url):
 with urllib.request.urlopen(url,timeout=15) as response:return json.load(response)
result={'source':'executed-aws-bank-of-anthos','checked_at':time.time(),'accounts':[],'observations':[]}
for username,account in [('testuser','1011226111'),('alice','1033623433')]:
 import urllib.parse
 login=get('http://'+ips['userservice']+':8080/login?'+urllib.parse.urlencode({'username':username,'password':'bankofanthos'}))
 token=login['token']
 request=urllib.request.Request('http://'+ips['balancereader']+':8080/balances/'+account,headers={'Authorization':'Bearer '+token})
 with urllib.request.urlopen(request,timeout=15) as response:api_balance=json.load(response)
 expected=int(sql("SELECT COALESCE(SUM(CASE WHEN to_acct='"+account+"' AND to_route='883745000' THEN amount ELSE 0 END),0)-COALESCE(SUM(CASE WHEN from_acct='"+account+"' AND from_route='883745000' THEN amount ELSE 0 END),0) FROM transactions;"))
 request=urllib.request.Request('http://'+ips['transactionhistory']+':8080/transactions/'+account,headers={'Authorization':'Bearer '+token})
 with urllib.request.urlopen(request,timeout=15) as response:history=json.load(response)
 history_ids=[t['transactionId'] for t in history]
 result['accounts'].append({'account':account,'ledger_expected_balance_cents':expected,'api_balance_cents':api_balance,'balance_matches':expected==api_balance,'history_returned':len(history),'history_unique_ids':len(history_ids)==len(set(history_ids))})
 assert expected==api_balance,'API balance differs from ledger'
for i in range(3):
 start=time.monotonic()
 request=urllib.request.Request('http://'+ips['balancereader']+':8080/balances/1033623433',headers={'Authorization':'Bearer '+token})
 with urllib.request.urlopen(request,timeout=15) as response:response.read();status=response.status
 result['observations'].append({'timestamp':time.time(),'balance_read_latency_ms':(time.monotonic()-start)*1000,'http_status':status})
 time.sleep(2)
result['blocked_database_sessions']=int(sql("SELECT COUNT(*) FROM pg_stat_activity WHERE cardinality(pg_blocking_pids(pid))>0;"))
result['ledgerwriter_resources']=json.loads(kube('get','deployment/ledgerwriter','-o','json'))['spec']['template']['spec']['containers'][0]['resources']
(root/'balance-history-reconciliation.json').write_text(json.dumps(result,indent=2));print(json.dumps(result,indent=2))
PY
