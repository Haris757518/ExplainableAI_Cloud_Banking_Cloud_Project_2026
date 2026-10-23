"""Evaluate the frozen revision on the newly executed AWS repeat workload."""
import argparse,hashlib,json,sys,tarfile
from collections import Counter
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from analysis.banking_replay import ROOT
from analysis.banking_localization import localize
from ai_models import banking_study
from dataset.real_banking.store import write_json

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--export',type=Path,required=True);args=parser.parse_args()
    metadata=json.loads((args.export/'export-manifest.json').read_text());archive=args.export/'evidence.tar.gz'
    assert metadata['hash_verified'] and hashlib.sha256(archive.read_bytes()).hexdigest()==metadata['sha256']
    destination=args.export/'verified-files'
    if not destination.exists():
        with tarfile.open(archive) as source:source.extractall(destination,filter='data')
    telemetry=destination/'telemetry';runs=list(telemetry.glob('final-controlled-*/summary.json'));assert len(runs)==1
    run=runs[0].parent;summary=json.loads(runs[0].read_text())
    for name,sha in summary['files_sha256'].items():assert hashlib.sha256((run/name).read_bytes()).hexdigest()==sha,name
    output=ROOT/'results/final_validation';protocol=json.loads((output/'prospective-protocol.json').read_text())
    scoring_plan=json.loads((output/'scoring-plan.json').read_text())
    assert hashlib.sha256(Path(__file__).read_bytes()).hexdigest()==scoring_plan['evaluation_script_sha256'],'Scoring implementation changed after pre-execution freeze'
    amendment1=json.loads((output/'protocol-amendment-001.json').read_text())
    amendment2=json.loads((output/'protocol-amendment-002.json').read_text())
    amendment3=json.loads((output/'protocol-amendment-003.json').read_text())
    expected={**protocol['source_sha256'],amendment1['file']:amendment1['new_sha256'],**amendment2['source_sha256']}
    for name,sha in expected.items():assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==sha,'Frozen implementation changed: '+name
    amendment4_path=output/'protocol-amendment-004.json'
    identity_amendment=json.loads(amendment4_path.read_text()) if amendment4_path.exists() else amendment3
    assert hashlib.sha256((run/'executed-collector.py').read_bytes()).hexdigest()==identity_amendment['executed_collector_lf_sha256']
    if amendment4_path.exists():
        assert metadata['source_instance']==summary['instance']==identity_amendment['source_instance']
        assert identity_amendment['original_collector_lf_sha256']==amendment3['executed_collector_lf_sha256']
    rows=[json.loads(line) for line in (run/'measurements.jsonl').read_text().splitlines()]
    spans=[]
    for line in (run/'frontend-raw.log').read_text().splitlines():
        if 'RESEARCH_SPAN ' in line:spans.append(json.loads(line.split('RESEARCH_SPAN ',1)[1]))
    banking_study.PROTOCOL.update(train_seconds=protocol['model_train_seconds'],validation_end_seconds=protocol['model_validation_end_seconds'],normal_test_end_seconds=protocol['normal_holdout_end_seconds'])
    model=banking_study.fit_and_predict(rows,spans,summary,output/'banking-models')
    model['limitations'][0]='One new executed workload after the investigator rules were frozen. Models use its normal prefix, with a 72-second normal holdout; this is not cross-recording model transfer.'
    source_start=summary['started_at'];reference_end=source_start+amendment3['localization_baseline_seconds']
    # Freeze predictions before opening intervention annotations.
    predictions=[];cache={}
    for method,models in model['predictions'].items():
        for fitted in models:
            for window in fitted['windows']:
                as_of=window['as_of']
                if as_of not in cache:cache[as_of]=localize(rows,start=source_start,baseline_end=reference_end,as_of=as_of,budget=protocol['localization_budget'])
                refined={**cache[as_of],'gnn_symptom_ranking':window['ranking']}
                predictions.append({'method':method,'seed':fitted['seed'],'as_of':as_of,'gnn_alert':window['alert'],'gnn_ranking':window['ranking'],'localization':refined})
    write_json(output/'predictions-before-label-scoring.json',predictions)
    labels=[json.loads(line) for line in (run/'interventions.jsonl').read_text().splitlines()]
    scores=[]
    for phase in [r for r in labels if r.get('event')=='phase_start' and r['name']!='normal']:
        truth='ledgerwriter' if phase['name'].startswith('reduced_cpu_') else 'ledger-db' if phase['name'].startswith('db_contention_') else None
        if not truth:continue
        when=phase['timestamp']+protocol['fixed_checkpoint_seconds_after_phase_start']
        for method in ('graph','identity'):
            for seed in banking_study.PROTOCOL['seeds']:
                available=[p for p in predictions if p['method']==method and p['seed']==seed and p['as_of']<=when]
                result=available[-1] if available else None;roots=result['localization']['roots'] if result else []
                scores.append({'phase':phase['name'],'method':method,'seed':seed,'evaluation_only_root':truth,'checkpoint':when,
                               'gnn_detected':bool(result and result['gnn_alert']),
                               'gnn_top1':bool(result and result['gnn_ranking'] and result['gnn_ranking'][0]==truth),
                               'refined_top1':len(roots)==1 and roots[0]['resource']==truth,'prediction':result})
    requests=[r for r in rows if r.get('instrument')=='payment_request'];starts=[r for r in rows if r.get('instrument')=='payment_start']
    ledger=json.loads((run/'ledger-after.json').read_text())
    counts=Counter(t['amount'] for t in ledger if t['from_acct']=='1011226111' and t['to_acct']=='1033623433' and t['from_route']=='883745000' and t['to_route']=='883745000')
    amounts=[r['amount_cents'] for r in requests]
    matches=sum(counts[a]==1 for a in amounts)
    baseline=json.loads((telemetry/'final-integrity/baseline/trials.json').read_text())
    patched=json.loads((telemetry/'final-integrity/patched/trials.json').read_text())
    restart=json.loads((telemetry/'final-integrity/patched/after-restart.json').read_text())
    hashes=json.loads((telemetry/'correctness-fix/deployed-class-checksums.json').read_text())
    def correct_trial(trial):
        return trial['held_process_exit']==0 and trial['earlier_id']<trial['later_id'] and len(trial['after']['accounts'])==2 and all(a['api_cents']==a['ledger_cents'] and a['gap_cents']==0 and a['history_ids'].count(trial['earlier_id'])==1 and a['history_ids'].count(trial['later_id'])==1 and len(a['history_ids'])==len(set(a['history_ids'])) for a in trial['after']['accounts'])
    required={t[k] for t in patched for k in ('earlier_id','later_id')}
    restart_ok=len(restart['accounts'])==2 and len(required)==6 and all(a['api_cents']==a['ledger_cents'] and a['gap_cents']==0 and required<=set(a['history_ids']) and len(a['history_ids'])==len(set(a['history_ids'])) for a in restart['accounts'])
    expected_classes=json.loads((ROOT/'deploy/correctness-fix/class-checksums.json').read_text())
    hashes_ok=hashes['expected']==hashes['observed']==expected_classes
    fix_passed=len(patched)==3 and all(correct_trial(t) for t in patched) and restart_ok and hashes_ok
    method_summary={name:{'independent_executed_fault_repetitions':len([r for r in scores if r['method']==name and r['seed']==42]),
                          'seed_results':[{'seed':seed,'gnn_top1_count':sum(r['gnn_top1'] for r in scores if r['method']==name and r['seed']==seed),'refined_top1_count':sum(r['refined_top1'] for r in scores if r['method']==name and r['seed']==seed),'detected_count':sum(r['gnn_detected'] for r in scores if r['method']==name and r['seed']==seed)} for seed in banking_study.PROTOCOL['seeds']]} for name in ('graph','identity')}
    report={'status':'evaluated','source':'New executed AWS Bank of Anthos workload after localization revision freeze','execution_id':summary['execution_id'],
        'export_sha256':metadata['sha256'],'export_directory':str(args.export),'protocol':protocol,'model_study':model,
        'fault_scores':scores,'method_summary':method_summary,'submitted_requests':len(requests),'recorded_starts':len(starts),
        'ledger_matches':matches,'unique_request_amounts':len(set(amounts))==len(amounts),
        'acknowledged_success':sum(r['outcome']=='acknowledged_success' for r in requests),
        'uncertain_requests':sum(r['outcome']=='uncertain' for r in requests),
        'corrective_code':{'verified':fix_passed,'unmodified_trials':len(baseline),'unmodified_incorrect_trials':sum(not correct_trial(r) for r in baseline),
                           'patched_trials':len(patched),'patched_correct_trials':sum(correct_trial(r) for r in patched),'restart_verified':restart_ok,'actual_class_hashes_verified':hashes_ok},
        'limitations':['Six controlled CPU/database repetitions in one new workload on one AWS host; not six independent applications or infrastructures.',
            'The revision was frozen before this workload. GNNs are still trained independently on its normal prefix; cross-recording transfer is not claimed.',
            'Graph and identity variants share the same direct-evidence rules; any improvement from those rules does not establish graph superiority.',
            'Higher traffic is a load condition, not automatically a fault. Its two repetitions are retained but excluded from injected root-service accuracy.',
            'The corrective code uses authoritative reads and may increase database work. Demonstrated correctness under these tests is not universal production certification.']}
    write_json(output/'report.json',report)
    files={name:hashlib.sha256((output/name).read_bytes()).hexdigest() for name in ('report.json','predictions-before-label-scoring.json','aws-cleanup.json')}
    write_json(output/'verified-results.json',{'source_archive_sha256':metadata['sha256'],'files':files})
    print(json.dumps({'method_summary':method_summary,'corrective_code':report['corrective_code'],'submitted_requests':len(requests),'ledger_matches':matches},indent=2))

if __name__=='__main__':main()
