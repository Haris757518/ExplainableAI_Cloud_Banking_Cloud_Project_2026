"""Execute one local demo-cent transfer and verify its exact ledger/history ID.

Requires a healthy prepared deployment and localhost frontend port forward.
Never starts a cluster, changes resources, injects faults, or calls AWS.
"""
import datetime
import argparse
import hashlib
import http.cookiejar
import json
from pathlib import Path
import subprocess
import time
import urllib.parse
import urllib.request
import uuid

NAMESPACE = 'banking-probe-research'
BASE = 'http://127.0.0.1:8080'
OUT = Path(r'D:\BankingResearch\Telemetry\normal')
CONTEXT = 'docker-desktop'


def kubectl(*args, stdin=None):
    result = subprocess.run(['kubectl', '--context', CONTEXT, *args],
                            input=stdin, capture_output=True, text=True, check=True)
    return result.stdout


def sql(query):
    return kubectl('-n', NAMESPACE, 'exec', 'statefulset/ledger-db', '--',
                   'psql', '-U', 'admin', '-d', 'postgresdb', '-At', '-c', query).strip()


def main():
    global CONTEXT, OUT
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--environment',choices=['local','aws'],default='local')
    parser.add_argument('--out',type=Path)
    parser.add_argument('--source-instance')
    args=parser.parse_args()
    if args.out:OUT=args.out
    if args.environment=='aws':
        if not args.source_instance:raise RuntimeError('AWS execution requires an expected source instance')
        token_req=urllib.request.Request('http://169.254.169.254/latest/api/token',method='PUT',headers={'X-aws-ec2-metadata-token-ttl-seconds':'60'})
        with urllib.request.urlopen(token_req,timeout=5) as response:metadata_token=response.read().decode()
        id_req=urllib.request.Request('http://169.254.169.254/latest/meta-data/instance-id',headers={'X-aws-ec2-metadata-token':metadata_token})
        with urllib.request.urlopen(id_req,timeout=5) as response:observed_instance=response.read().decode()
        if observed_instance!=args.source_instance:raise RuntimeError('Actual source instance differs from the approved source')
        CONTEXT='default'
    server = kubectl('config', 'view', '--minify', '-o',
                     'jsonpath={.clusters[0].cluster.server}').strip()
    parsed = urllib.parse.urlsplit(server)
    if parsed.hostname not in ('kubernetes.docker.internal', '127.0.0.1', 'localhost'):
        raise RuntimeError('Refusing a non-local Kubernetes endpoint')
    replicas = kubectl('-n', NAMESPACE, 'get', 'deployment/loadgenerator', '-o',
                       'jsonpath={.spec.replicas}').strip()
    if replicas != '0':
        raise RuntimeError('Stop automatic traffic before the first transfer check')
    run = OUT / ('first-transfer-' + datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%SZ'))
    run.mkdir(parents=True, exist_ok=False)
    jar = http.cookiejar.CookieJar()
    client = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    requests = []
    trace_id = uuid.uuid4().hex

    def request(path, form=None):
        payload = urllib.parse.urlencode(form).encode() if form is not None else None
        req = urllib.request.Request(BASE + path, data=payload,
            headers={'traceparent': '00-' + trace_id + '-' + uuid.uuid4().hex[:16] + '-01'})
        start_ns = time.time_ns()
        start = time.perf_counter()
        with client.open(req, timeout=60) as response:
            body = response.read()
            requests.append({'path':path,'method':'POST' if form is not None else 'GET',
                'start_time_unix_ns':start_ns,'elapsed_ms':(time.perf_counter()-start)*1000,
                'final_status':response.status,'final_path':urllib.parse.urlsplit(response.url).path})
            return body

    report = {'source':'executed-'+args.environment+'-bank-of-anthos','source_instance':args.source_instance,'status':'incomplete',
              'trace_id':trace_id,'requests':requests,'aws_calls':0}
    try:
        request('/login', {'username':'testuser','password':'bankofanthos'})
        token = next((c.value for c in jar if c.name == 'token'), None)
        if not token:
            raise RuntimeError('Demo login did not return a session')
        previous_id = int(sql('SELECT COALESCE(MAX(transaction_id),0) FROM transactions;'))
        operation = uuid.uuid4().hex
        html = request('/payment', {'account_num':'1033623433','amount':'0.01','uuid':operation})
        (run/'payment-response.html').write_bytes(html)
        rows = json.loads(sql("SELECT COALESCE(json_agg(t),'[]'::json) FROM (SELECT * FROM transactions WHERE transaction_id > "
            + str(previous_id) + " AND from_acct='1011226111' AND to_acct='1033623433' AND amount=1) t;"))
        (run/'ledger-new-transfer.json').write_text(json.dumps(rows,indent=2))
        if len(rows) != 1:
            raise RuntimeError('Expected exactly one matching new ledger record')
        transaction_id = rows[0]['transaction_id']
        history_script = ("import sys,json,requests; p=json.load(sys.stdin); "
            "r=requests.get('http://transactionhistory:8080/transactions/1011226111',"
            "headers={'Authorization':'Bearer '+p['token']},timeout=15); "
            "r.raise_for_status(); print(r.text)")
        history = None
        for attempt in range(15):
            history = json.loads(kubectl('-n',NAMESPACE,'exec','-i','deployment/frontend','--',
                'python','-c',history_script,stdin=json.dumps({'token':token})))
            if any(t.get('transactionId') == transaction_id for t in history):
                break
            time.sleep(2)
        else:
            raise RuntimeError('New ledger transaction was not observed in history')
        (run/'transaction-history.json').write_text(json.dumps(history,indent=2))
        request('/home')
        # Allow the local batched span exporter to flush before collecting logs.
        time.sleep(2)
        logs = kubectl('-n',NAMESPACE,'logs','deployment/frontend','--since=10m')
        (run/'frontend-raw.log').write_text(logs,encoding='utf-8')
        spans = []
        for line in logs.splitlines():
            if line.startswith('RESEARCH_SPAN '):
                span = json.loads(line[len('RESEARCH_SPAN '):])
                if span['trace_id'] == trace_id:
                    spans.append(span)
        (run/'frontend-spans.json').write_text(json.dumps(spans,indent=2))
        payment_spans = {s['span_id'] for s in spans if s['kind']=='SERVER'
                         and s['attributes'].get('http.route')=='/payment'}
        clients = [s for s in spans if s['kind']=='CLIENT'
                   and s['parent_span_id'] in payment_spans
                   and urllib.parse.urlsplit(s['attributes'].get('url.full',
                       s['attributes'].get('http.url',''))).hostname=='ledgerwriter']
        if not clients:
            raise RuntimeError('Transfer recorded, but no associated measured client spans were captured')
        report.update(status='verified',transaction_id=transaction_id,operation_uuid=operation,
            ledger_new_records=len(rows),history_record_found=True,measured_client_spans=len(clients),
            trace_coverage='frontend server/client only; no backend server or database spans',
            recovery_verified=False)
    except Exception as error:
        report.update(status='failed',error=type(error).__name__ + ': ' + str(error))
        raise
    finally:
        report['files_sha256'] = {p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                  for p in run.iterdir() if p.is_file()}
        (run/'verification.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
        print('Verification status:',report['status'],'Evidence:',run)


if __name__ == '__main__':
    main()
