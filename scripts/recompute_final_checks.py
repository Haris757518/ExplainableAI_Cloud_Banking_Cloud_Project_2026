"""Recompute final workload accounting and localization from bundled inputs.

No cloud calls, retraining, or fault execution. Candidate predictions are
computed from measurements before intervention annotations are opened.
"""
import hashlib
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from analysis.banking_localization import localize
from analysis.banking_followup import verified_final_study, verified_corrective_code

ROOT=Path(__file__).resolve().parents[1]


def main():
    report=verified_final_study()
    assert report,'Final report integrity or cleanup verification failed'
    raw=ROOT/'results/final_validation/raw'
    manifest=json.loads((raw/'manifest.json').read_text())
    assert manifest['source_archive_sha256']==report['export_sha256']
    for name,sha in manifest['files'].items():
        assert name in ('measurements.jsonl','frontend-raw.log','ledger-after.json','executed-collector.py','interventions.jsonl','summary.json','recovery-balance-history.json','recovery-transfer-0.json','recovery-transfer-1.json','recovery-transfer-2.json')
        assert hashlib.sha256((raw/name).read_bytes()).hexdigest()==sha,name
    for name,sha in manifest['model_files'].items():
        assert name in {f'{method}-{seed}.pt' for method in ('graph','identity') for seed in (42,43,44)}
        assert hashlib.sha256((raw.parent/'banking-models'/name).read_bytes()).hexdigest()==sha,name
    summary=json.loads((raw/'summary.json').read_text())
    rows=[json.loads(line) for line in (raw/'measurements.jsonl').read_text().splitlines()]
    # Match the original scoring plan: all available windows precede label use.
    saved=json.loads((raw.parent/'predictions-before-label-scoring.json').read_text())
    start=summary['started_at'];baseline_end=start+288;cache={}
    for prediction in saved:
        when=prediction['as_of']
        if when not in cache:cache[when]=localize(rows,start=start,baseline_end=baseline_end,as_of=when,budget=8)
        expected=prediction['localization']
        assert cache[when]['roots']==expected['roots'],'Localization differs from retained prediction'
    labels=[json.loads(line) for line in (raw/'interventions.jsonl').read_text().splitlines()]
    counts={}
    for method in ('graph','identity'):
        for seed in (42,43,44):
            actual={'gnn_top1_count':0,'refined_top1_count':0,'detected_count':0}
            for phase in labels:
                if phase.get('event')!='phase_start':continue
                truth='ledgerwriter' if phase['name'].startswith('reduced_cpu_') else 'ledger-db' if phase['name'].startswith('db_contention_') else None
                if not truth:continue
                available=[p for p in saved if p['method']==method and p['seed']==seed and p['as_of']<=phase['timestamp']+30]
                p=available[-1] if available else None
                roots=cache[p['as_of']]['roots'] if p else []
                actual['gnn_top1_count']+=bool(p and p['gnn_ranking'] and p['gnn_ranking'][0]==truth)
                actual['refined_top1_count']+=len(roots)==1 and roots[0]['resource']==truth
                actual['detected_count']+=bool(p and p['gnn_alert'])
            retained=next(r for r in report['method_summary'][method]['seed_results'] if r['seed']==seed)
            assert all(retained[k]==v for k,v in actual.items()),(method,seed,actual)
            counts[f'{method}-seed-{seed}']=actual
    requests=[r for r in rows if r.get('instrument')=='payment_request']
    ledger=json.loads((raw/'ledger-after.json').read_text())
    ledger_counts=Counter(t['amount'] for t in ledger if t['from_acct']=='1011226111' and t['to_acct']=='1033623433' and t['from_route']==t['to_route']=='883745000')
    matches=sum(ledger_counts[r['amount_cents']]==1 for r in requests)
    assert matches==report['ledger_matches'] and len(requests)==report['submitted_requests']
    proof=verified_corrective_code();assert proof and proof['verified']
    recovery=json.loads((raw/'recovery-balance-history.json').read_text())
    assert recovery['checked_at']>summary['ended_at'] and len(recovery['accounts'])==2
    assert all(a['api_balance_cents']==a['ledger_expected_balance_cents'] and a['history_unique_ids'] for a in recovery['accounts'])
    assert len(recovery['observations'])>=3 and all(o['http_status']==200 and o['timestamp']>summary['ended_at'] for o in recovery['observations'])
    assert recovery['blocked_database_sessions']==0 and recovery['ledgerwriter_pod_resources']['limits']['cpu']=='500m'
    receipts=[json.loads((raw/f'recovery-transfer-{i}.json').read_text()) for i in range(3)]
    assert len({r['transaction_id'] for r in receipts})==3 and all(r['status']=='verified' and r['ledger_new_records']==1 and r['history_record_found'] for r in receipts)
    assert all(any(q['path']=='/payment' and q['start_time_unix_ns']/1e9>summary['ended_at'] for q in r['requests']) for r in receipts)
    print(json.dumps({'status':'recomputed','requests':len(requests),'ledger_matches':matches,'scores':counts,'corrective_code_verified':True,
        'later_recovery_verified':True,
        'scope':'Direct-evidence localization and fixed-checkpoint metrics recomputed; saved GNN rankings and six checkpoint hashes verified. This command does not retrain models.'},indent=2))


if __name__=='__main__':main()
