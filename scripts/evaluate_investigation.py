"""Measured offline follow-up reads, never simulated AWS collection savings."""
from pathlib import Path
import sys,json,time,random,argparse
import numpy as np
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from dataset.benchmarks import manifest,load_case,labels_for_evaluation,ROOT
from analysis.incident_engine import analyze_case
from common.research import TelemetryObservation

def main():
    p=argparse.ArgumentParser();p.add_argument('--out',required=True);args=p.parse_args();out=Path(args.out)
    if out.exists():raise SystemExit('Choose a new output path; preserve historical results.')
    import pyarrow.parquet as pq
    rows=[]
    for i,entry in enumerate(r for r in manifest()['cases'] if r['source']=='rcaeval' and r['split']=='test'):
        case=load_case(entry['id']);first=min(s.observations[0].timestamp for s in case.series);last=max(s.observations[-1].timestamp for s in case.series);checkpoint=first+(last-first)/2+120
        initial=analyze_case(case,checkpoint,forecast_enabled=False);resources=sorted({s.resource for s in case.series});rng=random.Random(42)
        top=initial.investigation['resources'];strategies={'broad':resources,'uniform_first3':resources[:3],'random3_seed42':rng.sample(resources,min(3,len(resources))),'static_one_hop':top,'evidence_frontier':top,'legacy_top1_frontier':top[:1]}
        predictions={}
        for method,selected in strategies.items():
            columns=[s.id for s in case.series if s.resource in selected]
            if not columns:
                predictions[method]={'resources':0,'metric_columns':0,'file_read_calls':0,'new_valid_measurements':0,'ranked':[],'elapsed_ms':0,'table_memory_bytes':0};continue
            began=time.perf_counter();table=pq.read_table(ROOT/entry['file'],columns=['time']+columns);data=table.to_pydict();times=data.pop('time');updates={}
            for column,values in data.items():updates[column]=[TelemetryObservation(timestamp=float(t),value=float(v) if v is not None and np.isfinite(v) else None) for t,v in zip(times,values) if t<=checkpoint+60]
            # Follow-up reranking inspects only selected resources, explicitly
            # omitting uncollected current measurements rather than backfilling.
            subset=case.model_copy(update={'series':[s.model_copy(update={'observations':updates[s.id]}) for s in case.series if s.id in updates]})
            result=analyze_case(subset,checkpoint+60,forecast_enabled=False)
            predictions[method]={'resources':len(selected),'metric_columns':len(columns),'file_read_calls':1,'new_valid_measurements':sum(p.value is not None and checkpoint<p.timestamp<=checkpoint+60 for points in updates.values() for p in points),'ranked':[c.resource for c in result.candidates],'elapsed_ms':(time.perf_counter()-began)*1000,'table_memory_bytes':table.nbytes}
        truth=labels_for_evaluation(entry['id'])
        for r in predictions.values():
            rank=r['ranked'].index(truth['root_cause_service'])+1 if truth['root_cause_service'] in r['ranked'] else None
            r.update(top1=rank==1,top3=rank is not None and rank<=3,mrr=1/rank if rank else 0)
        rows.append({'case_id':entry['id'],'strategies':predictions})
        if (i+1)%5==0:print('Follow-up evaluated',i+1,flush=True)
    summary={}
    for method in ('broad','uniform_first3','random3_seed42','static_one_hop','evidence_frontier','legacy_top1_frontier'):
        selected=[row['strategies'][method] for row in rows]
        summary[method]={key:float(np.mean([r[key] for r in selected])) for key in ('resources','metric_columns','file_read_calls','new_valid_measurements','elapsed_ms','table_memory_bytes','top1','top3','mrr')}
    report={'dataset':'RCAEval RE1 held-out cases only','cases':len(rows),'summary':summary,'details':rows,'scope':'Actual local Parquet column reads and subsequent recorded measurements at checkpoint+60 seconds; not live data collection. Initial broad detection cost is excluded from marginal follow-up accounting.','limitations':['Static one-hop and evidence-frontier coincide when no recorded topology exists; no graph advantage claimed.','One file read per nonempty strategy; fewer columns are not fewer AWS API calls.','table_memory_bytes is an in-memory data-volume proxy, not cloud billing or disk bytes read.','Uniform/random selections can miss a cause; abstention is included in accuracy denominators.','No anomaly labels or root causes are used for resource selection.']}
    out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
