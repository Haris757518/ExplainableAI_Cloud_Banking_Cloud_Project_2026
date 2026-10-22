"""PROBE-XAI research prototype: progressively inspect competing explanations.

No benchmark case names, root labels or injection annotations enter decisions.
Supported drivers remain hypotheses, not confirmed physical causality.
"""
from statistics import median
from analysis.diagnostic_queries import FAMILIES,choose_next
from analysis.recommendations import recommend
from analysis.recovery_verification import verify_recovery

VERSION='probe-xai-v1'
ALIASES={
 'cpu':'cpu_percent','cpuutilization':'cpu_percent','cpu_percent':'cpu_percent',
 'latency-90':'latency_ms','latency':'latency_ms','latency_ms':'latency_ms','processing_ms':'processing_ms',
 'workload':'request_rate','requests_per_second':'request_rate','request_rate':'request_rate',
 'mem':'memory_percent','memory_percent':'memory_percent','queue_length':'queue_depth',
 'concurrency':'active_requests','active_workers':'worker_count',
 'query_duration':'db_latency_ms','lock_waits':'lock_wait_ms',
}

def summarize(series,as_of,baseline_end):
    points=[p for p in series.observations if p.timestamp<=as_of and p.value is not None and p.quality=='observed']
    before=[p.value for p in points if p.timestamp<=baseline_end]
    after=[p for p in points if baseline_end<p.timestamp<=as_of]
    if len(before)<12 or len(after)<2:return None
    intervals=[b.timestamp-a.timestamp for a,b in zip(points,points[1:]) if b.timestamp>a.timestamp]
    spacing=series.period_seconds or (median(intervals) if intervals else None)
    if spacing and as_of-after[-1].timestamp>3*spacing:return None
    center=median(before);scale=max(1.4826*median(abs(v-center) for v in before),abs(center)*.05,1e-8)
    latest=after[-2:];value=latest[-1].value
    onset=None
    for p in reversed(after):
        if (p.value-center)/scale<3.5:break
        onset=p.timestamp
    return {'series_id':series.id,'metric':ALIASES.get(series.metric.lower(),series.metric.lower()),
        'original_metric':series.original_metric,'resource':series.resource,'unit':series.unit,
        'timestamp':latest[-1].timestamp,'baseline':center,'value':value,'delta':value-center,
        'ratio':value/center if center else None,'score':(value-center)/scale,
        'rising':all((p.value-center)/scale>=3.5 for p in latest),
        'falling':all((center-p.value)/scale>=3.5 for p in latest),
        'stable':all(abs(p.value-center)<=max(abs(center)*.2,1e-8) for p in latest),
        'onset':onset,'baseline_observations':len(before),'observations_used':len(points)}

def classify(evidence):
    def e(m):return evidence.get(m,{})
    def up(m):return e(m).get('rising',False)
    def stable(m):return e(m).get('stable',False)
    def down(m):return e(m).get('falling',False)
    outcomes={}
    checks={
      'demand_exceeds_capacity':lambda:up('request_rate') and up('queue_depth') and stable('worker_count') and stable('cpu_per_request') and stable('retry_rate') and up('cpu_percent') and e('request_rate')['value']>e('capacity_rps')['value']>0 and e('request_rate')['onset']<=e('cpu_percent')['onset'] and e('request_rate')['onset']<=e('queue_depth')['onset'],
      'expensive_execution':lambda:up('cpu_per_request') and stable('request_rate') and stable('worker_count') and stable('retry_rate') and up('cpu_percent'),
      'reduced_capacity':lambda:(down('worker_count') or down('cpu_limit')) and up('throttling') and stable('request_rate') and up('queue_depth'),
      'retry_storm':lambda:up('retry_rate') and up('timeouts') and stable('external_request_rate') and up('request_rate') and up('queue_depth'),
      'garbage_collection':lambda:up('memory_percent') and up('gc_pause_ms') and up('latency_ms') and stable('request_rate'),
      'blocking_transaction':lambda:up('db_latency_ms') and up('lock_wait_ms') and up('blocked_sessions') and up('transaction_age_seconds'),
    }
    for name,required in FAMILIES.items():
        missing=[m for m in required if m not in evidence]
        supported=False if missing else bool(checks[name]())
        outcomes[name]={'name':name,'status':'insufficient_evidence' if missing else 'supported_hypothesis' if supported else 'not_supported_by_current_measurements',
            'missing':missing,'supporting_series':[e(m)['series_id'] for m in required if e(m)],
            'causal_confirmation':False}
    return outcomes

