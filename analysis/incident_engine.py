"""Shared label-blind detection, retrieval, reranking and investigation service."""
import math,hashlib
from statistics import median
from common.research import Incident,EvidenceRecord,RootCauseCandidate,RecommendedAction
from analysis.forecasting import forecast_next

VERSION='evidence-gated-mechanisms-v4'
FAMILIES={
 'application_latency':(['latency'],['cpu','mem','errors'],'positive robust deviation'),
 'database_query_latency':(['db_latency_ms'],['blocked_sessions','wait_events','db_connection_ms'],'positive robust deviation'),
 'database_connection_delay':(['db_connection_ms'],['db_latency_ms','pool_utilization'],'positive robust deviation'),
 'lock_contention':(['blocked_sessions','lock_waits'],['db_latency_ms'],'direct blocking/wait evidence'),
 'connection_saturation':(['pool_utilization','connection_limit'],['pool_waiters'],'measured utilization versus measured limit'),
 'cpu_pressure':(['cpu'],['request_rate','throttling'],'positive robust deviation; saturation requires unit/limit evidence'),
 'memory_pressure':(['mem'],['available_memory','memory_limit'],'growth/deviation; exhaustion requires limit evidence'),
 'memory_growth':(['mem'],['memory_limit'],'sustained growth; a leak is not inferred'),
 'disk_degradation':(['disk_latency'],['disk_queue'],'positive deviation'),
 'network_delay':(['network_latency'],['retransmissions'],'positive deviation'),
 'packet_loss':(['packet_loss'],['network_latency'],'direct loss measurement'),
 'timeouts':(['timeouts'],['latency'],'count/rate rise'),
 'error_rate':(['errors'],['request_rate'],'rate rise'),
 'request_overload':(['request_rate','cpu'],['queue_depth'],'joint demand/resource evidence'),
 'throughput_reduction':(['throughput'],['request_rate'],'negative deviation'),
 'queue_buildup':(['queue_depth'],['consumer_rate'],'positive deviation'),
 'resource_exhaustion':(['resource_used','resource_limit'],[],'measured usage and limit'),
 'dependency_failure':(['errors'],['dependency_errors'],'requires documented/recorded dependency'),
 'cascading_degradation':(['latency'],['errors'],'requires graph plus observed ordering; correlation is not causation'),
 'change_point':([],[],'relative shift against preceding median'),
 'sustained_degradation':([],[],'two consecutive above-threshold points'),
 'telemetry_quality':([],[],'missing, nonfinite, chronology, spacing and freshness checks'),
 'recovery_abnormality':([],[],'three subsequent values against a frozen incident reference'),
}

def capabilities(metrics=(),has_graph=False):
    metrics=set(metrics)
    out=[]
    for name,(required,optional,method) in FAMILIES.items():
        available=all(any(r==m or r in m for m in metrics) for r in required)
        if name in ('dependency_failure','cascading_degradation'):available &= has_graph
        implemented=name in ('application_latency','database_query_latency','database_connection_delay','cpu_pressure','memory_pressure','throughput_reduction','change_point','sustained_degradation','telemetry_quality','recovery_abnormality')
        supported=available and implemented
        out.append({'family':name,'required':required,'optional':optional,'method':method,'supported':supported,'status':'available evidence mechanics; not verified fault classification' if supported else 'missing required measurements/topology','compatible_sources':['Alibaba','Microsoft','RCAEval','AWS'],'ground_truth':'source-specific; labels never enter inference'})
    return out

