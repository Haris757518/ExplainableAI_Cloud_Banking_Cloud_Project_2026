"""Isolated fixtures validate mechanics; never published as measured research."""
import pytest
from common.research import DataSource,TelemetryCase,TelemetrySeries,TelemetryObservation,DependencyEdge
from analysis.incident_engine import analyze_case
from analysis.mechanisms import resource_labels

def case(metrics):
    return TelemetryCase(id='isolated-unit-fixture',collection='fixture',source=DataSource(id='rcaeval',kind='recorded_controlled_benchmark',reference='unit-test fixture'),provenance={'recording_end':120},series=[TelemetrySeries(id=m,resource='carservice',metric=m,original_metric=m,observations=[TelemetryObservation(timestamp=i,value=10 if i<90 else value) for i in range(121)]) for m,value in metrics.items()])

def test_latency_is_symptom_and_never_implies_database_lock():
    incident=analyze_case(case({'latency':100}),100,forecast_enabled=False)
    d=incident.explanation['diagnosis'];assert d['mechanism']=='unknown'
    assert all('blocking' not in r.diagnostic_action for r in incident.recommendations)
    assert incident.candidates[0].resource=='carservice'

@pytest.mark.parametrize('metric,expected',[('cpu','cpu_pressure'),('mem','memory_pressure'),('disk_latency','disk_degradation'),('packet_loss','packet_loss'),('network_latency','network_delay'),('db_connection_ms','connection_delay'),('blocked_sessions','lock_contention'),('query_latency','database_query_delay'),('errors','service_failures')])
def test_direct_metric_hypothesis_requires_observed_persistent_deviation(metric,expected):
    d=analyze_case(case({metric:100}),100,forecast_enabled=False).explanation['diagnosis']
    assert d['mechanism']==expected and not d['verified']
    assert d['hypotheses'][0]['supporting_evidence'][0]['metric']==metric

def test_contradictory_and_missing_evidence_exposed():
    d=analyze_case(case({'latency':100,'cpu':10}),100,forecast_enabled=False).explanation['diagnosis']
    cpu=next(h for h in d['hypotheses'] if h['mechanism']=='cpu_pressure')
    assert cpu['status']=='contradicted_by_current_measurements' and cpu['contradictory_evidence']
    assert next(h for h in d['hypotheses'] if h['mechanism']=='packet_loss')['status']=='insufficient_evidence'

def test_request_rate_alone_does_not_prove_overload():
    d=analyze_case(case({'load':100}),100,forecast_enabled=False).explanation['diagnosis']
    assert d['mechanism']=='unknown'

def test_pool_waiters_do_not_prove_exhaustion_without_limit():
    assert analyze_case(case({'pool_waiters':100}),100,forecast_enabled=False).explanation['diagnosis']['mechanism']=='unknown'

def test_no_future_values_or_edges_enter_diagnosis():
    c=case({'latency':100,'cpu':100});c.edges=[DependencyEdge(source='carservice',target='other',provenance='fixture',observed_at=110)]
    a=analyze_case(c,100,forecast_enabled=False)
    for s in c.series:
        for p in s.observations:
            if p.timestamp>100:p.value=1e12
    b=analyze_case(c,100,forecast_enabled=False)
    assert a.model_dump()==b.model_dump() and not a.graph['edges']

def test_label_metadata_never_selects_mechanism():
    c=case({'cpu':100});before=analyze_case(c,100,forecast_enabled=False).explanation['diagnosis']
    c.id='opaque-replacement';c.provenance['fault']='disk';c.provenance['root_cause_service']='fake'
    assert analyze_case(c,100,forecast_enabled=False).explanation['diagnosis']==before

def test_aliases_do_not_invent_service_identity():
    labels=resource_labels(['a9849882312323f12345678998','paymentservice','carservice','ts-order-service'])
    assert labels['paymentservice']=='Payment Service' and labels['a9849882312323f12345678998'].startswith('Resource ')
    assert labels['carservice']=='Carservice' and labels['ts-order-service']=='Order Service'

