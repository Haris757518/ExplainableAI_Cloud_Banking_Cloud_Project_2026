"""Normalize only measured values; topology requires explicit configuration."""
from datetime import datetime, timezone
from common.schema import AnalysisSample, GraphNode, GraphEdge, TelemetryPoint, TransactionContext


def build_aws_sample(discovery, raw, transaction_type='UPI_PAYMENT', mapping=None):
    mapping = mapping or {}
    nodes, telemetry, series = [], [], {}
    for group, kind, layer in [('ec2', 'ec2', 'compute'), ('rds', 'rds', 'data')]:
        observations = {x['node_id']: x for x in raw.get(group, [])}
        for resource in discovery.get(group, []):
            rid = resource['id']
            obs = observations.get(rid, {})
            metrics = obs.get('metrics', {})
            measured, normalized_series = {}, {}
            conversions = {'cpu_percent': ('cpu_percent', 1), 'read_latency_s': ('db_latency_ms', 1000),
                           'network_in_bytes': ('network_in_mbps', 8 / max(1, raw.get('period_seconds', 60)) / 1e6),
                           'network_out_bytes': ('network_out_mbps', 8 / max(1, raw.get('period_seconds', 60)) / 1e6),
                           'network_receive_bytes_s': ('network_in_mbps', 8 / 1e6),
                           'network_transmit_bytes_s': ('network_out_mbps', 8 / 1e6)}
            for source, (target, factor) in conversions.items():
                if source in metrics:
                    measured[target] = metrics[source] * factor
            for s in obs.get('series', []):
                target, factor = conversions.get(s['target'], (s['target'], 1))
                if s['target'] == 'write_latency_s':
                    target, factor = 'write_latency_ms', 1000
                normalized_series[target] = [{'timestamp_ms': int(datetime.fromisoformat(p['timestamp']).timestamp()*1000), 'value': p['value']*factor} for p in s.get('points', [])]
            stamps = [s['timestamp'] for s in obs.get('series', []) if s.get('timestamp')]
            ts = datetime.fromisoformat(max(stamps)) if stamps else datetime.fromisoformat(raw['timestamp']) if raw.get('timestamp') else datetime.now(timezone.utc)
            nodes.append(GraphNode(id=rid, type=kind, label=resource.get('name') or rid, layer=layer))
            telemetry.append(TelemetryPoint(node_id=rid, timestamp=ts, source='aws_cloudwatch', observed_metrics=sorted(measured), **measured))
            series[rid] = normalized_series
    if not nodes:
        raise ValueError('No discovered AWS resources.')
    ids = {n.id for n in nodes}
    edges = []
    for e in mapping.get('dependencies', []):
        if e.get('source') in ids and e.get('target') in ids:
            edges.append(GraphEdge(source=e['source'], target=e['target'], relationship=e.get('relationship', 'configured_dependency')))
    probe_path=[]
    for obs in raw.get('application', []):
        rid=obs['node_id']
        if rid not in ids or not obs.get('observed_metrics'):
            continue
        metrics=obs['metrics']
        app_id,db_id=f'observed-probe@{rid}',f'postgres@{rid}'
        ts=datetime.fromisoformat(max((s['timestamp'] for s in obs['series']),default=raw['timestamp']))
        per_metric={s['target']:[{'timestamp_ms':int(datetime.fromisoformat(p['timestamp']).timestamp()*1000),'value':p['value']} for p in s.get('points',[])] for s in obs['series']}
        if 'latency_ms' in metrics:
            nodes.append(GraphNode(id=app_id,type='microservice',label='Measured lab probe',layer='application'))
            telemetry.append(TelemetryPoint(node_id=app_id,timestamp=ts,latency_ms=metrics['latency_ms'],source='aws_cloudwatch',observed_metrics=['latency_ms']))
            series[app_id]={'latency_ms':per_metric.get('latency_ms',[])}
            edges.append(GraphEdge(source=app_id,target=rid,relationship='HOSTED_ON'))
        if 'db_query_ms' in metrics:
            nodes.append(GraphNode(id=db_id,type='database',label='EC2 PostgreSQL probe',layer='data'))
            telemetry.append(TelemetryPoint(node_id=db_id,timestamp=ts,db_latency_ms=metrics['db_query_ms'],source='aws_cloudwatch',observed_metrics=['db_latency_ms']))
            series[db_id]={'db_latency_ms':per_metric.get('db_query_ms',[]),'db_connection_ms':per_metric.get('db_connection_ms',[]),'db_roundtrip_ms':per_metric.get('db_roundtrip_ms',[])}
            edges.append(GraphEdge(source=db_id,target=rid,relationship='HOSTED_ON'))
            if 'latency_ms' in metrics:
                edges.append(GraphEdge(source=app_id,target=db_id,relationship='MEASURED_DB_CALL'))
                probe_path=[app_id,db_id]
    configured_path = mapping.get('transaction_paths', {}).get(transaction_type, [])
    path = [rid for rid in configured_path if rid in ids]
    if probe_path:
        path=probe_path
        transaction_type='OBSERVABILITY_PROBE'
    return AnalysisSample(transaction=TransactionContext(id=f"AWS-{raw.get('timestamp', datetime.now(timezone.utc).isoformat())}", type=transaction_type, path=path),
                          nodes=nodes, edges=edges, telemetry=telemetry, scenario='UNLABELED', source='aws_cloudwatch', node_labels={},
                          metadata={'series': series, 'collection': raw, 'ground_truth_available': False, 'topology_source': 'explicit_configuration',
                                    'transaction_context': 'measured_lab_probe' if probe_path else 'configured' if path else 'unavailable', 'banking_data': False,
                                    'application_timing_scope':'Measured SELECT 1 lab probe execution; excludes CloudWatch publishing and audit logging. Not production banking traffic.' if probe_path else None})


def normalize_aws_observations(raw):
    return build_aws_sample({group: [{'id': x['node_id']} for x in raw.get(group, [])] for group in ('ec2', 'rds')}, raw)
