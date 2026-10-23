"""Execute real demo payments on the isolated AWS host, for at most 90 minutes.

No fault labels are read. Each round has three concurrent requests; uncertain
payments are never retried. Run only after the research deployment is ready.
"""
import concurrent.futures,http.cookiejar,json,time,uuid,subprocess
from pathlib import Path
import urllib.request,urllib.parse,urllib.error

OUT=Path('/opt/banking-research/live');OUT.mkdir(parents=True,exist_ok=True)
BASE='http://127.0.0.1:8080'
class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,*args,**kwargs):return None

def main():
    jar=http.cookiejar.CookieJar()
    login=urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    with login.open(urllib.request.Request(BASE+'/login',data=urllib.parse.urlencode({'username':'testuser','password':'bankofanthos'}).encode()),timeout=20) as response:response.read()
    token=next(c.value for c in jar if c.name=='token')
    rows=[];baseline=[];started=time.time();resource_samples=[];resource_reference=None
    def kube(*args):return subprocess.check_output(['kubectl','-n','banking-probe-research',*args],text=True,timeout=6)
    def resources():
        observed={};begun=time.time()
        try:
            pods=json.loads(kube('get','pods','-o','json'))['items']
            for pod in pods:
                service=pod['metadata']['labels'].get('app')
                if service not in ('frontend','ledgerwriter','ledger-db','balancereader') or pod.get('status',{}).get('phase')!='Running':continue
                cid=pod['status']['containerStatuses'][0]['containerID'].split('://')[1]
                details=json.loads(subprocess.check_output(['k3s','crictl','inspect',cid],text=True,timeout=4))
                pid=details['info']['pid'];relative=Path(f'/proc/{pid}/cgroup').read_text().split('0::',1)[1].strip()
                folder=Path('/sys/fs/cgroup'+relative)
                observed[service]={name:(folder/name).read_text().strip() for name in ('cpu.max','cpu.stat','memory.current','memory.max')}
        except (OSError,KeyError,ValueError,subprocess.SubprocessError):pass
        return {'timestamp':begun,'instrument':'periodic_snapshot','cgroups':observed,'collection_elapsed_ms':(time.time()-begun)*1000}

    def payment(_):
        stamp=time.time();clock=time.monotonic();operation=uuid.uuid4().hex
        request=urllib.request.Request(BASE+'/payment',data=urllib.parse.urlencode({'account_num':'1033623433','amount':'0.01','uuid':operation}).encode(),headers={'Cookie':'token='+token,'Content-Type':'application/x-www-form-urlencoded'})
        row={'timestamp':stamp,'operation_uuid':operation,'amount_cents':1,'outcome':'uncertain'}
        try:
            client=urllib.request.build_opener(NoRedirect())
            try:response=client.open(request,timeout=8)
            except urllib.error.HTTPError as exc:response=exc
            with response:
                location=response.headers.get('Location','')
                message=urllib.parse.parse_qs(urllib.parse.urlsplit(location).query).get('msg',[''])[0]
                response.read()
                row.update(http_status=response.code,outcome='acknowledged_success' if message.lower()=='payment successful' else 'not_acknowledged_success')
        except (OSError,ValueError) as exc:row['error']=type(exc).__name__
        row.update(latency_ms=(time.monotonic()-clock)*1000,completed_at=time.time())
        return row
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        while time.time()-started<5400 and not (OUT/'STOP').exists():
            batch=list(pool.map(payment,range(3)))
            with (OUT/'requests.jsonl').open('a') as stream:
                for row in batch:stream.write(json.dumps(row)+'\n')
            rows.extend(batch);rows=rows[-180:]
            if len(baseline)<30:baseline.extend(batch)
            try:
                query="SELECT count(*) FROM pg_stat_activity WHERE datname=current_database() AND cardinality(pg_blocking_pids(pid))>0;"
                blocked=int(subprocess.check_output(['kubectl','-n','banking-probe-research','exec','statefulset/ledger-db','--','psql','-U','admin','-d','postgresdb','-At','-c',query],text=True,timeout=5).strip())
                locks=json.loads(kube('exec','statefulset/ledger-db','--','psql','-U','admin','-d','postgresdb','-At','-c',"SELECT COALESCE(json_agg(t),'[]'::json) FROM (SELECT l.pid,l.mode,l.granted,EXTRACT(EPOCH FROM clock_timestamp()-l.waitstart)*1000 AS lock_wait_ms,c.relname AS relation FROM pg_locks l LEFT JOIN pg_class c ON c.oid=l.relation WHERE (NOT l.granted OR (l.mode='AccessExclusiveLock' AND c.relname='transactions'))) t;"))
                database={'timestamp':time.time(),'blocked_sessions':blocked,'locks':locks}
            except (OSError,ValueError,subprocess.SubprocessError):database={'status':'unavailable'}
            resource_samples.append(resources());resource_samples=resource_samples[-3:]
            if resource_reference is None and len(baseline)>=30:resource_reference=resource_samples[-1]
            spans=[]
            try:
                for line in kube('logs','deployment/frontend','--tail=200').splitlines():
                    if 'RESEARCH_SPAN ' in line:
                        span=json.loads(line.split('RESEARCH_SPAN ',1)[1])
                        if span.get('kind')=='CLIENT' and time.time()-span['end_time_unix_ns']/1e9<20:spans.append(span)
            except (ValueError,OSError,subprocess.SubprocessError):pass
            snapshot={'source':'executed-aws-bank-of-anthos','started_at':started,'requests':rows,'baseline':baseline[:30],'database':database,'resource_samples':resource_samples,'resource_reference':resource_reference,'client_spans':spans[-12:]}
            temporary=OUT/'snapshot.partial';temporary.write_text(json.dumps(snapshot));temporary.replace(OUT/'snapshot.json')
            time.sleep(1)

if __name__=='__main__':main()
