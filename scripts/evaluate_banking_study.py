"""Run the retrospective banking study; labels are read only after predictions."""
import hashlib,json,sys,tarfile
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from analysis.banking_replay import ROOT,load_evidence,run_replay
from ai_models.banking_study import fit_and_predict
from dataset.real_banking.store import write_json

RETAINED=Path(r'D:\BankingResearch\Telemetry\aws-export-20261022T182441Z\verified-files\telemetry\controlled-20261022T174849Z')
OUT=ROOT/'results/banking_study/v1'

def main():
    files,manifest=load_evidence()
    summary=json.loads(files['summary.json'])
    raw=(RETAINED/'frontend-raw.log').read_bytes()
    assert hashlib.sha256(raw).hexdigest()==summary['files_sha256']['frontend-raw.log']
    spans=[]
    for line in raw.decode(errors='replace').splitlines():
        if 'RESEARCH_SPAN ' not in line:continue
        spans.append(json.loads(line.split('RESEARCH_SPAN ',1)[1]))
    rows=[json.loads(line) for line in files['measurements.jsonl'].splitlines()]
    report=fit_and_predict(rows,spans,summary,OUT)
    evidence=OUT/'evidence';evidence.mkdir()
    (evidence/'frontend-spans.jsonl').write_text('\n'.join(json.dumps(s,separators=(',',':')) for s in spans)+'\n')
    # All predictions exist before any intervention metadata is read.
    labels=(RETAINED/'interventions.jsonl').read_bytes()
    assert hashlib.sha256(labels).hexdigest()==summary['files_sha256']['interventions.jsonl']
    (evidence/'evaluation-only-interventions.jsonl').write_bytes(labels)
    starts=[json.loads(line) for line in labels.splitlines() if json.loads(line).get('event')=='phase_start']
    scored=[]
    for phase in starts:
        truth={'reduced_cpu':'ledgerwriter','db_contention':'ledger-db'}.get(phase['name'])
        if not truth:continue
        for method,models in report['predictions'].items():
            for model in models:
                available=[w for w in model['windows'] if w['as_of']<=phase['timestamp']+30 and w['has_measured_targets']]
                observed=available[-1] if available else None
                scored.append({'phase':phase['name'],'evaluation_only_root':truth,'method':method,'seed':model['seed'],
                               'checkpoint':phase['timestamp']+30,'observed_window':observed,
                               'top1':bool(observed and observed['ranking'] and observed['ranking'][0]==truth),
                               'detected':bool(observed and observed['alert'])})
    report['evaluation_only_injected_cases']=scored
    report['injected_case_count']=2
    report['source_archive_sha256']=manifest['archive_sha256']
    report['status']='evaluated'
    report['conclusion']='This completed within-recording study evaluates feasibility and failure modes. It does not establish independent banking generalization or GNN superiority.'
    # Recovery-gate ablation uses two separately retained real observation sets.
    earlier=Path(r'D:\BankingResearch\Telemetry\aws-export-20261022T180343Z\evidence.tar.gz')
    with tarfile.open(earlier) as archive:
        name=next(n for n in archive.getnames() if n.endswith('balance-history-reconciliation.json'))
        initial=archive.extractfile(name).read()
    (evidence/'before-resynchronization.json').write_bytes(initial)
    cases=[]
    for name,data in [('Before reader resynchronization',json.loads(initial)),('After reader resynchronization',json.loads(files['balance-history-reconciliation.json']))]:
        # Illustrative fixed policy, not a calibrated SLO; same rule in both arms.
        speed=len(data['observations'])>=3 and all(o['http_status']==200 and o['balance_read_latency_ms']<100 for o in data['observations']) and data['blocked_database_sessions']==0
        correctness=all(a['api_balance_cents']==a['ledger_expected_balance_cents'] and a['history_unique_ids'] for a in data['accounts'])
        cases.append({'case':name,'checked_at':data['checked_at'],'performance_only_recovery':speed,'integrity_gated_recovery':speed and correctness,
                      'balance_gap_cents':max(abs(a['api_balance_cents']-a['ledger_expected_balance_cents']) for a in data['accounts']),
                      'correctness_checks_passed':correctness})
    report['recovery_gate_ablation']={'cases':cases,'scope':'Two observation sets from one real workload, not independent trials. Speed is a demonstrative <100 ms balance-read policy. Transfer verification remains a separate requirement for the full replay.'}
    report['evidence_files_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in evidence.iterdir()}
    write_json(OUT/'report.json',report)
    for row in report['methods']:print(row)
    print('Recovery gate:',cases)

if __name__=='__main__':main()
