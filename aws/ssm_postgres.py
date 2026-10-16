"""Fixed read-only PostgreSQL diagnostic command for a managed EC2 host."""
from __future__ import annotations
import json
import shlex
import time
import boto3
from botocore.config import Config

SQL = """
BEGIN READ ONLY;
SET LOCAL statement_timeout = '5000ms';
SELECT json_build_object(
 'observed_at', clock_timestamp(),
 'server_version', current_setting('server_version'),
 'track_io_timing', current_setting('track_io_timing'),
 'blocked_sessions', (SELECT COUNT(*) FROM pg_stat_activity WHERE cardinality(pg_blocking_pids(pid))>0),
 'activity', (SELECT coalesce(json_agg(s), '[]'::json) FROM (
   SELECT state, wait_event_type, wait_event, COUNT(*) AS sessions,
          MAX(EXTRACT(EPOCH FROM (clock_timestamp()-query_start))*1000) AS max_query_age_ms
   FROM pg_stat_activity WHERE pid<>pg_backend_pid() AND backend_type='client backend'
   GROUP BY state, wait_event_type, wait_event) s),
 'database_counters', (SELECT coalesce(json_agg(d), '[]'::json) FROM (
   SELECT datname, numbackends, xact_commit, xact_rollback, blks_read, blks_hit,
          deadlocks, temp_files, temp_bytes, blk_read_time, blk_write_time, stats_reset
   FROM pg_stat_database WHERE datname NOT IN ('template0','template1') AND datname IS NOT NULL) d)
);
ROLLBACK;
"""


def collect_postgres(instance_id, region, profile=None, client=None):
    if client is None:
        client=boto3.Session(region_name=region,profile_name=profile or None).client('ssm',config=Config(connect_timeout=4,read_timeout=10,retries={'max_attempts':1}))
    command='sudo -u postgres psql -X -d postgres -At -v ON_ERROR_STOP=1 -c ' + shlex.quote(SQL)
    response=client.send_command(InstanceIds=[instance_id],DocumentName='AWS-RunShellScript',TimeoutSeconds=30,
        Parameters={'commands':[command],'executionTimeout':['15']},Comment='Read-only PostgreSQL wait and blocking diagnostics; no query text or customer rows')
    command_id=response['Command']['CommandId']
    for _ in range(20):
        try:
            result=client.get_command_invocation(CommandId=command_id,InstanceId=instance_id)
        except client.exceptions.InvocationDoesNotExist:
            time.sleep(.5)
            continue
        if result['Status']=='Success':
            output=result.get('StandardOutputContent','')
            start=output.find('{')
            if start>=0:
                try:
                    payload,_=json.JSONDecoder().raw_decode(output[start:])
                except json.JSONDecodeError:
                    return {'status':'unavailable','source':'aws_ssm_postgresql','error':'PostgreSQL diagnostic output was incomplete or malformed.'}
                return {'status':'observed','source':'aws_ssm_postgresql','instance_id':instance_id,'region':region,'observation':payload,
                        'causal_confirmation':False,
                        'limitations':'Snapshot of self-hosted PostgreSQL system views, not query text or customer records. Query ages are ongoing ages, not completed request latencies. Cumulative counters need time-separated snapshots; zero I/O timing can mean timing is disabled.'}
            return {'status':'unavailable','source':'aws_ssm_postgresql','error':'No PostgreSQL system-view JSON was returned.'}
        if result['Status'] in ('Failed','Cancelled','TimedOut'):
            return {'status':'unavailable','source':'aws_ssm_postgresql','error':'The fixed PostgreSQL system-view query did not succeed. Check the postgres operating-system account, local service, psql availability, and SSM permissions.'}
        time.sleep(.5)
    return {'status':'pending','source':'aws_ssm_postgresql','error':'The bounded SSM wait elapsed; no diagnosis is assigned.'}