def test_normal_state_has_no_empty_diagnosis_actions():
    incident=analyze_case(case({'cpu':10}),100,forecast_enabled=False)
    assert incident.status=='no_deviation_in_observed_metrics' and not incident.recommendations
    assert incident.explanation['diagnosis']['mechanism']=='unknown'

def test_verify_endpoint_refuses_uncompleted_recording(monkeypatch):
    from backend import research_api
    from fastapi import HTTPException
    monkeypatch.setattr(research_api,'read_case',lambda _:case({'cpu':100}))
    with pytest.raises(HTTPException) as e:research_api.verify_completed('fixture',100)
    assert e.value.status_code==409

def test_representative_split_keeps_repetitions_together():
    from pathlib import Path
    import json
    p=Path('results/research_v4/mechanisms_20261016/report.json')
    if not p.exists():pytest.skip('Optional measured experiment not run')
    report=json.loads(p.read_text());groups={}
    for row in report['cases']:groups.setdefault(row['group'],set()).add(row['split'])
    assert all(len(s)==1 for s in groups.values())
    test=[r for r in report['cases'] if r['split']=='test']
    assert len(test)==25 and {r['truth'] for r in test}=={'cpu','mem','disk','delay','loss'}


def test_application_processing_requires_direct_timing():
    d=analyze_case(case({'server_latency_ms':100}),100,forecast_enabled=False).explanation['diagnosis']
    assert d['mechanism']=='application_processing_delay' and not d['verified']

def test_recorded_dependency_deviation_is_not_automatically_failure():
    c=case({'latency':100});other=c.series[0].model_copy(deep=True,update={'id':'other-latency','resource':'other'})
    for point in other.observations:
        if point.timestamp>=90:point.value=20
    c.series.append(other);c.edges=[DependencyEdge(source='carservice',target='other',provenance='isolated fixture')]
    result=analyze_case(c,100,forecast_enabled=False)
    hypotheses=result.explanation['diagnosis']['hypotheses']
    assert any(h['mechanism']=='dependency_degradation' for h in hypotheses)
    assert all(h['mechanism']!='dependency_failure' for h in hypotheses)

def test_official_re2_graph_availability_and_label_boundary():
    from dataset.re2 import entries,load_re2
    if not entries()['cases']:pytest.skip('Optional RE2 recordings not imported')
    c=load_re2(entries()['cases'][0]['id'])
    assert c.edges and all(e.observed_at is not None for e in c.edges)
    assert not {'fault','root_cause_service','inject_time'} & c.provenance.keys()
    first=min(e.observed_at for e in c.edges)
    assert not analyze_case(c,first-1,forecast_enabled=False).graph['edges']
    later=analyze_case(c,first+1,forecast_enabled=False)
    assert all(e['observed_at']<=first+1 for e in later.graph['edges'])

def test_saved_graph_study_warmup_and_labels_are_separate():
    from pathlib import Path
    import json
    p=Path('results/research_v4/re2_graph_20261016_02/report.json')
    if not p.exists():pytest.skip('Optional graph study not run')
    report=json.loads(p.read_text())
    assert len(report['cases'])==5
    for row in report['cases']:
        assert row['train_end']<row['validation_end']<row['truth']['inject_time']<row['checkpoint']
        assert row['edges'] and all(e['observed_at']<=row['train_end'] for e in row['edges'])


def test_selected_metric_forecast_is_requested_from_prefix_only(monkeypatch):
    from backend import research_api
    c=case({'cpu':100})
    for i in range(5):c.series.append(c.series[0].model_copy(deep=True,update={'id':f'extra-{i}','metric':f'extra-{i}'}))
    monkeypatch.setattr(research_api,'read_case',lambda _:c)
    before=research_api.frame('fixture',100,metric_id='extra-4')
    predicted=next(f for f in before['incident']['forecasts'] if f['series_id']=='extra-4')
    for s in c.series:
        for point in s.observations:
            if point.timestamp>100:point.value=1e10
    after=research_api.frame('fixture',100,metric_id='extra-4')
    assert predicted==next(f for f in after['incident']['forecasts'] if f['series_id']=='extra-4')
    assert all(p['timestamp']<=100 for p in after['histories'][0]['observations'])
