"""Label-blind adapter: actual transaction traces -> existing evidence engine."""
import json,math,hashlib,time
from collections import defaultdict
from statistics import median
import numpy as np
from banking import store
from common.research import DataSource,TelemetryCase,TelemetrySeries,TelemetryObservation,DependencyEdge
from analysis.incident_engine import analyze_case,evidence_for
from analysis.mechanisms import diagnose,mechanism_actions

LABELS={'banking-api':'Banking API','account-service':'Account Service','ledger-service':'Ledger Service','banking-db':'SQLite Test Database'}

def case_for(operation,as_of=None,calibration=None):
    cal=calibration or store.calibration();requests=store.request_rows(operation,as_of)
    if cal:requests=[r for r in requests if r['ts']>=cal['recording_start']]
    points=defaultdict(list);edges={};trace_ids=[]
    for row in requests:
        spans=[json.loads(r['payload']) for r in store.rows('SELECT payload FROM spans WHERE trace_id=? AND end<=? ORDER BY start',(row['trace_id'],row['ts']))]
        if not spans:continue
        trace_ids.append(row['trace_id']);db_queries=[];connections=[]
        for span in spans:
            if span['kind']=='server':
                for metric,value in [('latency_ms',span['duration_ms']),('processing_ms',span['exclusive_ms']),('errors',int(span['status']>=400))]:points[(span['service'],metric)].append(TelemetryObservation(timestamp=row['ts'],value=value))
            if span['kind']=='database':db_queries.append(span['duration_ms'])
            if span['kind']=='connection':connections.append(span['duration_ms'])
            if span['caller'] and span['caller']!=span['service']:
                key=(span['caller'],span['service']);edges[key]=min(span['end'],edges.get(key,float('inf')))
        if db_queries:points[('banking-db','db_latency_ms')].append(TelemetryObservation(timestamp=row['ts'],value=sum(db_queries)))
        if connections:points[('banking-db','db_connection_ms')].append(TelemetryObservation(timestamp=row['ts'],value=sum(connections)))
    series=[TelemetrySeries(id=f'{node}:{metric}',resource=node,metric=metric,original_metric=metric,unit='count per request' if metric=='errors' else 'milliseconds',observations=obs) for (node,metric),obs in sorted(points.items())]
    digest=hashlib.sha256(json.dumps([(s.id,[(p.timestamp,p.value) for p in s.observations]) for s in series]).encode()).hexdigest()
    provenance={'topology':'Actual loopback HTTP calls and database child spans','transaction_path':['banking-api','ledger-service' if operation=='transfer' else 'account-service','banking-db'],'operation':operation,'environment':'Local academic banking application; dedicated SQLite fallback; no real money','measurement_scope':'Request handler duration includes downstream calls; excludes response serialization. Exclusive processing subtracts the union of local child intervals. Database duration is the sum of measured SQL spans, not complete transfer latency.','telemetry_sha256':digest,'calibration_id':cal['id'] if cal else None,'baseline_end':cal['reference_end'] if cal else None,'detector_threshold':cal['threshold'] if cal else 3.5,'future_points_used':False}
    return TelemetryCase(id=f"banking:{operation}:{cal['id'] if cal else 'uncalibrated'}",source=DataSource(id='banking-local',kind='academic_test_application',reference='Dedicated local FastAPI banking services; measured spans',topology_status='observed local HTTP/SQL calls'),collection=digest,series=series,edges=[DependencyEdge(source=a,target=b,provenance='Observed parent/child HTTP or SQL span',relationship='measured_call',observed_at=t) for (a,b),t in sorted(edges.items())],provenance=provenance),requests

