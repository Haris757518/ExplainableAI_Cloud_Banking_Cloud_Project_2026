from test_probe_xai import fixture,run
from analysis.recovery_verification import verify_recovery

def test_expensive_code_is_distinguished_from_high_demand():
    r=run(fixture({'latency_ms':100,'cpu_percent':95,'cpu_per_request':.2}))
    assert r['underlying_driver']=='expensive_execution'

def test_reduced_capacity_is_distinguished_from_increased_traffic():
    r=run(fixture({'latency_ms':100,'cpu_percent':95,'worker_count':.5,'cpu_limit':.5,'throttling':.5,'queue_depth':20}))
    assert r['underlying_driver']=='reduced_capacity'

def test_demand_after_cpu_onset_does_not_explain_earlier_cpu_pressure():
    case=fixture({'latency_ms':100,'cpu_percent':95,'request_rate':40,'queue_depth':30})
    for s in case.series:
        if s.metric=='request_rate':
            for p in s.observations:
                if p.timestamp<24:p.value=10
    assert run(case)['underlying_driver'] is None

def test_missing_competing_evidence_prevents_deep_claim():
    r=run(fixture({'latency_ms':100,'cpu_percent':95,'request_rate':40,'queue_depth':30},omit=['gc_pause_ms']))
    assert r['underlying_driver'] is None
    assert any(h['name']=='demand_exceeds_capacity' and h['status']=='supported_hypothesis' for h in r['hypotheses'])

def test_recommendation_alone_is_not_recovery():
    assert verify_recovery(10,20,[{'timestamp':30,'value':20}])['status']=='not_verified'

def test_performance_recovery_requires_transaction_integrity():
    points=[{'timestamp':i,'value':20} for i in [22,23,24]]
    action={'approved':True,'executed_at':21}
    assert verify_recovery(10,20,points,action)['status']=='not_verified'
    integrity={'measured_at':25,'pending_payments_consistent':True,'no_duplicate_processing':True,'ledger_reconciled':True}
    assert verify_recovery(10,20,points,action,integrity)['status']=='recovered'
    points[-1]['value']=100
    assert verify_recovery(10,20,points,action,integrity)['status']=='still_abnormal'
