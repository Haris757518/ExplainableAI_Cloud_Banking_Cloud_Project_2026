"""Explicit, bounded publication of existing measured banking rows only.

CloudWatch has no idempotency key. An uncertain network outcome is therefore
persisted as ambiguous and blocks retries, rather than risking duplicate counts.
"""
from __future__ import annotations
import hashlib
import json
import math
import os
import sqlite3
from contextlib import closing
from datetime import datetime, timezone, timedelta
from pathlib import Path
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

NAMESPACE = 'ExplainableAI/Banking'
ENVIRONMENT = 'academic-local-test'
DEMO_ENVIRONMENT = 'academic-local-demo-10s'
OPERATIONS = ('balance', 'transfer', 'history')
SERVICES = ('banking-api', 'account-service', 'ledger-service', 'banking-db')
METRICS = {
    'RequestCount': ('Count', 'Sum'), 'ErrorCount': ('Count', 'Sum'),
    'RequestLatencyMilliseconds': ('Milliseconds', 'Average'),
    'ClientLatencyMilliseconds': ('Milliseconds', 'Average'),
    'ServiceLatencyMilliseconds': ('Milliseconds', 'Average'),
    'ExclusiveProcessingMilliseconds': ('Milliseconds', 'Average'),
    'DBQueryMilliseconds': ('Milliseconds', 'Average'),
    'DBConnectionMilliseconds': ('Milliseconds', 'Average'),
}

def client(region, profile=None, write=False):
    # Automatic retries of PutMetricData can double counts after a lost response.
    return boto3.Session(region_name=region, profile_name=profile or None).client(
        'cloudwatch', config=Config(connect_timeout=4, read_timeout=12,
                                   retries={'total_max_attempts': 1 if write else 2}))

def safe_error(exc):
    return getattr(exc, 'response', {}).get('Error', {}).get('Code', type(exc).__name__)

def connect_readonly(path):
    path = Path(path).resolve()
    if not path.is_file():
        raise ValueError('Measured telemetry database does not exist.')
    db = sqlite3.connect(path.as_uri() + '?mode=ro', uri=True, timeout=5)
    db.row_factory = sqlite3.Row
    db.execute('PRAGMA query_only=ON')
    return db

def finite(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value) and value >= 0

def dimensions(service, operation):
    return [{'Name': 'Environment', 'Value': ENVIRONMENT},
            {'Name': 'Service', 'Value': service}, {'Name': 'Operation', 'Value': operation}]

def metric(name, value, ts, service, operation):
    if not finite(value) or not finite(ts):
        raise ValueError('Invalid measured metric or timestamp; publication stopped.')
    return {'MetricName': name, 'Dimensions': dimensions(service, operation),
            'Timestamp': datetime.fromtimestamp(ts, timezone.utc),
            'Value': float(value), 'Unit': METRICS[name][0], 'StorageResolution': 60}

def row_metrics(db, row):
    op, ts = row['operation'], row['ts']
    if op not in OPERATIONS or row['success'] not in (0, 1):
        raise ValueError('Unsupported measured request; publication stopped without skipping it.')
    values = [metric('RequestCount', 1, ts, 'banking-api', op),
              metric('ErrorCount', 1-row['success'], ts, 'banking-api', op),
              metric('RequestLatencyMilliseconds', row['duration_ms'], ts, 'banking-api', op)]
    if row['client_latency_ms'] is not None:
        values.append(metric('ClientLatencyMilliseconds', row['client_latency_ms'], ts, 'banking-api', op))
    spans = db.execute('SELECT payload FROM spans WHERE trace_id=? ORDER BY end,id LIMIT 513', (row['trace_id'],)).fetchall()
    if len(spans) > 512:
        raise ValueError('Span safety limit exceeded; request was not published.')
    for raw in spans:
        span = json.loads(raw['payload'])
        service, kind = span.get('service'), span.get('kind')
        if service not in SERVICES or span.get('operation') != op:
            raise ValueError('Unrecognized span provenance; request was not published.')
        stamp = span.get('end')
        if kind == 'server' and service != 'banking-db':
            for key, name in [('duration_ms', 'ServiceLatencyMilliseconds'), ('exclusive_ms', 'ExclusiveProcessingMilliseconds')]:
                if span.get(key) is not None:
                    values.append(metric(name, span[key], stamp, service, op))
        elif service == 'banking-db' and kind in ('database', 'connection'):
            values.append(metric('DBQueryMilliseconds' if kind == 'database' else 'DBConnectionMilliseconds',
                                 span.get('duration_ms'), stamp, service, op))
    if len(values) > 1000:
        raise ValueError('CloudWatch batch limit exceeded; no partial request was published.')
    return values

def source_id(db, path):
    first = db.execute('SELECT trace_id,ts FROM requests ORDER BY seq LIMIT 1').fetchone()
    return hashlib.sha256(json.dumps([str(Path(path).resolve()), list(first) if first else None]).encode()).hexdigest()

