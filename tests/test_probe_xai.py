"""Analytical fixtures only. Never exported as workload or research observations."""
from common.research import DataSource,TelemetryCase,TelemetrySeries,TelemetryObservation
from analysis.probe_xai import investigate
from analysis.incident_engine import analyze_case

BASE={'latency_ms':10,'cpu_percent':20,'request_rate':10,'queue_depth':1,'worker_count':2,
 'capacity_rps':20,'cpu_per_request':.02,'retry_rate':.01,'cpu_limit':2,'throttling':.01,
 'external_request_rate':10,'timeouts':1,'memory_percent':40,'gc_pause_ms':1,
 'db_latency_ms':2,'lock_wait_ms':1,'blocked_sessions':1,'transaction_age_seconds':2}

def fixture(changes,omit=()):
    series=[]
    for metric,base in BASE.items():
        if metric in omit:continue
        series.append(TelemetrySeries(id='payment:'+metric,resource='payment',metric=metric,original_metric=metric,
            unit='test fixture units',period_seconds=1,observations=[TelemetryObservation(timestamp=i,value=base if i<20 else changes.get(metric,base)) for i in range(30)]))
    return TelemetryCase(id='analytical-fixture',source=DataSource(id='banking-local',kind='academic_test_application',reference='Unit-test fixture, not an experiment'),collection='fixture',series=series,
        provenance={'baseline_end':19,'recording_end':29})

def run(case,budget=64,as_of=29):
    return investigate(case,analyze_case(case,as_of,forecast_enabled=False),as_of=as_of,budget=budget)

def test_high_cpu_alone_cannot_establish_traffic_overload():
    r=run(fixture({'latency_ms':100,'cpu_percent':95},omit=['request_rate','queue_depth','capacity_rps']))
    assert r['underlying_driver'] is None
    assert r['deepest_supported_level']=='mechanism'
    assert 'Defer scaling' in r['recommendation']['suggested_action']

def test_comprehensive_demand_signature_supports_hypothesis_without_causal_claim():
    r=run(fixture({'latency_ms':100,'cpu_percent':95,'request_rate':40,'queue_depth':30}))
    assert r['underlying_driver']=='demand_exceeds_capacity'
    assert r['causal_confirmation'] is False
    assert r['recommendation']['automatic_execution'] is False

def test_progressive_query_budget_is_enforced():
    r=run(fixture({'latency_ms':100,'cpu_percent':95,'request_rate':40,'queue_depth':30}),budget=3)
    assert r['query_cost_units']<=3
    assert r['underlying_driver'] is None

def test_future_measurements_do_not_change_diagnosis():
    case=fixture({'latency_ms':100,'cpu_percent':95})
    before=run(case,as_of=25)
    for s in case.series:
        for p in s.observations:
            if p.timestamp>25:p.value=100000
    after=run(case,as_of=25)
    assert before==after

def test_changing_case_names_and_injected_labels_cannot_change_diagnosis():
    case=fixture({'latency_ms':100,'cpu_percent':95})
    a=run(case);case.id='fault_is_traffic';case.provenance['root_cause_service']='database';case.provenance['fault']='loss'
    assert a==run(case)

def test_wrong_domain_gnn_is_not_used():
    case=fixture({'latency_ms':100,'cpu_percent':95});incident=analyze_case(case,29,forecast_enabled=False)
    r=investigate(case,incident,as_of=29,gnn={'status':'evaluated','source_checksum':'other','as_of':29,'ranking':['database']})
    assert r['resource']=='payment'

def test_normal_workload_has_no_incident_chain():
    r=run(fixture({}))
    assert r['chain']==[] and r['status']=='no_current_deviation'
