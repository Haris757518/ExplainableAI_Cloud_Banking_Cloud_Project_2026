"""Recorded RE2 parent/child evidence, with edge availability timestamps."""
from functools import lru_cache
import json
from dataset.benchmarks import ROOT,digest,finite,period
from common.research import DataSource,TelemetryCase,TelemetrySeries,TelemetryObservation,DependencyEdge
V4=ROOT.parent/'research_v4'
def entries():
    return json.loads((V4/'manifest.json').read_text(encoding='utf-8')) if (V4/'manifest.json').exists() else {'cases':[]}

@lru_cache(maxsize=2)
def load_re2(case_id):
    import pyarrow.parquet as pq
    info=entries();entry=next((e for e in info['cases'] if e['id']==case_id),None)
    if entry is None:raise FileNotFoundError('Benchmark case is not imported')
    folder=V4/entry['display_name']
    for filename,sha in entry['checksums'].items():
        if digest(folder/filename)!=sha:raise ValueError('RE2 source checksum mismatch')
    table=pq.read_table(folder/'metrics.parquet').to_pydict();times=table.pop('time')
    if any(b<=a for a,b in zip(times,times[1:])):raise ValueError('Nonchronological RE2 source')
    series=[]
    for name,values in table.items():
        resource,metric=name.rsplit('_',1)
        obs=[TelemetryObservation(timestamp=float(t),value=finite(v)) for t,v in zip(times,values)]
        series.append(TelemetrySeries(id=name,resource=resource,metric=metric,original_metric=name,period_seconds=period(obs),observations=obs))
    resources={s.resource for s in series}
    def resolve(name):
        if name in resources:return name
        # Explicit, inspectable alias: trace frontendservice corresponds to measured frontend.
        if name=='frontendservice' and 'frontend' in resources:return 'frontend'
        return None
    spans=pq.read_table(folder/'traces.parquet',columns=['traceID','spanID','parentSpanID','serviceName','startTime','duration']).to_pylist()
    parents={(r['traceID'],r['spanID']):r for r in spans};edges={};unmatched=set()
    for row in spans:
        parent=parents.get((row['traceID'],row['parentSpanID']))
        if not parent:continue
        source,target=resolve(parent['serviceName']),resolve(row['serviceName'])
        if not source or not target:unmatched.add(parent['serviceName'] if not source else row['serviceName']);continue
        if source==target:continue
        # Jaeger microsecond start/duration; completed spans only are available.
        available=max((row['startTime']+row['duration'])/1e6,(parent['startTime']+parent['duration'])/1e6)
        key=(source,target);edges[key]=min(available,edges.get(key,float('inf')))
    topology=[DependencyEdge(source=a,target=b,relationship='recorded_parent_child_span',provenance='Official RE2 Jaeger traceID + parentSpanID match; availability after both spans finish',observed_at=t) for (a,b),t in sorted(edges.items())]
    return TelemetryCase(id=case_id,source=DataSource(id='rcaeval',kind='recorded_controlled_benchmark',reference='https://huggingface.co/datasets/phamquiluan/RCAEval',revision=info['revision'],topology_status='recorded trace parent-child'),collection=entry['sha256'],series=series,edges=topology,provenance={'sha256':entry['sha256'],'split':'illustrative_re2_graph','recording_end':float(times[-1]),'topology':'Recorded RE2 parent-child spans, time-gated. frontendservice → frontend explicit alias.','unmatched_trace_services':sorted(unmatched),'trace_sha256':entry['checksums']['traces.parquet']})

def truth_re2(case_id):
    import pyarrow.parquet as pq
    entry=next(e for e in entries()['cases'] if e['id']==case_id)
    row=next(r for r in pq.read_table(ROOT/'rcaeval/cases.parquet').to_pylist() if r['case']==entry['display_name'])
    if row!=entry['truth']:raise ValueError('RE2 annotation differs from official index')
    if int((V4/entry['display_name']/'inject_time.txt').read_text())!=row['inject_time']:raise ValueError('Injection time mismatch')
    return {k:row[k] for k in ('root_cause_service','fault','inject_time','system')}|{'label_source':'Official RE2 case index and inject_time.txt; controlled injection'}