def investigate(case,incident,*,as_of=None,budget=12,policy='progressive',gnn=None):
    if policy not in {'progressive','conventional','none'}:raise ValueError('Unknown investigation policy')
    times=[p.timestamp for s in case.series for p in s.observations]
    if not times:return {'status':'insufficient_evidence','chain':[],'queries':[],'reason':'No measured observations.'}
    as_of=max(times) if as_of is None else as_of
    baseline_end=case.provenance.get('baseline_end',min(times)+min(600,.2*(case.provenance.get('recording_end',max(times))-min(times))))
    candidates=incident.candidates
    resource=candidates[0].resource if candidates else None
    if gnn and gnn.get('status')=='evaluated':
        if gnn.get('source_checksum')!=case.collection or gnn.get('as_of')!=as_of:
            gnn={'status':'not_applied','reason':'Model evidence does not match this recording and observation time.'}
        else:
            resource=next((r for r in gnn.get('ranking',[]) if any(s.resource==r for s in case.series)),resource)
    local=[s for s in case.series if s.resource==resource]
    index={}
    for s in sorted(local,key=lambda s:s.id):
        metric=ALIASES.get(s.metric.lower(),s.metric.lower())
        # Ambiguous duplicate metric aliases are excluded rather than arbitrarily chosen.
        index[metric]=None if metric in index else s
    index={m:s for m,s in index.items() if s is not None}
    examined={};queries=[];cost=0
    # Detection screens latency and resource pressure. Follow-up cost excludes this common screen.
    for metric in ['latency_ms','processing_ms','cpu_percent','db_latency_ms']:
        if metric in index:
            evidence=summarize(index[metric],as_of,baseline_end)
            if evidence:examined[metric]=evidence
    if policy!='none' and resource:
        while True:
            hypotheses=classify(examined)
            unresolved=[name for name,h in hypotheses.items() if h['status']=='insufficient_evidence']
            if policy=='conventional':
                unseen=sorted(set(index)-set(examined)-{q['metric'] for q in queries})
                next_query=[{'metric':unseen[0],'cost':1,'utility':None,'distinguishes':[], 'reason':'Conventional inspect-all measured-column order'}] if unseen else []
            else:
                next_query=choose_next(index,set(examined)|{q['metric'] for q in queries},unresolved,budget-cost)
            if not next_query or cost+next_query[0]['cost']>budget:break
            query=next_query[0];cost+=query['cost'];evidence=summarize(index[query['metric']],as_of,baseline_end)
            queries.append({**query,'outcome':'measured' if evidence else 'insufficient_history','evidence':evidence})
            if evidence:examined[query['metric']]=evidence
    hypotheses=classify(examined)
    supported=[name for name,h in hypotheses.items() if h['status']=='supported_hypothesis']
    cpu=examined.get('cpu_percent',{});db=examined.get('db_latency_ms',{})
    immediate='cpu_pressure' if cpu.get('rising') else 'database_pressure' if db.get('rising') else 'unknown'
    driver=supported[0] if len(supported)==1 else None
    # A deep explanation needs measured alternatives excluded, not only concurrent rises.
    competing=[name for name,h in hypotheses.items() if name!=driver and h['status']!='not_supported_by_current_measurements']
    reason=driver if driver and not competing else immediate
    chain=[]
    if incident.status=='deviation_detected':
        chain.append({'level':'symptom','title':'Measured performance changed','status':'observed',
            'explanation':'The detector found a sustained departure from the earlier measured reference.','evidence':[e for e in examined.values() if e['rising']]})
        if resource:chain.append({'level':'location','title':resource,'status':'suspected',
            'explanation':'This resource leads the declared service-ranking method. A ranking is not causal confirmation.','evidence':[]})
        if immediate!='unknown':chain.append({'level':'mechanism','title':immediate.replace('_',' '),'status':'supported_hypothesis',
            'explanation':'Resource-local measurements support this immediate bottleneck hypothesis.','evidence':[cpu if immediate=='cpu_pressure' else db]})
        if driver:chain.append({'level':'driver','title':driver.replace('_',' '),
            'status':'supported_hypothesis' if not competing else 'plausible_with_unresolved_alternatives',
            'explanation':'Required measured signatures agree. '+('Competing explanations remain unresolved.' if competing else 'Tested alternatives do not match the current measurements. Physical causality remains unconfirmed.'),
            'evidence':[examined[m] for m in FAMILIES[driver]]})
    missing=sorted({m for h in hypotheses.values() for m in h['missing']})
    deepest='driver' if driver and not competing else 'mechanism' if immediate!='unknown' and chain else 'location' if resource and chain else 'symptom' if chain else 'none'
    recommendation=recommend(reason)
    status='investigated' if chain else 'no_current_deviation' if incident.status=='no_deviation_in_observed_metrics' else 'insufficient_evidence'
    result={'version':VERSION,'status':status,'resource':resource,'as_of':as_of,'baseline_end':baseline_end,
        'summary':(f"{resource}: {immediate.replace('_',' ')} is supported as a hypothesis; "+(f"{driver.replace('_',' ')} remains a candidate explanation." if driver else 'the underlying driver is not established.')) if chain and immediate!='unknown' else f'A deviation was detected near {resource}; the mechanism and underlying driver are not established.' if chain else 'No supported incident explanation is available for this measured prefix.',
        'chain':chain,'deepest_supported_level':deepest,'underlying_driver':driver if deepest=='driver' else None,
        'hypotheses':list(hypotheses.values()),'unresolved_alternatives':competing,'missing_measurements':missing,
        'queries':queries,'query_cost_units':cost,'query_budget':budget,'measured_columns_inspected':len(examined),
        'initial_screen_columns':min(len(examined),sum(m in examined for m in ['latency_ms','processing_ms','cpu_percent','db_latency_ms'])),
        'cost_definition':'Explicit measured-column inspection effort; not AWS cost or measured information gain.',
        'policy':policy,'recommendation':recommendation,'recovery':{'status':'not_verified','reason':'No approved corrective action and later correctness evidence are recorded.'},
        'stop_reason':'No remaining available discriminating measurements within the budget. Missing series are never fabricated.',
        'gnn':gnn or {'status':'not_applied','reason':'No matching domain checkpoint applied.'},
        'source':case.source.model_dump(),'source_checksum':case.collection,'future_points_used':False,
        'causal_confirmation':False,'novelty_status':'Research prototype; comparative benefit requires independent evaluation.'}
    return result
