"""Preserve failed GNN rankings and evaluate evidence-guided localization separately."""
import json,sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from analysis.banking_replay import ROOT,load_evidence
from analysis.banking_localization import localize

files,_=load_evidence();rows=[json.loads(line) for line in files['measurements.jsonl'].splitlines()]
summary=json.loads(files['summary.json']);original=json.loads((ROOT/'results/banking_study/v1/report.json').read_text())
predictions=[]
for method,models in original['predictions'].items():
    for model in models:
        for window in model['windows']:
            if window['as_of']<=summary['started_at']+60:continue
            result=localize(rows,start=summary['started_at'],baseline_end=summary['started_at']+60,as_of=window['as_of'],gnn_ranking=window['ranking'])
            predictions.append({'method':method,'seed':model['seed'],'as_of':window['as_of'],'result':result})
# Evaluation-only truth is consulted only after all revised predictions exist.
scores=[]
for old in original['evaluation_only_injected_cases']:
    available=[p for p in predictions if p['method']==old['method'] and p['seed']==old['seed'] and p['as_of']<=old['checkpoint']]
    revised=available[-1]['result'] if available else None
    roots=revised['roots'] if revised else []
    scores.append({'phase':old['phase'],'method':old['method'],'seed':old['seed'],'gnn_top1':old['top1'],
                   'evidence_localization_top1':len(roots)==1 and roots[0]['resource']==old['evaluation_only_root'],
                   'revised':revised})
output=ROOT/'results/banking_study/localization-revision.json'
report={'status':'evaluated','cases':2,'protocol':'Same two previously inspected injected cases, fixed injection+30s checkpoints. Development-set regression, not an independent accuracy test.',
        'scores':scores,'predictions':predictions,
        'conclusion':'Evidence-guided localization is a separately evaluated hybrid; the original GNN scores and failed rankings are unchanged.',
        'limitations':['This revision was developed after inspecting the failed cases; independent new executions are required before a generalization claim.']}
output.write_text(json.dumps(report,indent=2))
print([(r['phase'],r['method'],r['seed'],r['gnn_top1'],r['evidence_localization_top1']) for r in scores])
