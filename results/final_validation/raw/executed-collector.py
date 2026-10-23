"""Bounded, real AWS banking experiments. Labels never enter measurements.

Run on the approved host via SSM. No external money, AWS provisioning, retries,
or invented measurements. Raw actuator, cgroup, PostgreSQL and request evidence
is retained; missing instruments remain missing.
"""
import concurrent.futures,datetime,hashlib,http.cookiejar,io,json,os,subprocess,threading,time
from pathlib import Path
import urllib.request,urllib.parse,urllib.error,uuid

NS='banking-probe-research'
ROOT=Path('/opt/banking-research/telemetry')
RUN='final-controlled-'+datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ')
OUT=ROOT/RUN;OUT.mkdir(parents=True,exist_ok=False)
RAW=OUT/'measurements.jsonl';LABELS=OUT/'interventions.jsonl'
lock=threading.Lock();stop=threading.Event();events=[];next_id=10000
def write(path,row):
    with lock:
        with path.open('a') as f:f.write(json.dumps(row,separators=(',',':'))+'\n')
def kube(*args,timeout=20):
    return subprocess.check_output(['kubectl','-n',NS,*args],text=True,timeout=timeout)
def get(url,timeout=4):
    with urllib.request.urlopen(url,timeout=timeout) as response:return json.load(response)
def sql(query,timeout=15):
    return kube('exec','statefulset/ledger-db','--','psql','-U','admin','-d','postgresdb','-At','-c',query,timeout=timeout).strip()
services=json.loads(kube('get','services','-o','json'))['items']
ips={s['metadata']['name']:s['spec']['clusterIP'] for s in services}
pods=json.loads(kube('get','pods','-o','json'))['items']
cgroups={}
for pod in pods:
    service=pod['metadata']['labels'].get('app')
    if service not in ('frontend','ledgerwriter','ledger-db','balancereader'):continue
    try:
        cid=pod['status']['containerStatuses'][0]['containerID'].split('://')[1]
        details=json.loads(subprocess.check_output(['k3s','crictl','inspect',cid],text=True))
        pid=details['info']['pid'];relative=Path(f'/proc/{pid}/cgroup').read_text().split('0::',1)[1].strip()
        cgroups[service]=Path('/sys/fs/cgroup'+relative)
    except Exception as error:write(RAW,{'timestamp':time.time(),'instrument':'cgroup_discovery','service':service,'error':str(error)})
(OUT/'deployment-before.json').write_text(json.dumps(pods))
(OUT/'executed-collector.py').write_bytes(Path(__file__).read_bytes())
java_metrics=('process.cpu.time','process.cpu.usage','jvm.gc.pause','jvm.memory.used','jvm.memory.max',
              'tomcat.threads.busy','tomcat.threads.config.max','hikaricp.connections.active',
              'hikaricp.connections.pending','hikaricp.connections.acquire','executor.queued')
def sample():
    while not stop.is_set():
        begun=time.monotonic();row={'timestamp':time.time(),'instrument':'periodic_snapshot','cgroups':{},'java':{}}
        for service,path in cgroups.items():
            data={}
            for name in ('cpu.stat','cpu.max','memory.current','memory.max'):
                try:data[name]=(path/name).read_text().strip()
                except Exception as error:data[name]={'unavailable':str(error)}
            row['cgroups'][service]=data
        try:
            query="""SELECT COALESCE(json_agg(t),'[]'::json) FROM (SELECT pid,application_name,state,wait_event_type,wait_event,EXTRACT(EPOCH FROM clock_timestamp()-query_start)*1000 AS query_elapsed_ms,EXTRACT(EPOCH FROM clock_timestamp()-xact_start) AS transaction_age_seconds,pg_blocking_pids(pid) AS blocking_pids FROM pg_stat_activity WHERE datname=current_database() AND pid<>pg_backend_pid() AND state<>'idle') t;"""
            row['postgres_activity']=json.loads(sql(query,timeout=5))
            row['postgres_lock_waits']=json.loads(sql("SELECT COALESCE(json_agg(t),'[]'::json) FROM (SELECT pid,locktype,mode,granted,EXTRACT(EPOCH FROM clock_timestamp()-waitstart)*1000 AS lock_wait_ms FROM pg_locks WHERE NOT granted) t;",timeout=5))
        except Exception as error:row['postgres_unavailable']=str(error)
        row['collection_elapsed_ms']=(time.monotonic()-begun)*1000
        write(RAW,row);stop.wait(max(0,2-(time.monotonic()-begun)))