def publisher(db_path, checkpoint, region, profile=None, publish=False, limit=10, cw=None,
              environment=ENVIRONMENT, storage_resolution=60, allowed_sequences=None):
    if (environment, storage_resolution) not in ((ENVIRONMENT, 60), (DEMO_ENVIRONMENT, 1)):
        raise ValueError('Use the standard environment at 60 seconds or the isolated demo environment at 1 second.')
    if storage_resolution == 1 and (not allowed_sequences or len(allowed_sequences) > 60):
        raise ValueError('High-resolution publication requires a bounded manifest of at most 60 new request sequences.')
    if allowed_sequences is not None and any(type(seq) is not int or seq < 1 for seq in allowed_sequences):
        raise ValueError('Invalid request manifest.')
    if not 1 <= limit <= 20:
        raise ValueError('Publication limit must be 1–20 measured requests per invocation.')
    path = Path(checkpoint)
    state = sqlite3.connect(path, timeout=2, isolation_level=None)
    try:
        state.execute('CREATE TABLE IF NOT EXISTS publication(source TEXT,region TEXT,last_seq INTEGER NOT NULL DEFAULT 0,pending_seq INTEGER,PRIMARY KEY(source,region))')
        # Reserve the checkpoint for this complete invocation; concurrent publishers fail closed.
        state.execute('BEGIN IMMEDIATE')
        with closing(connect_readonly(db_path)) as db:
            sid = source_id(db, db_path)
            state.execute('INSERT OR IGNORE INTO publication(source,region) VALUES(?,?)', (sid, region))
            last, pending = state.execute('SELECT last_seq,pending_seq FROM publication WHERE source=? AND region=?', (sid, region)).fetchone()
            if pending is not None:
                return {'status': 'ambiguous_publication', 'pending_sequence': pending,
                        'note': 'Prior send may have reached AWS. Do not reset the checkpoint or retry blindly.', 'published_requests': 0}
            if allowed_sequences is None:
                rows = db.execute('SELECT * FROM requests WHERE seq>? ORDER BY seq LIMIT ?', (last, limit)).fetchall()
            else:
                placeholders=','.join('?' for _ in allowed_sequences)
                rows=db.execute(f'SELECT * FROM requests WHERE seq>? AND seq IN ({placeholders}) ORDER BY seq LIMIT ?', (last,*allowed_sequences,limit)).fetchall()
            prepared = [(r['seq'], row_metrics(db, r)) for r in rows]
            if storage_resolution == 1:
                for _, metrics in prepared:
                    for datum in metrics:
                        datum['StorageResolution']=1
                        datum['Dimensions']=[{**dim,'Value':environment} if dim['Name']=='Environment' else dim for dim in datum['Dimensions']]
            now = datetime.now(timezone.utc)
            if any(not now-timedelta(days=14) <= m['Timestamp'] <= now+timedelta(minutes=2) for _, metrics in prepared for m in metrics):
                return {'status': 'timestamp_outside_publication_window', 'published_requests': 0,
                        'note': 'Existing observations are outside the supported AWS timestamp window; timestamps were not rewritten.'}
            result = {'status': 'dry_run', 'namespace': NAMESPACE, 'environment': environment, 'region': region,
                      'storage_resolution': storage_resolution,
                      'source': 'local_measured_banking', 'hosting': 'local', 'request_count': len(rows),
                      'last_confirmed_sequence': last, 'publication_status': 'previous_publication_confirmed' if last else 'not_yet_published',
                      'metric_count': sum(len(v) for _, v in prepared), 'published_requests': 0,
                      'published_metric_values': 0,
                      'first_sequence': rows[0]['seq'] if rows else None,
                      'last_sequence': rows[-1]['seq'] if rows else last,
                      'metric_names': sorted({m['MetricName'] for _, v in prepared for m in v}),
                      'missing_measurements': ['memory utilization', 'packet loss', 'PostgreSQL waits'],
                      'checkpoint': 'unchanged'}
            if not publish or not rows:
                result['status'] = 'dry_run' if not publish else 'no_new_requests'
                return result
            cw = cw or client(region, profile, write=True)
            # Commit intent before the remote call. A crash after send cannot cause replay.
            for seq, metrics in prepared:
                state.execute('UPDATE publication SET pending_seq=? WHERE source=? AND region=?', (seq, sid, region))
                state.commit()
                # Exclusive file lock below protects committed-intent transitions too.
                try:
                    cw.put_metric_data(Namespace=NAMESPACE, MetricData=metrics)
                except Exception as exc:
                    code = safe_error(exc)
                    definite = isinstance(exc, ClientError) and exc.response.get('ResponseMetadata', {}).get('HTTPStatusCode', 500) < 500
                    state.execute('BEGIN IMMEDIATE')
                    if definite:
                        state.execute('UPDATE publication SET pending_seq=NULL WHERE source=? AND region=?', (sid, region))
                    state.commit()
                    return {**result, 'status': 'publication_denied' if definite else 'ambiguous_publication',
                            'error_code': code, 'checkpoint': 'successful requests only; uncertain request blocked',
                            'failed_sequence': seq}
                state.execute('BEGIN IMMEDIATE')
                state.execute('UPDATE publication SET last_seq=?,pending_seq=NULL WHERE source=? AND region=?', (seq, sid, region))
                state.commit()
                result['published_requests'] += 1
                result['published_metric_values'] += len(metrics)
                result['last_confirmed_sequence'] = seq
                result['publication_status'] = 'publication_confirmed'
            result.update(status='published', checkpoint='advanced_after_success', verification='pending_cloudwatch_read')
            return result
    finally:
        if state.in_transaction: state.rollback()
        state.close()

def run_publisher(db_path, checkpoint, region, **kwargs):
    """Cross-process lock spans remote calls and durable checkpoint commits."""
    lock = Path(str(checkpoint)+'.lock')
    lock.parent.mkdir(parents=True, exist_ok=True)
    try:
        fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    except FileExistsError:
        raise ValueError('Publisher already locked or interrupted. Inspect the checkpoint before removing a stale lock.')
    try:
        os.write(fd, str(os.getpid()).encode())
        return publisher(db_path, checkpoint, region, **kwargs)
    finally:
        os.close(fd)
        lock.unlink()
