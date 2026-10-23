import json
from analysis.banking_replay import load_evidence,summarize
from analysis.banking_localization import localize

def recording():
    files,_=load_evidence()
    return [json.loads(line) for line in files['measurements.jsonl'].splitlines()],json.loads(files['summary.json'])['started_at']

def test_evidence_refines_wrong_symptom_ranks_without_rewriting_them():
    rows,start=recording()
    for when,expected in [(1792691440.3528275,'ledgerwriter'),(1792691578.482533,'ledger-db')]:
        result=localize(rows,start=start,baseline_end=start+60,as_of=when,gnn_ranking=['frontend','ledgerwriter','ledger-db'])
        assert result['roots'][0]['resource']==expected
        assert result['gnn_symptom_ranking'][0]=='frontend'
        assert result['causal_confirmation'] is False

def test_no_budget_or_missing_measurements_cannot_create_cause():
    rows,start=recording()
    result=localize(rows,start=start,baseline_end=start+60,as_of=1792691440.3528275,budget=0)
    assert result['roots']==[] and result['queries']==[]
    missing=[r for r in rows if r.get('instrument')!='periodic_snapshot']
    result=localize(missing,start=start,baseline_end=start+60,as_of=1792691440.3528275)
    assert result['roots']==[]

def test_immediate_start_events_keep_arrival_rate_separate_from_timeouts():
    # Software fixture only, not an exported workload observation.
    rows=[{'instrument':'payment_start','timestamp':10},
          {'instrument':'payment_request','timestamp':10,'completed_at':25,'latency_ms':15000}]
    summary=summarize(rows,0,20)
    assert summary['requests']==0 and summary['arrival_rps']==.05

def test_future_completed_snapshot_cannot_localize_current_cause():
    rows,start=recording();when=1792691440.3528275
    altered=[]
    for row in rows:
        if row.get('instrument')=='periodic_snapshot' and row['timestamp']>start+60:
            row={**row,'collection_elapsed_ms':1e12}
        altered.append(row)
    result=localize(altered,start=start,baseline_end=start+60,as_of=when)
    assert result['roots']==[]
