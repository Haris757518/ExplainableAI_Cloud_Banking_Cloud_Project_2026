"""Isolated software mechanics. No fixture is published as research telemetry."""
import json,math
import pytest
from common.research import DataSource,TelemetryCase,TelemetrySeries,TelemetryObservation,DependencyEdge
from dataset.benchmarks import parse_microsoft,safe_file
from analysis.incident_engine import analyze_case,capabilities
from analysis.forecasting import forecast_next,forecast_evaluation,fit_models,predict

def fixture_case():
    points=[TelemetryObservation(timestamp=i,value=10 if i<90 else 100) for i in range(120)]
    return TelemetryCase(id='test-only',source=DataSource(id='test-fixture',kind='expert_labelled_series',reference='isolated test fixture'),collection='test-only',series=[TelemetrySeries(id='m',resource='recorded-series',metric='latency',original_metric='fixture',period_seconds=1,observations=points)])

def test_original_labels_rows_and_conflicts_are_preserved(tmp_path):
    path=tmp_path/'fixture.csv';path.write_text('TimeStamp,Value,Label\n2018-01-01 00:00:00,2,0\n2018-01-01 00:00:00,2,1\n2018-01-01 01:00:00,,0\n')
    obs,labels,kind=parse_microsoft(path)
    assert len(obs)==2 and obs[0].source_rows==[0,1] and labels==[None,0]
    assert obs[0].value==2 and obs[1].value is None and 'unspecified' in kind

def test_conflicting_values_remain_unknown(tmp_path):
    path=tmp_path/'fixture.csv';path.write_text('TimeStamp,Value,Label\n2018-01-01,2,0\n2018-01-01,3,0\n')
    obs,labels,_=parse_microsoft(path)
    assert obs[0].value is None and obs[0].quality=='conflicting_source_measurements' and labels==[0]

def test_no_source_path_traversal(tmp_path):
    with pytest.raises(ValueError):safe_file(tmp_path,'../outside.csv')

def test_forecast_insufficient_history():
    s=fixture_case().series[0].model_copy(update={'observations':fixture_case().series[0].observations[:20]})
    assert forecast_next(s).status=='insufficient_history'

def test_forecast_selection_is_chronological_and_serializable():
    case=fixture_case();r=forecast_evaluation(case.series[0])
    assert r['split']['train'][1]==72 and r['split']['test'][0]==96
    assert r['methods']['persistence']['targets']==24
    assert json.loads(forecast_next(case.series[0]).model_dump_json())['status']=='forecast'

def test_ar_lags_never_use_target_or_future():
    values=[float(i) for i in range(100)];model=fit_models(values,60)
    original=predict(values,70,model,'ridge_ar12');values[70:]=[1e12]*30
    assert predict(values,70,model,'ridge_ar12')==original

def test_replay_future_values_cannot_change_current_inference():
    case=fixture_case();a=analyze_case(case,80)
    changed=case.model_copy(deep=True)
    for p in changed.series[0].observations[81:]:p.value=1e9
    b=analyze_case(changed,80)
    assert a.model_dump()==b.model_dump() and a.status=='no_deviation_in_observed_metrics'

def test_labels_are_not_an_inference_argument_or_contract():
    from pydantic import ValidationError
    with pytest.raises(ValidationError):TelemetryCase(**fixture_case().model_dump(),root_cause_service='leaked')
    with pytest.raises(TypeError):analyze_case(fixture_case(),truth='leaked')

def test_gate_rejects_single_point_noise_and_keeps_sustained_deviation():
    case=fixture_case();a=analyze_case(case,90,forecast_enabled=False);b=analyze_case(case,92,forecast_enabled=False)
    assert not a.candidates and b.candidates and b.cause_verified is False
    assert b.recommendations[0].mechanism_status.startswith('suspected')

def test_no_graph_fabricated_for_univariate_series():
    r=analyze_case(fixture_case(),92)
    assert r.graph['edges']==[] and r.explanation['gnn_used'] is False

def test_unsupported_network_loss_is_not_claimed():
    r=next(c for c in capabilities(['latency'],False) if c['family']=='packet_loss')
    assert r['supported'] is False

def test_investigation_frontier_is_bounded():
    result=analyze_case(fixture_case(),92)
    assert len(result.investigation['resources'])<=3
    assert result.investigation['actual_external_calls']==0 and result.investigation['cost_savings'] is None

def test_research_endpoints_and_persistence(monkeypatch):
    from backend.main import app
    from fastapi.testclient import TestClient
    import backend.research_api as api
    monkeypatch.setattr(api,'read_case',lambda case_id:fixture_case())
    with TestClient(app) as client:
        r=client.get('/api/research/replay/test-only?as_of=92');assert r.status_code==200
        assert all(p['timestamp']<=92 for s in r.json()['histories'] for p in s['observations'])
        assert client.get('/api/research/replay/test-only?as_of=9999').status_code==422
        r=client.post('/api/research/incidents/test-only?as_of=92');assert r.status_code==200
        assert client.get('/api/research/incidents').json()['incidents']

def test_imported_grouped_splits_if_available():
    from dataset.benchmarks import manifest
    rows=[r for r in manifest()['cases'] if r['source']=='rcaeval']
    if not rows:pytest.skip('Official dataset not imported')
    groups={}
    for row in rows:groups.setdefault(row['group'],set()).add(row['split'])
    assert all(len(s)==1 for s in groups.values())

def test_topology_selection_excludes_later_call_frequencies(tmp_path):
    from dataset.observed_trace import measured_snapshot
    lines=['timestamp,traceid,rpcid,um,rpctype,dm,rt','0,early,1,A,rpc,B,10']
    lines += [f'1000,late{i},1,C,rpc,D,20' for i in range(30)]
    (tmp_path/'MSCallGraph.csv').write_text('\n'.join(lines)+'\n')
    result=measured_snapshot(tmp_path,max_services=2,max_edges=1,selection_end_ms=500)
    assert {n['id'] for n in result.nodes}=={'A','B'}

def test_irregular_forecast_does_not_invent_calendar_timestamp():
    case=fixture_case();case.series[0].observations[-1].timestamp+=5
    result=forecast_next(case.series[0])
    assert result.status=='forecast' and result.timestamp is None
    assert 'Irregular' in result.reliability

def test_authenticated_but_unauthorized_aws_is_not_healthy(monkeypatch):
    from backend.main import app,settings
    from aws.discovery import AWSDiscoveryError
    from fastapi.testclient import TestClient
    monkeypatch.setattr(settings,'aws_mode',True)
    monkeypatch.setattr('backend.main.AWSDiscovery.status',lambda self:{'connected':True})
    def denied(self):raise AWSDiscoveryError('UnauthorizedOperation: resource discovery denied')
    monkeypatch.setattr('backend.main.AWSDiscovery.discover',denied)
    with TestClient(app) as client:
        response=client.post('/api/aws/analyze')
    assert response.status_code==502
    assert 'UnauthorizedOperation' in response.json()['detail']
    assert response.json().get('is_anomaly') is None
