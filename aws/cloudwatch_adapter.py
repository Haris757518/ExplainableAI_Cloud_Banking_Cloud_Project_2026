from __future__ import annotations
from datetime import datetime, timedelta, timezone
import math
import boto3
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

EC2_METRICS = {
    'CPUUtilization': {'target': 'cpu_percent', 'unit': 'Percent', 'stat': 'Average'},
    'NetworkIn': {'target': 'network_in_bytes', 'unit': 'Bytes', 'stat': 'Sum'},
    'NetworkOut': {'target': 'network_out_bytes', 'unit': 'Bytes', 'stat': 'Sum'},
    'DiskReadOps': {'target': 'disk_read_ops', 'unit': 'Count', 'stat': 'Sum'},
    'DiskWriteOps': {'target': 'disk_write_ops', 'unit': 'Count', 'stat': 'Sum'},
}
RDS_METRICS = {
    'CPUUtilization': {'target': 'cpu_percent', 'unit': 'Percent', 'stat': 'Average'},
    'DatabaseConnections': {'target': 'db_connections', 'unit': 'Count', 'stat': 'Average'},
    'ReadLatency': {'target': 'read_latency_s', 'unit': 'Seconds', 'stat': 'Average'},
    'WriteLatency': {'target': 'write_latency_s', 'unit': 'Seconds', 'stat': 'Average'},
    'ReadIOPS': {'target': 'read_iops', 'unit': 'Count/Second', 'stat': 'Average'},
    'WriteIOPS': {'target': 'write_iops', 'unit': 'Count/Second', 'stat': 'Average'},
    'FreeableMemory': {'target': 'freeable_memory_bytes', 'unit': 'Bytes', 'stat': 'Average'},
    'FreeStorageSpace': {'target': 'free_storage_bytes', 'unit': 'Bytes', 'stat': 'Average'},
    'NetworkReceiveThroughput': {'target': 'network_receive_bytes_s', 'unit': 'Bytes/Second', 'stat': 'Average'},
    'NetworkTransmitThroughput': {'target': 'network_transmit_bytes_s', 'unit': 'Bytes/Second', 'stat': 'Average'},
    'DiskQueueDepth': {'target': 'disk_queue_depth', 'unit': 'Count', 'stat': 'Average'},
}
APPLICATION_METRICS = {
    'RequestLatencyMilliseconds': {'target':'latency_ms','unit':'Milliseconds','stat':'Average'},
    'DBConnectionMilliseconds': {'target':'db_connection_ms','unit':'Milliseconds','stat':'Average'},
    'DBQueryMilliseconds': {'target':'db_query_ms','unit':'Milliseconds','stat':'Average'},
    'DBRoundTripMilliseconds': {'target':'db_roundtrip_ms','unit':'Milliseconds','stat':'Average'},
    'RequestCount': {'target':'request_count','unit':'Count','stat':'Sum'},
    'ErrorCount': {'target':'error_count','unit':'Count','stat':'Sum'},
}


