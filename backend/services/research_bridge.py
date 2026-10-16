"""Adapt existing observed pipelines without changing their provenance or models."""
from common.research import DataSource,TelemetryCase,TelemetrySeries,TelemetryObservation,DependencyEdge
from analysis.incident_engine import analyze_case

def observed_incident(sample,gnn):
    live=sample.source=='aws_cloudwatch'
    series=[]
    for node,metrics in sample.metadata.get('series',{}).items():
        for metric,points in metrics.items():
            series.append(TelemetrySeries(id=f'{node}:{metric}',resource=node,metric=metric,original_metric=metric,unit='milliseconds' if metric.endswith('_ms') else 'percent' if metric.endswith('_percent') else 'source-defined',period_seconds=sample.metadata.get('collection',{}).get('period_seconds',sample.metadata.get('window_ms',5000)/1000),timestamp_kind='unix_seconds' if live else 'relative_trace_seconds',observations=[TelemetryObservation(timestamp=(p['timestamp_ms']+(0 if live else sample.metadata.get('window_ms',5000)))/1000,value=p['value'],original_timestamp=p['timestamp_ms'],timestamp_semantics='actual CloudWatch timestamp' if live else 'window-end availability; original relative window-start milliseconds retained') for p in points]))
    source=DataSource(id='aws' if live else 'alibaba',kind='live_cloud' if live else 'production_trace',reference='AWS CloudWatch and existing PostgreSQL observability probe' if live else 'https://github.com/alibaba/clusterdata/tree/master/cluster-trace-microservices-v2021',topology_status='observed/configured' if sample.edges else 'unavailable')
    case=TelemetryCase(id=sample.transaction.id,source=source,collection=sample.transaction.id,series=series,edges=[DependencyEdge(source=e.source,target=e.target,relationship=e.relationship,provenance='configured or deployed measured probe' if live else 'recorded Alibaba calls') for e in sample.edges],provenance={'topology':'recorded/configured','banking_data':False,'transaction_path':sample.transaction.path})
    result=analyze_case(case)
    result.explanation['gnn_used']=gnn['status']=='evaluated'
    result.explanation['gnn_evidence']=gnn
    result.explanation['transaction_path']=sample.transaction.path
    result.explanation['gnn_role']='Domain-checked measured reconstruction evidence; not a calibrated cause probability or cross-domain transfer.'
    return result