def investigate(operation,as_of=None,persist=True):
    case,requests=case_for(operation,as_of)
    incident=analyze_case(case,as_of,forecast_enabled=False)
    calibrated=case.provenance['calibration_id'] is not None
    if not calibrated:
        incident.status='insufficient_evidence';incident.candidates=[];incident.recommendations=[]
        incident.explanation['diagnosis']={'resource':None,'mechanism':'unknown','status':'baseline_required','hypotheses':[],'verified':False,'next_check':'Collect and freeze the normal banking baseline.'}
    else:
        # Attribute excess to measured self-time or actual DB work, not inclusive caller latency.
        threshold=case.provenance['detector_threshold'];reference_end=case.provenance['baseline_end']
        evidence=[e for s in case.series if (e:=evidence_for(s,threshold=threshold,reference_end=reference_end)) is not None]
        incident.evidence=evidence
        for candidate in incident.candidates:
            own=[e for e in candidate.supporting_evidence if e.metric in ('processing_ms','db_latency_ms','db_connection_ms','errors') and e.score>=threshold and e.persistence>=2]
            excess=max((max(0,e.value-e.reference) for e in own),default=0)
            severity=max((e.score for e in own),default=0)
            candidate.score=math.log1p(severity)+math.log1p(excess) if own else .05*math.log1p(candidate.temporal_score)
            candidate.score_definition='log(1+own-time deviation) + log(1+measured own-metric excess (milliseconds for timing, counts for errors)); inclusive-only symptoms receive a low fallback score. Not a failure probability.'
        incident.candidates.sort(key=lambda c:(-c.score,c.resource))
        incident.explanation['diagnosis']=diagnose(incident)
        d=incident.explanation['diagnosis'];database=[e.model_dump() for e in evidence if e.resource=='banking-db']
        d['database_comparison']=database
        incident.recommendations=mechanism_actions(d)
        from cfao.policy import CFAOEngine
        policy=CFAOEngine().evidence_frontier(incident.candidates,maximum=2,transaction_path=case.provenance['transaction_path'])
        incident.investigation.update(policy)
        fields={'application_processing_delay':['processing_ms','latency_ms'],'lock_contention':['db_latency_ms','blocked_sessions','lock_waits','db_connection_ms']}.get(d['mechanism'],['latency_ms','processing_ms','db_latency_ms'])
        selected=[e for e in evidence if (e.resource in policy['resources'] and e.metric in fields) or (d['mechanism']=='application_processing_delay' and e.resource=='banking-db' and e.metric=='db_latency_ms')]
        for request in incident.investigation.get('requests',[]):
            request['purpose']=d['next_check']
        incident.investigation['stop_reason']='Inspect the selected measured banking trace fields; no additional external calls, sampling changes or AWS cost savings are claimed.'
        incident.investigation.update(examined_resources=sorted({e.resource for e in selected}),examined_metric_fields=[e.resource+':'+e.metric for e in selected],broad_metric_fields=len(evidence),focused_metric_fields=len(selected),actual_external_calls=0,accounting='Measured evidence fields examined after broad detection; no AWS billing or sampling claim.')
    incident.explanation['resource_labels']=LABELS
    incident.explanation['reference_protocol']='Frozen first 60% of the explicitly collected normal workload; threshold selected on the next 20%; final 20% held out.'
    incident.explanation['gnn_used']=False;incident.explanation['gnn_reason']='Banking models require matching local calibration; Alibaba weights are never used.'
    if calibrated and case.series:
        from banking.graph_model import infer
        gnn=infer(case);incident.explanation['banking_gnn']=gnn;incident.explanation['gnn_used']=gnn.get('status')=='evaluated'
        incident.explanation['gnn_role']='Separate compatible next-request graph prediction evidence; not used in resource ranking without independently validated localization contribution.'
    incident.provenance['baseline_calibrated']=calibrated
    output=incident.model_dump(mode='json')
    if persist and calibrated:store.save_snapshot(output,operation)
    return output,requests

def freeze_baseline(trace_ids,seed=42):
    all_requests=[r for r in store.request_rows() if r['trace_id'] in set(trace_ids)]
    if len(all_requests)<120 or any(not r['success'] for r in all_requests):raise ValueError('At least 120 successful measured normal requests are required.')
    all_requests.sort(key=lambda r:r['seq']);a=int(.6*len(all_requests));b=int(.8*len(all_requests))
    cal={'id':hashlib.sha256(''.join(trace_ids).encode()).hexdigest()[:24],'recording_start':all_requests[0]['ts'],'reference_end':all_requests[a-1]['ts'],'validation_end':all_requests[b-1]['ts'],'recording_end':all_requests[-1]['ts'],'threshold':3.5,'required_persistence':2,'seed':seed,'trace_ids':trace_ids,'train_trace_ids':[r['trace_id'] for r in all_requests[:a]],'validation_trace_ids':[r['trace_id'] for r in all_requests[a:b]],'test_trace_ids':[r['trace_id'] for r in all_requests[b:]],'protocol':'Chronological normal-only 60/20/20; labels not used for inference.'}
    scores=[];cases={}
    for operation in ('balance','transfer','history'):
        c,_=case_for(operation,all_requests[-1]['ts'],calibration=cal);cases[operation]=c
        for row in all_requests[a:b]:
            if row['operation']!=operation:continue
            for s in c.series:
                prefix=s.model_copy(update={'observations':[p for p in s.observations if p.timestamp<=row['ts']]})
                e=evidence_for(prefix,reference_end=cal['reference_end'])
                if e:scores.append(e.score)
    cal['threshold']=max(3.5,float(np.quantile(scores,.995))*1.25) if scores else 3.5
    with store.connect() as db:db.execute('INSERT INTO calibration VALUES(?,?,?)',(cal['id'],json.dumps(cal),time.time()))
    heldout=[]
    for row in all_requests[b:]:
        incident,_=investigate(row['operation'],row['ts'],persist=False)
        heldout.append(incident['status']=='deviation_detected')
    cal['normal_heldout']={'requests':len(heldout),'false_positive_requests':sum(heldout),'false_alarm_rate':sum(heldout)/len(heldout)}
    # Immutable new calibration record keeps threshold selection and evaluation together.
    with store.connect() as db:db.execute('UPDATE calibration SET payload=? WHERE id=?',(json.dumps(cal),cal['id']))
    from banking.graph_model import train
    model=train(cases['transfer'],cal)
    return {'calibration_id':cal['id'],'threshold':cal['threshold'],'normal_heldout':cal['normal_heldout'],'requests':len(all_requests),'graph_models':model}

def recovery(incident,operation):
    current,_=case_for(operation);comparisons=[]
    for e in incident.get('evidence',[]):
        if e['score']<incident['explanation'].get('detector_threshold',3.5):continue
        s=next((s for s in current.series if s.resource==e['resource'] and s.metric==e['metric']),None)
        new=[p for p in s.observations if p.timestamp>incident['observation_time'] and p.value is not None] if s else []
        last=new[-3:];within=[abs(p.value-e['reference'])/e['scale']<incident['explanation'].get('detector_threshold',3.5) for p in last]
        comparisons.append({'resource':e['resource'],'metric':e['metric'],'new_points':len(new),'latest_values':[p.value for p in last],'reference':e['reference'],'returned':len(within)==3 and all(within)})
    return {'status':'returned_toward_frozen_reference' if comparisons and all(c['returned'] for c in comparisons) else 'persists_or_insufficient_followup','comparisons':comparisons,'causal_recovery_verified':False}
