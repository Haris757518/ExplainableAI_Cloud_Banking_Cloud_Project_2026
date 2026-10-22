import hashlib,json
from collections import defaultdict
from common.research import DataSource,TelemetryCase,TelemetrySeries,TelemetryObservation,DependencyEdge
from dataset.banking_cloud_schema import BankingCloudRecording

def normalize(recording,source_bytes):
    """Validate retained collector bytes, chronology and observed span links.

    Content hashes establish artifact identity, not independent execution proof.
    Arbitrary labels cannot enter this schema or the resulting inference case.
    """
    r=BankingCloudRecording.model_validate(recording)
    if hashlib.sha256(source_bytes).hexdigest()!=r.source_artifact_sha256:
        raise ValueError('Collector artifact checksum mismatch')
    parsed=json.loads(source_bytes)
    if parsed.get('execution_id')!=r.execution_id or parsed.get('measurements')!=[p.model_dump() for p in r.measurements] or parsed.get('spans',[])!=[s.model_dump() for s in r.spans]:
        raise ValueError('Recording differs from retained collector artifact')
    groups=defaultdict(list);seen=set()
    for p in r.measurements:
        from aws.banking_telemetry import check_metric
        check_metric(p.metric,p.unit,p.value)
        key=(p.service,p.metric,p.timestamp)
        if key in seen:raise ValueError('Duplicate service metric timestamp')
        seen.add(key);groups[p.service,p.metric,p.unit].append(p)
    if not groups:raise ValueError('No measured workload observations')
    units=defaultdict(set)
    for service,metric,unit in groups:units[service,metric].add(unit)
    if any(len(u)>1 for u in units.values()):raise ValueError('Metric unit changes within a recording')
    series=[]
    for (service,metric,unit),points in sorted(groups.items()):
        if any(a.timestamp>=b.timestamp for a,b in zip(points,points[1:])):raise ValueError('Nonchronological input')
        series.append(TelemetrySeries(id=service+':'+metric,resource=service,metric=metric,original_metric=metric,unit=unit,
            observations=[TelemetryObservation(timestamp=p.timestamp,value=p.value,quality='observed' if p.value is not None else 'missing') for p in points]))
    spans={(s.trace_id,s.span_id):s for s in r.spans}
    if len(spans)!=len(r.spans):raise ValueError('Duplicate trace/span identity')
    edges={}
    for span in r.spans:
        parent=spans.get((span.trace_id,span.parent_span_id))
        if parent and parent.service!=span.service:
            if span.start<parent.start or span.end>parent.end:raise ValueError('Child span outside parent interval')
            key=(parent.service,span.service);edges[key]=min(edges.get(key,float('inf')),max(parent.end,span.end))
    latest=max(p.timestamp for p in r.measurements)
    if not min(p.timestamp for p in r.measurements)<r.baseline_end<latest:raise ValueError('Invalid baseline boundary')
    return TelemetryCase(id=r.recording_id,source=DataSource(id='banking-cloud' if r.environment=='aws' else 'banking-local-recording',
        kind='academic_test_application',reference=r.application,topology_status='recorded parent-child spans' if edges else 'unavailable'),
        collection=r.source_artifact_sha256,series=series,edges=[DependencyEdge(source=a,target=b,observed_at=t,
            relationship='recorded_parent_child_span',provenance='Retained workload collector spans') for (a,b),t in sorted(edges.items())],
        provenance={'environment':r.environment,'application':r.application,'infrastructure_id':r.infrastructure_id,'execution_id':r.execution_id,
            'baseline_end':r.baseline_end,'recording_end':latest,'collector_version':r.collector_version,
            'execution_evidence_status':'collector artifact retained; execution attestation requires independent deployment records'})