jar=http.cookiejar.CookieJar();login=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
with login.open(urllib.request.Request('http://127.0.0.1:8080/login',data=urllib.parse.urlencode({'username':'testuser','password':'bankofanthos'}).encode()),timeout=30) as response:response.read()
token=next(c.value for c in jar if c.name=='token')
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None
def post(path,form,trace=None):
    client=urllib.request.build_opener(NoRedirect())
    headers={'Cookie':'token='+token,'Content-Type':'application/x-www-form-urlencoded'}
    if trace:headers['traceparent']='00-'+trace+'-'+uuid.uuid4().hex[:16]+'-01'
    request=urllib.request.Request('http://127.0.0.1:8080'+path,data=urllib.parse.urlencode(form).encode(),headers=headers)
    try:
        with client.open(request,timeout=8) as response:return response.status,response.headers.get('Location',''),response.read().decode(errors='replace')
    except urllib.error.HTTPError as response:
        return response.code,response.headers.get('Location',''),response.read().decode(errors='replace')
# Fund only the isolated public demo account, using the upstream demo deposit
# mechanism. This is virtual test money, not an external financial transfer.
funding=post('/deposit',{'account':json.dumps({'account_num':'9099791699','routing_num':'808889588'}),'amount':'10000000.00','uuid':uuid.uuid4().hex})
write(RAW,{'timestamp':time.time(),'instrument':'demo_funding','status':funding[0],'result_path':funding[1]})
assert 'successful' in urllib.parse.unquote(funding[1]).lower(),'Demo funding did not succeed'
before=int(sql('SELECT COALESCE(MAX(transaction_id),0) FROM transactions;'))
started=time.time();sampler=threading.Thread(target=sample,daemon=True);sampler.start()
pool=concurrent.futures.ThreadPoolExecutor(max_workers=64);pending=[]
def payment(number,scheduled):
    operation=uuid.uuid4().hex;trace=uuid.uuid4().hex;begun=time.time();clock=time.monotonic()
    write(RAW,{'timestamp':begun,'instrument':'payment_start','operation_uuid':operation,'amount_cents':number})
    row={'timestamp':begun,'instrument':'payment_request','operation_uuid':operation,'trace_id':trace,'amount_cents':number,
         'scheduled_at':scheduled,'client_dispatch_delay_ms':max(0,(begun-scheduled)*1000)}
    try:
        status,location,body=post('/payment',{'account_num':'1033623433','amount':format(number/100,'.2f'),'uuid':operation},trace)
        message=urllib.parse.parse_qs(urllib.parse.urlsplit(location).query).get('msg',[''])[0]
        row.update(http_status=status,outcome='acknowledged_success' if message.lower()=='payment successful' else 'not_acknowledged_success',result_path=urllib.parse.urlsplit(location).path,result_message=message)
    except Exception as error:row.update(outcome='uncertain',error=type(error).__name__+': '+str(error))
    row['latency_ms']=(time.monotonic()-clock)*1000;row['completed_at']=time.time();events.append(row);write(RAW,row)
def phase(name,duration,rate):
    global next_id
    begin=time.time();write(LABELS,{'timestamp':begin,'event':'phase_start','name':name,'planned_seconds':duration,'offered_rps':rate})
    for n in range(int(duration*rate)):
        scheduled=begin+n/rate
        time.sleep(max(0,scheduled-time.time()))
        next_id+=1;pending.append(pool.submit(payment,next_id,scheduled))
    time.sleep(max(0,begin+duration-time.time()))
    concurrent.futures.wait(pending,timeout=20)
    write(LABELS,{'timestamp':time.time(),'event':'phase_end','name':name})
