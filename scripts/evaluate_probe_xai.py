"""Prespecified comparisons on imported RE2 recordings, labels after inference."""
import sys,json,time
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from statistics import mean
import torch
from dataset.re2 import entries,load_re2,truth_re2
from analysis.incident_engine import analyze_case
from analysis.probe_xai import investigate
from ai_models.re2_inference import infer
from dataset.real_banking.store import write_json

ROOT=Path(__file__).resolve().parents[1]
torch.set_num_threads(1)
def main():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--out',default='results/probe_xai/evaluation.json');args=parser.parse_args()
    out=ROOT/'results/probe_xai';out.mkdir(exist_ok=True)
    target=ROOT/args.out
    if target.exists():raise SystemExit('Preserve completed evaluation; choose a new study before changing its protocol.')
    methods={name:[] for name in ['statistical_baseline','gnn_only','gnn_conventional_diagnosis','gnn_probe_xai']}
    details=[]
    for entry in entries()['cases']:
        case=load_re2(entry['id']);times=[p.timestamp for s in case.series for p in s.observations];start,end=min(times),max(times)
        when=start+.5*(end-start)+120
        t=time.perf_counter();incident=analyze_case(case,when,forecast_enabled=False);detection_ms=(time.perf_counter()-t)*1000
        normal_when=start+.4*(end-start)
        normal_incident=analyze_case(case,normal_when,forecast_enabled=False)
        t=time.perf_counter();gnn=infer(case,when);gnn_ms=(time.perf_counter()-t)*1000
        predictions={}
        for name,policy,model,budget in [('statistical_baseline','none',None,0),('gnn_only','none',gnn,0),
                ('gnn_conventional_diagnosis','conventional',gnn,64),('gnn_probe_xai','progressive',gnn,12)]:
            t=time.perf_counter();result=investigate(case,incident,as_of=when,policy=policy,gnn=model,budget=budget)
            duration=(time.perf_counter()-t)*1000+detection_ms+(gnn_ms if model else 0)
            ranking=model['ranking'] if model and model.get('status')=='evaluated' else [c.resource for c in incident.candidates]
            mechanism=next((c['title'].replace(' ','_') for c in result['chain'] if c['level']=='mechanism'),None) if policy!='none' else None
            predictions[name]={'ranking':ranking,'mechanism':mechanism,'underlying_driver':result['underlying_driver'],
                'deepest_level':result['deepest_supported_level'],'followup_queries':len(result['queries']),
                'effort_units':result['query_cost_units'],'diagnosis_ms':duration,'model_status':(model or {}).get('status','not_applied')}
        # Explicit evaluation-only annotation access. Predictions already exist.
        truth=truth_re2(case.id)
        expected={'cpu':'cpu_pressure','mem':'memory_pressure','disk':'disk_degradation','delay':'network_delay','loss':'packet_loss'}.get(truth['fault'])
        for name,p in predictions.items():
            ranking=p['ranking'];rank=ranking.index(truth['root_cause_service'])+1 if truth['root_cause_service'] in ranking else None
            scored={**p,'top1':rank==1,'top3':rank is not None and rank<=3,'mechanism_agreement':p['mechanism']==expected}
            methods[name].append(scored)
        details.append({'case_id':case.id,'as_of':when,'predictions':predictions,'evaluation_only_truth':truth,
            'normal_checkpoint':normal_when,'normal_checkpoint_precedes_injection':normal_when<truth['inject_time'],
            'normal_checkpoint_alert':normal_incident.status=='deviation_detected',
            'diagnosis_checkpoint_follows_injection':when>=truth['inject_time'],
            'diagnosis_checkpoint_alert':incident.status=='deviation_detected'})
        print('Evaluated',case.id,flush=True)
    n=len(details)
    summary={name:{'cases':n,'top1':mean(r['top1'] for r in rows),'top3':mean(r['top3'] for r in rows),
        'mechanism_agreement':mean(r['mechanism_agreement'] for r in rows),'driver_abstention':mean(r['underlying_driver'] is None for r in rows),
        'mean_queries':mean(r['followup_queries'] for r in rows),'mean_effort_units':mean(r['effort_units'] for r in rows),
        'mean_diagnosis_ms':mean(r['diagnosis_ms'] for r in rows),'underlying_driver_accuracy':None,'unsupported_diagnosis_rate':None} for name,rows in methods.items()}
    report={'status':'evaluated','cases':n,'protocol':f'{n} prespecified RE2-OB cases, fixed midpoint plus 120 seconds. Matching per-case prefix-trained GNNs; no diagnosis-label tuning. Same measured prefix across four methods. This is an illustrative compatibility study.',
        'detection':{'pre_injection_checkpoints':sum(r['normal_checkpoint_precedes_injection'] for r in details),
            'pre_injection_alerts':sum(r['normal_checkpoint_precedes_injection'] and r['normal_checkpoint_alert'] for r in details),
            'post_injection_checkpoints':sum(r['diagnosis_checkpoint_follows_injection'] for r in details),
            'post_injection_alerts':sum(r['diagnosis_checkpoint_follows_injection'] and r['diagnosis_checkpoint_alert'] for r in details),
            'interpretation':'One fixed normal and one fixed diagnosis checkpoint per recording, scored after inference. Not pointwise precision/recall or onset detection.'},
        'methods':summary,'case_results':details,
        'conclusion':'This bounded study tests implementation compatibility and diagnostic abstention. It does not establish novelty, generalization or a PROBE-XAI accuracy advantage.',
        'limitations':[f'{n} preselected illustrative cases, not an independent representative test set.',
            'RCAEval injected fault labels do not independently label deeper workload/application drivers; driver accuracy and unsupported-diagnosis rate are unavailable.',
            'Follow-up costs count in-memory recorded-column inspections, not live diagnostic API reads, AWS savings or measured information gain.',
            'GNN checkpoints were fitted independently on each recording prefix; no transfer to banking workload is assumed.',
            'No Bank of Anthos banking transactions or banking safety outcomes were measured in this study.',
            'Budgets are declared method configurations, not tuned test-set optima.'],
        'labels_used_for':'Scoring after all method predictions, never inference','probe_version':'probe-xai-v1'}
    write_json(target,report)
    print(json.dumps(summary,indent=2))

if __name__=='__main__':main()
