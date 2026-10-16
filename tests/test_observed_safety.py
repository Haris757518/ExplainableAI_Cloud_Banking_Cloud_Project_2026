"""Software fixtures only; excluded from research evidence."""
from analysis.observed import deviation

def test_duplicates_do_not_create_history():
    assert deviation([{'timestamp_ms':0,'value':1}]*10) is None

def test_conflicting_duplicate_is_excluded():
    points=[{'timestamp_ms':i,'value':10} for i in range(6)]
    points.append({'timestamp_ms':5,'value':100})
    assert deviation(points) is None

def test_chronological_holdout_and_nonfinite():
    points=[{'timestamp_ms':i,'value':10 if i<5 else 100} for i in range(6)]
    points.append({'timestamp_ms':7,'value':float('nan')})
    result=deviation(list(reversed(points)))
    assert result['reference_median']==10 and result['latest']==100

def test_fault_routes_absent():
    from backend.main import app
    assert not any(getattr(r,'path','').startswith('/api/lab') for r in app.routes)

def test_recollection_counts_each_metric_separately():
    from analysis.evidence import compare_series
    old={'n':{'a':[{'timestamp_ms':5,'value':2}], 'b':[{'timestamp_ms':2,'value':1}]}}
    new={'n':{'a':[{'timestamp_ms':5,'value':2}], 'b':[{'timestamp_ms':3,'value':1}]}}
    result=compare_series(old,new)
    assert result[0]['new_point_count']==0 and result[1]['new_point_count']==1

def test_database_abstains_without_blocking_evidence():
    from analysis.evidence import database_findings
    assert database_findings({})['cause_status']=='cause_not_established'
    assert database_findings({'observation':{'blocked_sessions':0}})['causal_confirmation'] is False

def test_stale_live_metrics_cannot_be_current_anomalies():
    from datetime import datetime,timezone
    from common.schema import AnalysisSample,GraphNode,TransactionContext
    from analysis.observed import analyze_observed
    sample=AnalysisSample(transaction=TransactionContext(id='fixture',type='OBSERVABILITY_PROBE'),nodes=[GraphNode(id='n',type='ec2',label='test')],edges=[],telemetry=[],scenario='UNLABELED',source='aws_cloudwatch',metadata={'collection':{'timestamp':datetime.now(timezone.utc).isoformat()},'series':{'n':{'cpu_percent':[{'timestamp_ms':i*60000,'value':10 if i<5 else 100} for i in range(6)]}}})
    result=analyze_observed(sample)
    assert result.is_anomaly is None and result.root_causes==[]
    assert result.assessment['excluded_series'][0]['freshness']=='stale'


def test_cloudwatch_partial_and_malformed_are_not_complete():
    from aws.cloudwatch_adapter import CloudWatchAdapter
    from datetime import datetime,timezone
    class Incomplete:
        def get_metric_data(self,**kwargs):
            return {'MetricDataResults':[{'Id':'m0','StatusCode':'PartialData','Timestamps':[datetime.now(timezone.utc)],'Values':[]}]}
    result=CloudWatchAdapter('us-east-1',client=Incomplete()).collect(['fixture'],[])
    assert result['observed_metric_count']==0
    assert {e.get('code') for e in result['errors']} >= {'IncompleteMetricResponse','MismatchedMetricLengths'}

def test_aws_permission_error_is_not_healthy():
    from aws.cloudwatch_adapter import CloudWatchAdapter
    from botocore.exceptions import ClientError
    class Denied:
        def get_metric_data(self,**kwargs):
            raise ClientError({'Error':{'Code':'AccessDenied','Message':'fixture'}},'GetMetricData')
    result=CloudWatchAdapter('us-east-1',client=Denied()).collect(['fixture'],[])
    assert result['errors'] and result['observed_metric_count']==0

def test_followup_needs_three_strictly_new_points():
    from analysis.evidence import assess_followup
    evidence=[{'node':'n','metric':'latency_ms','robust_z':10,'reference_median':10,'reference_mad':0,'scale':1}]
    old={'n':{'latency_ms':[{'timestamp_ms':5,'value':100}]}}
    assert assess_followup(evidence,old,old)[0]['status']=='no_new_observations'
    new={'n':{'latency_ms':[{'timestamp_ms':i,'value':10} for i in (6,7,8)]}}
    assert assess_followup(evidence,old,new)[0]['status']=='returned_toward_reference'