target=next(p for p in pods if p['metadata']['labels'].get('app')=='ledgerwriter')
container=target['spec']['containers'][0];original=container['resources']
resized=False
def resize(resources):
    patch={'spec':{'containers':[{'name':container['name'],'resources':resources}]}}
    result=kube('patch','pod',target['metadata']['name'],'--subresource=resize','--type=strategic','-p',json.dumps(patch))
    write(LABELS,{'timestamp':time.time(),'event':'executed_pod_resize','requested_resources':resources,'output':result})
try:
    phase('normal',360,5)
    reduced=json.loads(json.dumps(original));reduced['limits']['cpu']='20m';reduced['requests']['cpu']='20m'
    for trial in range(1,4):
        try:
            resize(reduced);resized=True;phase('reduced_cpu_'+str(trial),75,5)
        finally:
            if resized:resize(original);resized=False
        phase('cpu_recovery_'+str(trial),90,5)
        lock_command=['kubectl','-n',NS,'exec','statefulset/ledger-db','--','psql','-U','admin','-d','postgresdb','-v','ON_ERROR_STOP=1','-c',"SET application_name='research-bounded-lock'; BEGIN; LOCK TABLE transactions IN ACCESS EXCLUSIVE MODE; SELECT pg_sleep(30); COMMIT;"]
        lock_log=(OUT/('bounded-lock-'+str(trial)+'.stdout')).open('w')
        blocker=subprocess.Popen(lock_command,stdout=lock_log,stderr=subprocess.STDOUT)
        write(LABELS,{'timestamp':time.time(),'event':'bounded_database_lock_started','duration_seconds':30,'trial':trial})
        phase('db_contention_'+str(trial),60,5);blocker.wait(timeout=10);lock_log.close()
        assert blocker.returncode==0
        write(LABELS,{'timestamp':time.time(),'event':'bounded_database_lock_process_exit','return_code':blocker.returncode,'trial':trial})
        phase('db_recovery_'+str(trial),60,5)
        if trial<=2:
            phase('heavy_transactions_'+str(trial),60,15)
            phase('traffic_recovery_'+str(trial),60,5)
finally:
    if resized:resize(original)
    pool.shutdown(wait=True);stop.set();sampler.join(timeout=20)
    time.sleep(5)
    (OUT/'frontend-raw.log').write_text(kube('logs','deployment/frontend','--since=40m'))
    (OUT/'ledgerwriter-raw.log').write_text(kube('logs','deployment/ledgerwriter','--since=40m'))
    ledger=json.loads(sql('SELECT COALESCE(json_agg(t),\'[]\'::json) FROM (SELECT * FROM transactions WHERE transaction_id>'+str(before)+') t;'))
    (OUT/'ledger-after.json').write_text(json.dumps(ledger))
    counts={}
    for t in ledger:
        if t['from_acct']=='1011226111' and t['to_acct']=='1033623433':counts[t['amount']]=counts.get(t['amount'],0)+1
    observed={e['amount_cents'] for e in events};unresolved=[e['operation_uuid'] for e in events if e['outcome']=='uncertain' and counts.get(e['amount_cents'],0)==0]
    summary={'source':'executed-aws-bank-of-anthos','instance':'i-04d8be0ce9bcbef28','execution_id':RUN,'started_at':started,'ended_at':time.time(),
       'submitted_requests':len(events),'acknowledged_success':sum(e['outcome']=='acknowledged_success' for e in events),
       'unique_amount_ledger_records':sum(counts.get(amount,0) for amount in observed),'duplicate_amounts':[amount for amount in observed if counts.get(amount,0)>1],
       'acknowledged_but_missing_ledger':[e['operation_uuid'] for e in events if e['outcome']=='acknowledged_success' and counts.get(e['amount_cents'],0)!=1],
       'unresolved_uncertain_requests':unresolved,'missing_measurements':['Direct per-request backend CPU attribution','HTTP server admission queue depth','Full backend and SQL distributed spans'],
       'integrity_scope':'Unique transfer amount per request in this isolated run; label file separate. Uncertain uncommitted requests do not imply success.',
       'files_sha256':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.iterdir() if p.is_file()}}
    (OUT/'summary.json').write_text(json.dumps(summary,indent=2));print(json.dumps(summary,indent=2),flush=True)
