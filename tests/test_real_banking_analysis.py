from datetime import date,timedelta
from analysis.banking_api_anomalies import analyze
from analysis.banking_api_forecasting import evaluate

def rows():
    # Test fixtures only: these values are never saved as banking observations.
    return [{'bank':'Fixture','service':'API','metric':'latency','date':(date(2020,1,1)+timedelta(days=i)).isoformat(),'value':10.} for i in range(100)]

def test_future_values_cannot_change_reference_or_threshold():
    r=rows(); before=analyze(r)['series'][0]
    r[-1]['value']=1000
    after=analyze(r)['series'][0]
    assert before['threshold']==after['threshold'] and before['reference']==after['reference']
    assert after['findings'][-1]['evidence']==r[-1]
    assert after['findings'][-1]['verified_incident'] is False
    assert before['findings']==[]

def test_forecast_uses_only_prior_observations():
    r=rows(); r[-1]['value']=900
    result=evaluate(r)
    assert result['predictions'][-1]['persistence']==10
    assert result['predictions'][-1]['training_median']==10
    assert result['test_count']==20

def test_nulls_do_not_become_zero_observations():
    r=rows(); r[-1]['value']=None
    assert sum(analyze(r)['series'][0]['counts'].values())==99
