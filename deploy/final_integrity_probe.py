"""Executed PostgreSQL/API proof, deliberately isolated from normal app traffic."""
import json,os,subprocess,time,urllib.request,urllib.parse
from pathlib import Path
STAGE=os.environ['PROBE_STAGE'];assert STAGE in ('baseline','patched')
NS='banking-probe-research';OUT=Path('/opt/banking-research/telemetry/final-integrity')/STAGE;OUT.mkdir(parents=True,exist_ok=True)
def kube(*args):return subprocess.check_output(['kubectl','-n',NS,*args],text=True,timeout=180)
def sql(query):return kube('exec','statefulset/ledger-db','--','psql','-U','admin','-d','postgresdb','-At','-v','ON_ERROR_STOP=1','-c',query).strip()
services=json.loads(kube('get','services','-o','json'))['items'];ips={s['metadata']['name']:s['spec']['clusterIP'] for s in services}
def get(service,path,token=None):
 request=urllib.request.Request('http://'+ips[service]+':8080'+path,headers={'Authorization':'Bearer '+token} if token else {})
 with urllib.request.urlopen(request,timeout=20) as response:return json.load(response)
def balances(tokens):
 rows=[]
 for account,token in tokens.items():
  api=get('balancereader','/balances/'+account,token)
  expected=int(sql("SELECT COALESCE(SUM(CASE WHEN to_acct='"+account+"' AND to_route='883745000' THEN amount ELSE 0 END),0)-COALESCE(SUM(CASE WHEN from_acct='"+account+"' AND from_route='883745000' THEN amount ELSE 0 END),0) FROM transactions;"))
  history=get('transactionhistory','/transactions/'+account,token)
  rows.append({'account':account,'api_cents':api,'ledger_cents':expected,'gap_cents':api-expected,'history_ids':[t['transactionId'] for t in history]})
 return {'timestamp':time.time(),'accounts':rows}
tokens={}
for user,account in [('testuser','1011226111'),('alice','1033623433')]:
 try:tokens[account]=get('userservice','/login?'+urllib.parse.urlencode({'username':user,'password':'bankofanthos'}))['token']
 except Exception:
  if user=='alice':raise RuntimeError('Recipient login must succeed; do not fabricate its verification')
  raise
trials=[]
for trial in range(3):
 if STAGE=='baseline' or trial==0:
  for service in ('balancereader','transactionhistory'):
   kube('rollout','restart','deployment/'+service);kube('rollout','status','deployment/'+service,'--timeout=150s')
 before=balances(tokens)
 assert all(a['gap_cents']==0 for a in before['accounts'])
 insert="INSERT INTO transactions (from_acct,to_acct,from_route,to_route,amount,timestamp) VALUES ('1011226111','1033623433','883745000','883745000',AMOUNT,clock_timestamp()) RETURNING transaction_id;"
 held_path=OUT/f'held-{trial}.txt'
 with held_path.open('w') as stream:
  held=subprocess.Popen(['kubectl','-n',NS,'exec','statefulset/ledger-db','--','psql','-U','admin','-d','postgresdb','-At','-v','ON_ERROR_STOP=1','-c',"SET application_name='final-order-probe';BEGIN;"+insert.replace('AMOUNT','17')+'SELECT pg_sleep(8);COMMIT;'],stdout=stream,stderr=subprocess.STDOUT)
  try:
   for attempt in range(30):
    if int(sql("SELECT COUNT(*) FROM pg_stat_activity WHERE application_name='final-order-probe' AND wait_event='PgSleep';"))==1:break
    time.sleep(.1)
   else:raise RuntimeError('Held transaction not observed')
   later=sql(insert.replace('AMOUNT','19'));later_id=int(later.splitlines()[0]);time.sleep(1)
   while_held=balances(tokens)
   held.wait(timeout=20)
  finally:
   if held.poll() is None:held.wait(timeout=20)
 assert held.returncode==0
 earlier_id=next(int(x) for x in held_path.read_text().splitlines() if x.isdigit())
 time.sleep(1);after=balances(tokens)
 good=all(a['gap_cents']==0 and a['history_ids'].count(earlier_id)==1 and a['history_ids'].count(later_id)==1 and len(a['history_ids'])==len(set(a['history_ids'])) for a in after['accounts'])
 result={'trial':trial+1,'stage':STAGE,'source':'Executed AWS PostgreSQL and banking APIs','scope':'Two diagnostic SQL transfers, not application request traffic',
         'earlier_id':earlier_id,'later_id':later_id,'before':before,'while_held':while_held,'after':after,'both_accounts_and_history_correct':good,'held_process_exit':held.returncode}
 trials.append(result);(OUT/'trials.json').write_text(json.dumps(trials,indent=2));print(json.dumps(result),flush=True)
 if STAGE=='patched':assert good,'Patched reader failed commit-order correctness'
print('Completed',STAGE,'trials:',len(trials),flush=True)
if STAGE=='patched':
 for service in ('balancereader','transactionhistory'):
  kube('rollout','restart','deployment/'+service);kube('rollout','status','deployment/'+service,'--timeout=150s')
 after_restart=balances(tokens)
 required={r[key] for r in trials for key in ('earlier_id','later_id')}
 assert all(a['gap_cents']==0 and required<=set(a['history_ids']) and len(a['history_ids'])==len(set(a['history_ids'])) for a in after_restart['accounts'])
 (OUT/'after-restart.json').write_text(json.dumps(after_restart,indent=2))
 print('Post-fix restart check passed',flush=True)