def evidence_for(series,threshold=3.5,history_limit=48,reference_end=None):
    original=series.observations
    points=[p for p in original if p.value is not None]
    if len(points)<14:return None
    if series.period_seconds and original[-1].timestamp-points[-1].timestamp>3*series.period_seconds:return None
    valid=points[:-1][-history_limit:] if reference_end is None else [p for p in points if p.timestamp<=reference_end and p.timestamp<points[-1].timestamp][-256:]
    if len(valid)<12 or points[-1].value is None:return None
    center=median(p.value for p in valid);mad=median(abs(p.value-center) for p in valid)
    scale=max(1.4826*mad,abs(center)*.05,1e-8)
    last=points[-1];delta=last.value-center
    # Generic expert-labelled benchmarks can contain both rises and drops.
    # Semantically directional live metrics remain positive except free capacity/throughput.
    two_sided=series.metric.startswith('application-') or series.resource=='recorded-series'
    downward=any(m in series.metric for m in ('free','available','throughput'))
    score=abs(delta)/scale if two_sided else max(0,-delta if downward else delta)/scale
    consecutive=0;onset=None
    for p in reversed(points[-6:]):
        if p.value is None:break
        z=abs(p.value-center)/scale if two_sided else max(0,-(p.value-center) if downward else p.value-center)/scale
        if z<threshold:break
        consecutive+=1;onset=p.timestamp
    return EvidenceRecord(resource=series.resource,metric=series.metric,timestamp=last.timestamp,value=last.value,reference=center,scale=scale,score=score,direction='two-sided' if two_sided else 'decrease' if downward else 'increase',persistence=consecutive,onset=onset)

def recommend(evidence):
    actions=[]
    for e in evidence:
        metric=e.metric.lower()
        if 'cpu' in metric:category='cpu_pressure';diagnostic='Compare workload rate, process CPU and measured throttling.';mitigation='Consider capacity or workload changes only after confirming saturation.';missing='CPU units, limits and workload demand'
        elif any(k in metric for k in ('connection','pool')):category='connection_delay';diagnostic='Compare connection timing with query timing, pool occupancy and server admission.';mitigation='Review connection leaks and long transactions before changing pool limits.';missing='Pool occupancy, limits, authentication and network timing'
        elif any(k in metric for k in ('latency','query')):category='latency_deviation';diagnostic='Compare query, connection and application timing; inspect blocking and wait events.';mitigation='Review the measured bottleneck before changing query, capacity or timeout settings.';missing='Waits, spans, pool admission and network evidence'
        elif 'mem' in metric:category='memory_growth';diagnostic='Compare memory trend with workload, garbage collection and actual limits.';mitigation='Review allocation and retention only after confirming sustained pressure.';missing='Memory units, limits, allocations and workload trend'
        else:category='metric_deviation';diagnostic='Verify source metric definition and collect discriminating resource/error evidence.';mitigation='Defer operational changes until a mechanism is supported.';missing='Mechanism-specific corroboration'
        actions.append(RecommendedAction(category=category,evidence=[f'{e.resource}:{e.metric}={e.value:g}, preceding reference={e.reference:g}, score={e.score:.3g}'],mechanism_status='suspected; relative deviation only',diagnostic_action=diagnostic,proposed_mitigation=mitigation,purpose='Distinguish competing explanations without assuming causality.',verification_metric=e.metric,prerequisites=missing+'; separate operator authorization before changes.'))
    return actions[:6]

