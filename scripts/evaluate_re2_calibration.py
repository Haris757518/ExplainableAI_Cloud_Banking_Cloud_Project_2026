"""Evaluate calibrated detection on the fixed legacy checkpoints without label tuning."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import torch
from dataset.re2 import entries,load_re2,truth_re2
from ai_models.re2_detection import PROTOCOL,calibrated_scores,decide
from dataset.real_banking.store import ROOT,write_json
torch.set_num_threads(2)
predictions=[]
for entry in entries()['cases']:
    case=load_re2(entry['id']);times=[p.timestamp for s in case.series for p in s.observations];start,end=min(times),max(times)
    calibrated=calibrated_scores(case)
    predictions.append({'case_id':case.id,'source_checksum':case.collection,'calibration':{k:v for k,v in calibrated.items() if k!='points'},
                        'normal_time':start+.4*(end-start),'fault_time':start+.5*(end-start)+120,
                        'normal':decide(calibrated,start+.4*(end-start)),'fault':decide(calibrated,start+.5*(end-start)+120)})
    print(case.id,flush=True)
# No fault annotation has been consulted before predictions are complete.
tp=fp=tn=fn=0
for row in predictions:
    truth=truth_re2(row['case_id']);row['evaluation_only_injection_time']=truth['inject_time']
    assert row['normal_time']<truth['inject_time']<=row['fault_time']
    if row['normal']['status']=='deviation_detected':fp+=1
    else:tn+=1
    if row['fault']['status']=='deviation_detected':tp+=1
    else:fn+=1
precision=tp/(tp+fp) if tp+fp else 0;recall=tp/(tp+fn) if tp+fn else 0
report={'status':'evaluated','protocol':PROTOCOL,'cases':len(predictions),'checkpoint_predictions':predictions,
        'confusion':{'true_positive':tp,'false_positive':fp,'true_negative':tn,'false_negative':fn},
        'precision':precision,'recall':recall,'f1':2*precision*recall/(precision+recall) if precision+recall else 0,
        'metric_unit':'One fixed pre-injection and one fixed post-injection checkpoint per recording, not every time point.',
        'previous_pre_injection_alerts':11,'labels_used_for':'Scoring after prediction only',
        'limitations':['The collection was already inspected during development; this is a calibration audit, not an independent test set.',
                       'Model selection and threshold calibration share the validation prefix; no formal false-alarm bound is claimed.']}
path=ROOT/'results/probe_xai/calibrated-detection.json'
if path.exists():raise SystemExit('Preserve the completed calibration audit.')
write_json(path,report);print(json.dumps({k:report[k] for k in ('confusion','precision','recall','f1')}))
