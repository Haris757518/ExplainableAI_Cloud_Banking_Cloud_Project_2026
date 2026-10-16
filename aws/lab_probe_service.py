"""Measured lab health probes on EC2. No fabricated users, transactions or metrics."""
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import os
from pathlib import Path
import threading
import time
from urllib.request import urlopen
import boto3
from botocore.config import Config
import psycopg

INSTANCE_ID=os.environ['OBSERVER_INSTANCE_ID']
REGION=os.environ.get('AWS_REGION','us-east-1')
SERVICE='observed-lab-probe'
STORE=Path('/var/lib/explainableai-observer/observations.jsonl')
CW=boto3.client('cloudwatch',region_name=REGION,config=Config(connect_timeout=3,read_timeout=5,retries={'max_attempts':1}))
LATEST={}
LOCK=threading.Lock()


def probe():
    started=time.perf_counter()
    observed=datetime.now(timezone.utc)
    report={'observed_at':observed.isoformat(),'instance_id':INSTANCE_ID,'source':'aws_ec2_measured_lab_probe',
            'workload':'read-only SELECT 1 against isolated lab monitoring database','banking_transaction':False}
    try:
        connect_start=time.perf_counter()
        with psycopg.connect(dbname='xai_observability',user='xaiobserver',host='/var/run/postgresql',connect_timeout=3) as connection:
            report['db_connection_ms']=(time.perf_counter()-connect_start)*1000
            connection.execute("SET TRANSACTION READ ONLY")
            query_start=time.perf_counter()
            value=connection.execute('SELECT 1').fetchone()[0]
            report['db_query_ms']=(time.perf_counter()-query_start)*1000
            if value!=1:
                raise RuntimeError('Unexpected database probe result')
        report['db_roundtrip_ms']=(time.perf_counter()-connect_start)*1000
        report['success']=True
    except Exception as exc:
        report['success']=False
        report['error_type']=type(exc).__name__
    report['request_latency_ms']=(time.perf_counter()-started)*1000
    data=[{'MetricName':'RequestLatencyMilliseconds','Value':report['request_latency_ms'],'Unit':'Milliseconds'},
          {'MetricName':'RequestCount','Value':1,'Unit':'Count'},
          {'MetricName':'ErrorCount','Value':int(not report['success']),'Unit':'Count'}]
    for field,name in [('db_connection_ms','DBConnectionMilliseconds'),('db_query_ms','DBQueryMilliseconds'),('db_roundtrip_ms','DBRoundTripMilliseconds')]:
        if field in report:
            data.append({'MetricName':name,'Value':report[field],'Unit':'Milliseconds'})
    for item in data:
        item.update({'Timestamp':observed,'StorageResolution':60,'Dimensions':[{'Name':'InstanceId','Value':INSTANCE_ID},{'Name':'Service','Value':SERVICE}]})
    try:
        CW.put_metric_data(Namespace='ExplainableAI/ObservedLab',MetricData=data)
        report['cloudwatch_published']=True
    except Exception as exc:
        report['cloudwatch_published']=False
        report['publish_error_type']=getattr(exc,'response',{}).get('Error',{}).get('Code',type(exc).__name__)
    # Export timing boundaries explicitly: publishing and logging are not included
    # in the application/DB execution timers and are never labeled network latency.
    report['timing_scope']='DB/application probe execution; excludes metric publishing and audit logging'
    with LOCK:
        LATEST.clear();LATEST.update(report)
        with STORE.open('a',encoding='utf-8') as stream:
            stream.write(json.dumps(report)+'\n')
    return report


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path in ('/health','/probe'):
            result=probe();status=200 if result['success'] else 503
        elif self.path=='/metrics':
            with LOCK:
                result=dict(LATEST)
            status=200
        else:
            result={'error':'Not found'};status=404
        payload=json.dumps(result).encode()
        self.send_response(status);self.send_header('Content-Type','application/json');self.send_header('Content-Length',str(len(payload)));self.end_headers();self.wfile.write(payload)
    def log_message(self,*args):
        pass


def scheduled_probe():
    while True:
        try:
            probe()
        except Exception:
            pass
        time.sleep(60)


if __name__=='__main__':
    threading.Thread(target=scheduled_probe,daemon=True).start()
    ThreadingHTTPServer(('127.0.0.1',8080),Handler).serve_forever()