def analyze_case(case,as_of=None,*,graph_enabled=True,evidence_gate=True,forecast_enabled=True):
    # Prefix filtering happens before all calculations, including forecasting.
    prefix=case.model_copy(update={'series':[s.model_copy(update={'observations':[p for p in s.observations if as_of is None or p.timestamp<=as_of]}) for s in case.series]})
    first=min((p.timestamp for s in prefix.series for p in s.observations),default=0)
    # A fixed recording-relative warm-up is a declared benchmark protocol, not a fault
    # label. It stays fixed as replay advances and cannot adapt away an incident.
    recorded_end=case.provenance.get('recording_end',first+3000)
    reference_end=first+min(600,.2*(recorded_end-first)) if case.source.id=='rcaeval' else None
    if case.source.id in {'banking-local','banking-cloud','banking-local-recording'}:reference_end=case.provenance.get('baseline_end')
    threshold,persistence=3.5,2
    if case.source.id in {'banking-local','banking-cloud','banking-local-recording'}:threshold=float(case.provenance.get('detector_threshold',3.5))
    calibration='predeclared heuristic, not validated fault confidence'
    if case.source.id=='microsoft':
        from pathlib import Path
        import json
        reports=sorted((Path(__file__).resolve().parents[1]/'results/research_v3').glob('*/run.json'),key=lambda p:p.stat().st_mtime)
        reports=[p for p in reports if (p.parent/'microsoft.json').exists()]
        if reports and (reports[-1].parent/'microsoft.json').exists():
            rule=json.loads((reports[-1].parent/'microsoft.json').read_text(encoding='utf-8'))['methods']['median_mad']
            threshold,persistence=rule['threshold'],rule['persistence']
            calibration='Microsoft median/MAD threshold and persistence selected on chronological validation only'
    evidence=[];missing=[]
    for series in prefix.series:
        if case.source.kind=='live_cloud':
            from datetime import datetime,timezone
            valid=[p for p in series.observations if p.value is not None]
            age=datetime.now(timezone.utc).timestamp()-valid[-1].timestamp if valid else float('inf')
            if age>max(300,3*(series.period_seconds or 60)) or age<-(series.period_seconds or 60):
                missing.append(series.id+': stale/future live observation');continue
        e=evidence_for(series,threshold=threshold,reference_end=reference_end)
        if e:evidence.append(e)
        else:missing.append(series.id+': insufficient or missing history')
    evidence.sort(key=lambda e:e.score,reverse=True)
    abnormal=[e for e in evidence if e.score>=threshold and (e.persistence>=persistence or not evidence_gate)]
    by_resource={}
    for e in abnormal:by_resource.setdefault(e.resource,[]).append(e)
    retrieval=sorted(by_resource,key=lambda n:max(e.score for e in by_resource[n]),reverse=True)
    edges=[e for e in prefix.edges if as_of is None or e.observed_at is None or e.observed_at<=as_of] if graph_enabled else []
    candidates=[]
    for node in retrieval[:20]:
        support=by_resource[node];temporal=max(e.score for e in support)
        onset=min((e.onset for e in support if e.onset is not None),default=float('inf'))
        propagation=[]
        for edge in edges:
            if edge.target==node and edge.source in by_resource:
                upstream=min((e.onset for e in by_resource[edge.source] if e.onset is not None),default=float('-inf'))
                if onset<=upstream:propagation.append(edge)
        graph_support=len(propagation)
        score=math.log1p(temporal)+.15*len(support)+.2*graph_support
        candidates.append(RootCauseCandidate(resource=node,score=score,temporal_score=temporal,graph_support=graph_support,score_definition='log(1+maximum positive deviation) + 0.15*supporting metrics + 0.2*recorded upstream relationships with compatible onset; heuristic, not calibrated confidence',supporting_evidence=support,competing_hypotheses=['resource/workload pressure','downstream delay','application overhead','unknown mechanism'],missing_evidence=['independent mechanism-specific corroboration']+([] if edges else ['dependency topology unavailable'])))
    candidates.sort(key=lambda c:(-c.score,c.resource))
    from cfao.policy import CFAOEngine
    policy=CFAOEngine().evidence_frontier(candidates,maximum=3,transaction_path=case.provenance.get('transaction_path',[]))
    frontier=policy['resources']
    broad=sorted({s.resource for s in prefix.series})
    static=set(frontier)
    for edge in edges:
        if edge.source in frontier or edge.target in frontier:static.update((edge.source,edge.target))
    latest=max((p.timestamp for s in prefix.series for p in s.observations),default=None)
    forecasts=[]
    if forecast_enabled:
        selected=sorted(prefix.series,key=lambda s:next((e.score for e in evidence if e.resource==s.resource and e.metric==s.metric),0),reverse=True)[:4]
        forecasts=[forecast_next(s) for s in selected if not any(m.startswith(s.id+': stale/future') for m in missing)]
    status='insufficient_evidence' if not evidence else 'deviation_detected' if abnormal else 'no_deviation_in_observed_metrics'
    incident = Incident(id=hashlib.sha256(f'{case.id}:{latest}:{VERSION}'.encode()).hexdigest()[:24],source=case.source,observation_time=latest,status=status,score_interpretation='Relative chronological deviation; no operational-failure probability.',model_version=VERSION,affected_services=sorted(by_resource),candidates=candidates[:10],evidence=evidence[:100],missing_evidence=missing[:20],recommendations=recommend(abnormal),forecasts=forecasts,investigation={'strategy':'evidence-gated bounded candidate frontier','resources':frontier,'requests':[{'resource':c.resource,'purpose':'distinguish competing mechanisms','missing':c.missing_evidence} for c in candidates[:3]],'broad_resource_count':len(broad),'selected_resource_count':len(frontier),'static_one_hop_count':len(static),'actual_external_calls':0,'sampling_changed':False,'cost_savings':None,'stop_reason':'No current candidate' if not frontier else 'Recorded dataset: inspect available measured columns; no external telemetry is fabricated.'},explanation={'method':'exact median/MAD evidence, onset ordering and explicit graph-support terms','reference_protocol':'first min(600 seconds, 20% recording duration) frozen (RCAEval); preceding 48 valid points (other sources)','retrieval_order':retrieval,'gnn_used':False,'gnn_reason':'Alibaba checkpoint domain restriction preserved; this benchmark has no validated GNN weights.','causal_confirmation':False,'important_edges':[e.model_dump() for e in edges if e.source in by_resource or e.target in by_resource],'affected_dependents':sorted({e.source for e in edges if e.target in by_resource})},recovery={'status':'not_established','reason':'Requires a persisted prior deviation reference and subsequent observations; no recovery event is invented.'},graph={'nodes':broad,'edges':[e.model_dump() for e in edges],'provenance':prefix.provenance.get('topology','unavailable')},ground_truth_available=case.source.kind in ('expert_labelled_series','recorded_controlled_benchmark'),provenance={**case.provenance,'collection':case.collection,'as_of':as_of,'future_points_used':False})

    incident.investigation.update(policy)
    incident.explanation.update(detector_threshold=threshold,required_persistence=persistence,calibration=calibration)
    incident.provenance["data_quality"]={"missing_points":sum(p.value is None for s in prefix.series for p in s.observations),"observed_points":sum(p.value is not None for s in prefix.series for p in s.observations),"insufficient_or_stale_series":len(missing)}
    from analysis.mechanisms import diagnose, mechanism_actions, resource_labels
    incident.explanation['diagnosis'] = diagnose(incident)
    incident.explanation['resource_labels'] = resource_labels(incident.graph['nodes'])
    incident.recommendations = mechanism_actions(incident.explanation['diagnosis'])
    for request in incident.investigation.get('requests',[]):
        candidate=next((c for c in incident.candidates if c.resource==request['resource']),None)
        if candidate:
            local=diagnose(incident.model_copy(update={'candidates':[candidate]}))
            request['purpose']=local['next_check']
            request['mechanism_status']=local['status']
    leading=incident.candidates[0] if incident.candidates else None
    propagation=[]
    if leading:
        origin_onset=min((e.onset for e in leading.supporting_evidence if e.onset is not None),default=None)
        for edge in edges:
            if edge.target!=leading.resource or edge.source not in by_resource:continue
            caller_onset=min((e.onset for e in by_resource[edge.source] if e.onset is not None),default=None)
            propagation.append({'caller':edge.source,'dependency':edge.target,'origin_onset':origin_onset,'caller_onset':caller_onset,'ordering':'compatible_later_or_simultaneous' if origin_onset is not None and caller_onset is not None and origin_onset<=caller_onset else 'contradictory_or_unknown','causal_confirmation':False})
    incident.explanation['observed_propagation']=propagation
    incident.explanation['onset_interpretation']='Start of a qualifying run within the last six valid observations, not independently annotated fault onset.'
    incident.explanation['localization_scope']='metric_series_only' if case.source.id=='microsoft' else 'suspected_resource'
    if case.source.id in {'banking-cloud','banking-local-recording'}:
        from analysis.probe_xai import investigate
        incident.explanation['probe_xai']=investigate(case,incident,as_of=latest,budget=12)
    return incident
