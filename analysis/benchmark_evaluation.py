"""Benchmark scoring is separate from label-blind inference."""
import json,time,math
import numpy as np
from dataset.benchmarks import manifest,load_case,labels_for_evaluation
from analysis.forecasting import fit_models,predict,forecast_evaluation
from analysis.incident_engine import analyze_case

def binary(truth,prediction):
    tp=sum(y==1 and p==1 for y,p in zip(truth,prediction));fp=sum(y==0 and p==1 for y,p in zip(truth,prediction));fn=sum(y==1 and p==0 for y,p in zip(truth,prediction));tn=sum(y==0 and p==0 for y,p in zip(truth,prediction))
    precision=tp/(tp+fp) if tp+fp else None;recall=tp/(tp+fn) if tp+fn else None
    return {'tp':tp,'fp':fp,'fn':fn,'tn':tn,'precision':precision,'recall':recall,'f1':2*tp/(2*tp+fp+fn) if 2*tp+fp+fn else 0.,'false_alarm_rate':fp/(fp+tn) if fp+tn else None,'evaluated_points':len(truth)}

def scores_for_series(series):
    values=[p.value for p in series.observations];n=len(values);a=int(.6*n)
    y=np.asarray([np.nan if v is None else v for v in values])
    score=np.full(n,np.nan)
    for i in range(12,n):
        history=y[max(0,i-48):i];history=history[np.isfinite(history)]
        if len(history)<12 or not np.isfinite(y[i]):continue
        center=np.median(history);scale=max(1.4826*np.median(abs(history-center)),abs(center)*.05,1e-8)
        score[i]=abs(y[i]-center)/scale
    model=fit_models(values,a) if a>=36 else None
    residual=np.full(n,np.nan)
    raw=np.full(n,np.nan)
    for i in range(12,n):
        p=predict(values,i,model,'ridge_ar12')
        if p is not None and values[i] is not None:raw[i]=abs(values[i]-p)
    train=raw[12:a];train=train[np.isfinite(train)]
    if len(train):residual=raw/max(1.4826*float(np.median(train)),1e-8)
    return {'median_mad':score,'forecast_residual':residual}

def microsoft():
    cases=[r for r in manifest()['cases'] if r['source']=='microsoft'];data=[];forecast=[]
    for row in cases:
        case=load_case(row['id']);series=case.series[0]
        # No labels are involved in construction of detector scores or forecasts.
        scores=scores_for_series(series);f=forecast_evaluation(series)
        labels=labels_for_evaluation(row['id'])['point_labels']
        data.append((row,series,scores,labels))
        if f['status']=='evaluated':forecast.append({'case_id':row['id'],**f})
    methods={}
    for method in ('median_mad','forecast_residual'):
        choices=[]
        for threshold in (2.,3.5,5.,8.,12.):
            for persistence in (1,2):
                actual=[];predicted=[]
                for _,series,scores,labels in data:
                    n=len(labels);a,b=int(.6*n),int(.8*n);score=scores[method]
                    for i in range(a,b):
                        if all(np.isfinite(v[i]) for v in scores.values()) and labels[i] is not None:actual.append(labels[i]);predicted.append(int(all(np.isfinite(score[j]) and score[j]>=threshold for j in range(i-persistence+1,i+1))))
                choices.append((binary(actual,predicted)['f1'],threshold,persistence))
        _,threshold,persistence=max(choices,key=lambda r:(r[0],r[1],r[2]))
        actual=[];predicted=[];details=[];delays=[];unknown=0
        for row,series,scores,labels in data:
            n=len(labels);b=int(.8*n);score=scores[method];yt=[];yp=[];last_label=0;event_start=None;found=False
            for i in range(b,n):
                if labels[i] is None:unknown+=1;continue
                if labels[i] and not last_label:event_start=series.observations[i].timestamp;found=False
                last_label=labels[i]
                if not all(np.isfinite(v[i]) for v in scores.values()):unknown+=1;continue
                alert=int(all(np.isfinite(score[j]) and score[j]>=threshold for j in range(i-persistence+1,i+1)))
                yt.append(labels[i]);yp.append(alert)
                if alert and labels[i] and event_start is not None and not found:delays.append(series.observations[i].timestamp-event_start);found=True
            actual+=yt;predicted+=yp;details.append({'case_id':row['id'],**binary(yt,yp)})
        methods[method]={'threshold':threshold,'persistence':persistence,'selection':'F1 on chronological validation only; frozen before held-out scoring','heldout':binary(actual,predicted),'unscorable_points':unknown,'mean_detected_event_delay_source_seconds':float(np.mean(delays)) if delays else None,'detected_events_with_delay':len(delays),'delay_limitation':'Conditional on detected labelled events; undetected events remain false negatives. Source-local time differences only when timezone is absent.','by_series':details}
    return {'dataset':'Microsoft cloud-monitoring-dataset','series':len(cases),'split':'Each series: first60% train, next20% validation, final20% test; no point adjustment; same common-valid-point mask for both detectors','label_source':'Official CSV Label column, retained unchanged; conflicting annotations excluded rather than changed','methods':methods,'forecasting':forecast,'limitations':['Point labels do not establish a root cause or service graph.','Chronological splits share series; this is not unseen-series generalization.','Pooled validation threshold calibration may weight long series more heavily.'],'source_revision':manifest()['microsoft_revision']}