class CloudWatchAdapter:
    """Read-only batched and paginated collection; missing datapoints stay missing."""
    def __init__(self, region, lookback_minutes=15, period_seconds=60, profile=None, client=None):
        if period_seconds < 60 or period_seconds % 60:
            raise ValueError('Native EC2/RDS metric period must be a positive multiple of 60 seconds.')
        if not 1 <= lookback_minutes <= 20160:
            raise ValueError('Lookback must be between 1 minute and 14 days.')
        self.region, self.lookback_minutes, self.period_seconds = region, lookback_minutes, period_seconds
        if client is None:
            session = boto3.Session(region_name=region, profile_name=profile or None)
            client = session.client('cloudwatch', region_name=region, config=Config(connect_timeout=4, read_timeout=15, retries={'max_attempts': 2}))
        self.client = client

    def collect(self, ec2_ids, rds_ids, include_application=False):
        end = datetime.now(timezone.utc)
        end = datetime.fromtimestamp((int(end.timestamp()) // self.period_seconds) * self.period_seconds, tz=timezone.utc)
        start = end - timedelta(minutes=self.lookback_minutes)
        result = {'region': self.region, 'timestamp': end.isoformat(), 'period_seconds': self.period_seconds,
                  'lookback_minutes': self.lookback_minutes, 'source': 'aws_cloudwatch', 'ec2': [], 'rds': [], 'application': [], 'errors': [], 'api_calls': 0}
        queries, targets = [], {}
        for group, ids, namespace, dimension, metric_map in [('ec2', ec2_ids, 'AWS/EC2', 'InstanceId', EC2_METRICS), ('rds', rds_ids, 'AWS/RDS', 'DBInstanceIdentifier', RDS_METRICS)]:
            for rid in dict.fromkeys(ids):
                item = {'node_id': rid, 'source': 'aws_cloudwatch', 'period_seconds': self.period_seconds, 'metrics': {}, 'observed_metrics': [], 'series': [], 'error': None}
                result[group].append(item)
                for name, spec in metric_map.items():
                    qid = f'm{len(queries)}'
                    queries.append({'Id': qid, 'MetricStat': {'Metric': {'Namespace': namespace, 'MetricName': name, 'Dimensions': [{'Name': dimension, 'Value': rid}]}, 'Period': self.period_seconds, 'Stat': spec['stat']}, 'ReturnData': True})
                    targets[qid] = (item, name, spec, {})
        if include_application:
            for rid in dict.fromkeys(ec2_ids):
                item={'node_id':rid,'source':'aws_cloudwatch','period_seconds':self.period_seconds,'metrics':{},'observed_metrics':[],'series':[],'error':None}
                result['application'].append(item)
                for name,spec in APPLICATION_METRICS.items():
                    qid=f'm{len(queries)}'
                    queries.append({'Id':qid,'MetricStat':{'Metric':{'Namespace':'ExplainableAI/ObservedLab','MetricName':name,'Dimensions':[{'Name':'InstanceId','Value':rid},{'Name':'Service','Value':'observed-lab-probe'}]},'Period':self.period_seconds,'Stat':spec['stat']},'ReturnData':True})
                    targets[qid]=(item,name,spec,{})
        statuses = {}
        returned = set()
        for offset in range(0, len(queries), 500):
            token, seen_tokens = None, set()
            try:
                while True:
                    kwargs = {'MetricDataQueries': queries[offset:offset+500], 'StartTime': start, 'EndTime': end, 'ScanBy': 'TimestampAscending', 'MaxDatapoints': 100800}
                    if token:
                        kwargs['NextToken'] = token
                    response = self.client.get_metric_data(**kwargs)
                    result['api_calls'] += 1
                    result['errors'].extend(response.get('Messages', []))
                    for entry in response.get('MetricDataResults', []):
                        if entry.get('Id') not in targets:
                            result['errors'].append({'code': 'UnknownMetricId'})
                            continue
                        returned.add(entry['Id'])
                        statuses[entry['Id']] = entry.get('StatusCode', 'Complete')
                        if len(entry.get('Timestamps', [])) != len(entry.get('Values', [])):
                            result['errors'].append({'code': 'MismatchedMetricLengths', 'metric_id': entry['Id']})
                        item, name, spec, points = targets[entry['Id']]
                        if entry.get('StatusCode', 'Complete') not in ('Complete', 'PartialData'):
                            item['error'] = entry.get('StatusCode')
                            result['errors'].append({'resource': item['node_id'], 'metric': name, 'status': item['error']})
                            continue
                        for ts, value in zip(entry.get('Timestamps', []), entry.get('Values', [])):
                            if isinstance(ts, datetime) and ts.tzinfo is not None and isinstance(value, (int, float)) and math.isfinite(value) and value >= 0:
                                points[ts.isoformat()] = float(value)
                    token = response.get('NextToken')
                    if not token:
                        break
                    if token in seen_tokens:
                        raise ValueError('CloudWatch repeated a pagination token.')
                    seen_tokens.add(token)
            except (BotoCoreError, ClientError, ValueError) as exc:
                result['errors'].append({'code': type(exc).__name__, 'message': 'CloudWatch collection failed or was incomplete.'})
        for qid in targets:
            if qid not in returned or statuses.get(qid) != 'Complete':
                result['errors'].append({'code': 'IncompleteMetricResponse', 'metric_id': qid, 'status': statuses.get(qid, 'omitted')})
        for item, name, spec, points in targets.values():
            if not points:
                continue
            ordered = sorted(points.items())
            item['metrics'][spec['target']] = ordered[-1][1]
            item['observed_metrics'].append(spec['target'])
            item['series'].append({'metric_name': name, 'target': spec['target'], 'unit': spec['unit'], 'stat': spec['stat'],
                                   'value': ordered[-1][1], 'timestamp': ordered[-1][0],
                                   'points': [{'timestamp': ts, 'value': v} for ts, v in ordered]})
        result['observed_metric_count'] = sum(len(item['observed_metrics']) for group in ('ec2', 'rds', 'application') for item in result[group])
        return result

    def collect_ec2(self, rid):
        return self.collect([rid], [])['ec2'][0]

    def collect_rds(self, rid):
        return self.collect([], [rid])['rds'][0]
