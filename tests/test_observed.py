"""Small test fixtures below are test inputs, never research measurements."""
from datetime import datetime, timezone, timedelta
import json
from pathlib import Path
import pytest
from botocore.stub import Stubber
import boto3
from common.schema import AnalysisSample, TelemetryPoint, GraphNode, TransactionContext
from aws.cloudwatch_adapter import CloudWatchAdapter
from aws.normalizer import build_aws_sample
from analysis.observed import analyze_observed
from dataset.alibaba_adapter import build_snapshot


def test_missing_values_are_unknown():
    sample=build_aws_sample({'ec2':[{'id':'i-observed'}]}, {'ec2':[{'node_id':'i-observed','metrics':{'cpu_percent':25}}]})
    t=sample.telemetry[0]
    assert t.cpu_percent==25 and t.memory_percent is None and t.latency_ms is None
    assert t.observed_metrics==['cpu_percent']
    assert sample.node_labels=={} and sample.transaction.path==[] and sample.edges==[]
    result=analyze_observed(sample)
    assert result.anomaly_score is None and result.is_anomaly is None
    assert result.assessment['status']=='insufficient_evidence'


def test_alibaba_preserves_durations_and_unknowns(tmp_path):
    p=tmp_path/'MSCallGraph.csv'
    p.write_text('timestamp,traceid,rpcid,um,rpctype,dm,rt\n0,T,1,A,db,B,12\n0,T,1,A,db,B,-8\n',encoding='utf-8')
    snapshot=build_snapshot(tmp_path)
    b=next(t for t in snapshot.to_analysis_sample().telemetry if t.node_id=='B')
    assert b.latency_ms==12 and b.db_latency_ms==12
    assert b.cpu_percent is None and b.timestamp is None
    assert snapshot.metadata['series']['B']['server_latency_ms'][0]['value']==8
    assert snapshot.to_analysis_sample().scenario=='UNLABELED'


def test_chronological_evidence_without_intervention():
    series={'B':{'db_latency_ms':[{'timestamp_ms':i*60000,'value':v} for i,v in enumerate([10,11,9,10,10,100])]}}
    sample=AnalysisSample(transaction=TransactionContext(id='observed',type='UPI_PAYMENT'),nodes=[GraphNode(id='B',type='rds',label='B')],edges=[],
                          telemetry=[TelemetryPoint(node_id='B',db_latency_ms=100,observed_metrics=['db_latency_ms'],source='aws_cloudwatch')],
                          scenario='UNLABELED',source='aws_cloudwatch',metadata={'series':series})
    result=analyze_observed(sample)
    assert result.is_anomaly is True and result.root_causes[0].node=='B'
    assert result.counterfactual is None and result.assessment['causal_confirmation'] is False
    assert result.assessment['evidence'][0]['reference_median']==10
    assert result.cfao.refinement['sampling_changed'] is False


def test_cloudwatch_request_shape_and_pagination():
    client=boto3.client('cloudwatch',region_name='ap-south-1',aws_access_key_id='testing',aws_secret_access_key='testing')
    adapter=CloudWatchAdapter('ap-south-1',client=client)
    now=datetime.now(timezone.utc)
    # Botocore validates request structure before Stubber dispatch. This catches
    # the old ReturnData-inside-MetricStat defect that permissive fake clients missed.
    with Stubber(client) as stub:
        stub.add_response('get_metric_data',{'MetricDataResults':[{'Id':'m0','Timestamps':[now-timedelta(minutes=1)],'Values':[10.], 'StatusCode':'PartialData'}],'NextToken':'page2'})
        stub.add_response('get_metric_data',{'MetricDataResults':[{'Id':'m0','Timestamps':[now],'Values':[20.], 'StatusCode':'Complete'}]})
        result=adapter.collect(['i-1'],[])
    assert result['api_calls']==2
    assert result['observed_metric_count']==1
    assert result['ec2'][0]['metrics']['cpu_percent']==20
    assert len(result['ec2'][0]['series'][0]['points'])==2


def test_no_fallback_topology():
    sample=build_aws_sample({'ec2':[{'id':'i-1'}],'rds':[{'id':'db-1'}]}, {'ec2':[],'rds':[]})
    assert sample.edges==[] and sample.transaction.path==[]
    assert all(n.id!='payment-service' for n in sample.nodes)


def test_measured_probe_has_explicit_lab_context_and_separate_db_timing():
    ts='2026-10-16T06:00:00+00:00'
    app={'node_id':'i-1','metrics':{'latency_ms':8.,'db_query_ms':2.,'db_connection_ms':3.},'observed_metrics':['latency_ms','db_query_ms','db_connection_ms'],
         'series':[{'target':key,'timestamp':ts,'points':[{'timestamp':ts,'value':value}]} for key,value in [('latency_ms',8.),('db_query_ms',2.),('db_connection_ms',3.)]]}
    sample=build_aws_sample({'ec2':[{'id':'i-1'}]}, {'timestamp':ts,'ec2':[],'rds':[],'application':[app]})
    assert sample.transaction.type=='OBSERVABILITY_PROBE'
    assert sample.metadata['banking_data'] is False
    assert next(t for t in sample.telemetry if t.node_id=='postgres@i-1').db_latency_ms==2.
    assert next(t for t in sample.telemetry if t.node_id=='observed-probe@i-1').latency_ms==8.
    assert any(e.relationship=='MEASURED_DB_CALL' for e in sample.edges)


def test_ssm_postgres_uses_fixed_read_only_query():
    from aws.ssm_postgres import collect_postgres
    class Client:
        def send_command(self, **kwargs):
            command=kwargs['Parameters']['commands'][0]
            assert 'BEGIN READ ONLY' in command and 'statement_timeout' in command
            assert 'pg_stat_activity' in command
            assert 'SELECT query' not in command
            return {'Command':{'CommandId':'test'}}
        def get_command_invocation(self, **kwargs):
            return {'Status':'Success','StandardOutputContent':'BEGIN\n{"blocked_sessions": 0, "activity": [], "database_counters": [\n{"datname":"postgres"},\n{"datname":"xai_observability"}]}\nROLLBACK'}
    result=collect_postgres('i-1','us-east-1',client=Client())
    assert result['status']=='observed' and result['source']=='aws_ssm_postgresql'
    assert result['causal_confirmation'] is False
    assert len(result['observation']['database_counters'])==2


def test_gnn_does_not_transfer_alibaba_weights_to_aws():
    from ai_models.observed_gnn import explain_observed_checkpoint
    sample=build_aws_sample({'ec2':[{'id':'i-1'}]}, {'ec2':[],'rds':[]})
    result=explain_observed_checkpoint(sample)
    assert result['status']=='not_applied' and 'source/domain' in result['reason']
