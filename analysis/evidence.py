"""Read-only corroboration and unique-observation comparisons."""
def database_findings(observation):
    measured=observation.get('observation', {})
    blocked=measured.get('blocked_sessions')
    findings=[]
    if isinstance(blocked, (int,float)):
        findings.append({'kind':'direct_measurement','finding':f'{blocked} blocked sessions in this snapshot','supports':'current blocking' if blocked>0 else None,'contradicts':'current blocking' if blocked==0 else None})
    return {'findings':findings,'cause_status':'blocking_observed' if isinstance(blocked,(int,float)) and blocked>0 else 'cause_not_established',
            'causal_confirmation':False,'limitation':'A snapshot cannot attribute an earlier latency change or exclude intermittent blocking, slow SQL, authentication or pool pressure.'}

def compare_series(before, after):
    comparisons=[]
    for node, metrics in after.items():
        for metric, points in metrics.items():
            old=before.get(node,{}).get(metric,[])
            cutoff=max((p['timestamp_ms'] for p in old), default=float('-inf'))
            fresh=[p for p in points if p['timestamp_ms']>cutoff]
            comparisons.append({'node':node,'metric':metric,'new_point_count':len(fresh),'previous_latest':old[-1] if old else None,'new_latest':fresh[-1] if fresh else None})
    return comparisons

def assess_followup(evidence, before, after):
    assessments=[]
    for e in evidence:
        if e['robust_z']<3.5: continue
        old=before.get(e['node'],{}).get(e['metric'],[])
        cutoff=max((p['timestamp_ms'] for p in old),default=float('-inf'))
        points=sorted((p for p in after.get(e['node'],{}).get(e['metric'],[]) if p['timestamp_ms']>cutoff),key=lambda p:p['timestamp_ms'])
        scale=e.get('scale',max(1.4826*e['reference_mad'],abs(e['reference_median'])*.05,1e-6))
        last=points[-3:]
        z=[max(0,(p['value']-e['reference_median'])/scale) for p in last]
        state='no_new_observations' if not z else 'deviation_persists' if z[-1]>=3.5 else 'returned_toward_reference' if len(z)==3 and all(v<3.5 for v in z) else 'insufficient_subsequent_observations'
        assessments.append({'node':e['node'],'metric':e['metric'],'status':state,'new_points':len(points),'reference_median':e['reference_median'],'rule':'Three newer observations below the original deviation threshold; this is not proof of incident recovery.'})
    return assessments
