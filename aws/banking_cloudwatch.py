"""Independent banking custom-metric reads; never join local banking to EC2/RDS."""
from datetime import datetime, timezone, timedelta
from statistics import median
from aws.banking_publisher import NAMESPACE, ENVIRONMENT, OPERATIONS, METRICS, client, dimensions, finite, safe_error

CUTOFF = datetime(2026, 10, 16, 8, 5, tzinfo=timezone.utc)

def collect(region, profile=None, lookback_minutes=1440, cw=None):
    if not 1 <= lookback_minutes <= 20160:
        raise ValueError('Lookback must be 1–20160 minutes.')
    now = datetime.now(timezone.utc)
    start = max(now-timedelta(minutes=lookback_minutes), CUTOFF)
    result = {'status': 'pending_or_insufficient_data', 'namespace': NAMESPACE, 'region': region,
              'source': 'aws_cloudwatch', 'workload_origin': 'local_measured_banking',
              'environment': ENVIRONMENT, 'hosting': 'local', 'period_seconds': 60,
              'collected_at': now.isoformat(), 'start': start.isoformat(), 'end': now.isoformat(),
              'series': [], 'errors': [], 'api_calls': 0, 'collection_complete': False,
              'exclusion_policy': {'not_before': CUTOFF.isoformat(), 'reason': 'Earlier controlled AWS trials remain excluded.'},
              'resource_relationship': 'not_established'}
    queries, targets = [], {}
    for op in OPERATIONS:
        specs = [('banking-api', n) for n in ('RequestCount', 'ErrorCount', 'RequestLatencyMilliseconds', 'ClientLatencyMilliseconds')]
        for service in ('banking-api', 'account-service', 'ledger-service'):
            specs += [(service, 'ServiceLatencyMilliseconds'), (service, 'ExclusiveProcessingMilliseconds')]
        specs += [('banking-db', 'DBQueryMilliseconds'), ('banking-db', 'DBConnectionMilliseconds')]
        for service, name in specs:
            key = f'b{len(queries)}'; unit, stat = METRICS[name]; dims = dimensions(service, op)
            queries.append({'Id': key, 'MetricStat': {'Metric': {'Namespace': NAMESPACE, 'MetricName': name, 'Dimensions': dims}, 'Period': 60, 'Stat': stat, 'Unit': unit}, 'ReturnData': True})
            targets[key] = {'service': service, 'operation': op, 'metric_name': name, 'unit': unit,
                            'statistic': stat, 'dimensions': dims, 'source': 'aws_cloudwatch', 'period_seconds': 60,
                            'points': {}, 'response_status': 'omitted', 'messages': []}
    try:
        cw = cw or client(region, profile)
        token, seen = None, set()
        for _ in range(20):
            args = dict(MetricDataQueries=queries, StartTime=start, EndTime=now, ScanBy='TimestampAscending', MaxDatapoints=100800)
            if token: args['NextToken'] = token
            response = cw.get_metric_data(**args); result['api_calls'] += 1
            result['errors'].extend({'code': m.get('Code', 'CloudWatchMessage')} for m in response.get('Messages', []))
            for entry in response.get('MetricDataResults', []):
                if entry.get('Id') not in targets:
                    result['errors'].append({'code': 'UnknownMetricId'}); continue
                target = targets[entry['Id']]
                target['response_status'] = entry.get('StatusCode', 'omitted')
                target['messages'].extend({'code': m.get('Code', 'CloudWatchMessage')} for m in entry.get('Messages', []))
                if len(entry.get('Timestamps', [])) != len(entry.get('Values', [])):
                    result['errors'].append({'code': 'MismatchedMetricLengths'}); continue
                if target['response_status'] not in ('Complete', 'PartialData'): continue
                for ts, value in zip(entry.get('Timestamps', []), entry.get('Values', [])):
                    if isinstance(ts, datetime) and ts.tzinfo and start <= ts <= now and finite(value):
                        target['points'][ts.isoformat()] = float(value)
            token = response.get('NextToken')
            if not token: break
            if token in seen: raise ValueError('Repeated pagination token.')
            seen.add(token)
        else:
            raise ValueError('Pagination safety limit reached.')
    except Exception as exc:
        result['errors'].append({'code': safe_error(exc)})
    for row in targets.values():
        row['points'] = [{'timestamp': ts, 'value': v} for ts, v in sorted(row['points'].items())]
        row['missing_data'] = not bool(row['points'])
        result['series'].append(row)
    result['collection_complete'] = not result['errors'] and all(r['response_status'] == 'Complete' and not r['messages'] for r in result['series'])
    result['observed_series'] = sum(not r['missing_data'] for r in result['series'])
    result['status'] = ('observations_available' if result['collection_complete'] else 'partial_collection') if result['observed_series'] else ('collection_unavailable' if result['errors'] else 'pending_or_insufficient_data')
    result['investigation'] = investigate(result)
    return result

def investigate(collection):
    findings = []
    for series in collection['series']:
        if series['metric_name'] not in ('RequestLatencyMilliseconds', 'ServiceLatencyMilliseconds', 'ExclusiveProcessingMilliseconds', 'DBQueryMilliseconds'):
            continue
        points = series['points']
        if len(points) < 10 or series['response_status'] != 'Complete' or not collection['collection_complete']:
            continue
        split = max(6, int(len(points)*0.6)); base = [p['value'] for p in points[:split]]
        normal = median(base); mad = median([abs(v-normal) for v in base])
        threshold = normal + max(5.0, normal*.5, 6*1.4826*mad)
        recent = points[-2:]
        freshness = (datetime.fromisoformat(collection['end'])-datetime.fromisoformat(recent[-1]['timestamp'])).total_seconds()
        abnormal = freshness <= 180 and all(p['value'] > threshold for p in recent)
        findings.append({'service': series['service'], 'operation': series['operation'], 'metric': series['metric_name'],
                         'baseline_median': normal, 'threshold': threshold, 'latest': recent[-1]['value'],
                         'latest_timestamp': recent[-1]['timestamp'], 'fresh': freshness <= 180,
                         'status': 'abnormal_latency' if abnormal else ('no_deviation_in_observed_series' if freshness <= 180 else 'historical_evidence_only')})
    abnormal = [f for f in findings if f['status'] == 'abnormal_latency']
    return {'status': 'abnormal_latency' if abnormal else ('observations_evaluated' if findings else 'insufficient_evidence'),
            'findings': findings, 'affected_services': sorted({f['service'] for f in abnormal}),
            'root_cause': 'not_established', 'gnn_used': False,
            'explanation': 'Independent 60-second CloudWatch averages; earliest 60% baseline, median/MAD threshold, two-point persistence. Stale data cannot establish a current anomaly. Aggregates cannot prove a transaction-level mechanism.',
            'corrective_actions': ['Compare service exclusive processing with database execution in matched local traces.', 'Collect additional normal windows and fresh follow-up measurements before confirming a cause.'],
            'followup_verification': 'not_established'}