def localization(rows,method):
    n=len(rows);ranks=[];retrieved=0;covered=0;selected=0;broad=0;latency=[]
    by_fault={};by_system={}
    for row in rows:
        order=row[method];truth=row['truth']['root_cause_service'];rank=order.index(truth)+1 if truth in order else None
        ranks.append(rank);retrieved+=truth in (order[:20] if method!='evidence_gated' else row['retrieval']);covered+=bool(order);selected+=row['selected'];broad+=row['broad'];latency.append(row['elapsed_ms'])
        for key,value in ((by_fault,row['truth']['fault']),(by_system,row['truth']['system'])):key.setdefault(value,[]).append(rank)
    def metrics(r):
        return {'cases':len(r),'top1':sum(v==1 for v in r)/len(r) if r else None,'top3':sum(v is not None and v<=3 for v in r)/len(r) if r else None,'mrr':sum(1/v if v else 0 for v in r)/len(r) if r else None}
    return {**metrics(ranks),'candidate_retrieval_recall_at20':retrieved/n if n else None,'diagnosis_coverage':covered/n if n else None,'mean_selected_resources':selected/n if n else None,'mean_broad_resources':broad/n if n else None,'mean_local_analysis_ms':float(np.mean(latency)) if latency else None,'by_fault':{k:metrics(v) for k,v in by_fault.items()},'by_system':{k:metrics(v) for k,v in by_system.items()}}

def rcaeval():
    cases=[r for r in manifest()['cases'] if r['source']=='rcaeval'];rows=[]
    for i,entry in enumerate(cases):
        case=load_case(entry['id']);start=min(s.observations[0].timestamp for s in case.series);end=max(s.observations[-1].timestamp for s in case.series)
        # A prespecified checkpoint based on recording coordinates, not root cause
        # or injection labels. Prediction inputs stop strictly at this checkpoint.
        checkpoint=min(end,start+(end-start)/2+120)
        began=time.perf_counter();result=analyze_case(case,checkpoint,forecast_enabled=False)
        ungated=analyze_case(case,checkpoint,evidence_gate=False,forecast_enabled=False)
        elapsed=(time.perf_counter()-began)*1000
        temporal={}
        for e in result.evidence:temporal[e.resource]=max(temporal.get(e.resource,0),e.score)
        baseline=sorted(temporal,key=lambda n:(-temporal[n],n))
        # Independent label vault is accessed only after all method predictions.
        truth=labels_for_evaluation(entry['id'])
        rows.append({'case_id':entry['id'],'split':entry['split'],'truth':truth,'checkpoint':checkpoint,'checkpoint_seconds_after_injection':checkpoint-truth['inject_time'],'warmup_precedes_injection':start+min(600,.2*(end-start))<truth['inject_time'],'temporal':baseline,'evidence_gated':[c.resource for c in result.candidates],'without_gate':[c.resource for c in ungated.candidates],'retrieval':result.explanation['retrieval_order'][:20],'selected':result.investigation['selected_resource_count'],'broad':result.investigation['broad_resource_count'],'elapsed_ms':elapsed,'status':result.status})
        if (i+1)%10==0:print(f'RCAEval evaluated {i+1}/{len(cases)}',flush=True)
    splits={split:{method:localization([r for r in rows if r['split']==split],method) for method in ('temporal','without_gate','evidence_gated')} for split in ('train','validation','test')}
    return {'dataset':'RCAEval RE1 recorded controlled benchmark','cases':len(rows),'protocol':'Frozen first min(600 seconds, 20% recording duration) reference; diagnose at recording midpoint +120s, using only prefix telemetry. No root-cause/fault/injection label enters inference. The checkpoint alignment is audited after prediction, not supplied as a detector alert.','splits':splits,'cases_detail':rows,'graph_comparison':{'status':'not_applicable_to_RE1','reason':'No recorded dependency topology in selected metric-only files; no service graph fabricated. See separate Alibaba topology ablation.'},'detection_delay':None,'limitations':['Subset grouped by system/service/fault, all repeated runs remain in one partition.','Fixed-checkpoint localization differs from end-to-end alert-triggered RCA.','No point-level fault mechanism labels are inferred from service rankings.','Local CPU timings and resource-selection counts are not measured AWS cost savings.'],'source_revision':manifest()['rcaeval_revision']}
