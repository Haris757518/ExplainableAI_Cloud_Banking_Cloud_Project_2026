"""Verify the running dashboard against real trace and AWS data; no fixtures."""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import httpx


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',default='http://127.0.0.1:8000')
    parser.add_argument('--out',default='results/observed/live_validation.json')
    args=parser.parse_args()
    with httpx.Client(base_url=args.url,timeout=90) as client:
        def get(path):
            r=client.get(path);r.raise_for_status();return r.json()
        def post(path):
            r=client.post(path);r.raise_for_status();return r.json()
        assert client.get('/').status_code==200
        health=get('/api/health')
        assert health['simulation_enabled'] is False
        assert client.post('/api/simulate').status_code==403
        assert client.post('/api/research/refine').status_code==403
        alibaba=post('/api/alibaba/analyze')
        assert alibaba['graph']['metadata']['measured_calls']>0
        assert alibaba['assessment']['gnn_used'] is True
        assert alibaba['assessment']['gnn_evidence']['latest_window_held_out'] is True
        assert alibaba['counterfactual'] is None
        aws=post('/api/aws/analyze?lookback_minutes=60')
        assert aws['source']=='aws_cloudwatch' and aws['aws_collection']['observed_metric_count']>0
        assert aws['assessment']['gnn_used'] is False
        assert aws['transaction']['type']=='OBSERVABILITY_PROBE'
        ids=[r['id'] for r in aws['aws_discovery']['ec2']]
        if len(ids)!=1:
            raise RuntimeError('Choose an explicit EC2 instance for the database verification.')
        database=post('/api/aws/database/diagnostics?instance_id='+ids[0])
        assert database['status']=='observed'
        local=get('/api/diagnostics/database')
        assert local['analytics_store']['connected']
        graph=get('/api/graph/'+str(aws['run_id']))
        assert any(n['type']=='database' for n in graph['nodes'])
        report={'observed_at':datetime.now(timezone.utc).isoformat(),'verification_source':'real HTTP endpoints and live AWS observations',
                'dashboard_http_ok':True,'simulation_disabled':True,
                'alibaba':{'run_id':alibaba['run_id'],'rows_scanned':alibaba['graph']['metadata']['rows_scanned'],
                    'measured_calls':alibaba['graph']['metadata']['measured_calls'],'status':alibaba['assessment']['status'],
                    'gnn_evidence':alibaba['assessment']['gnn_evidence'],'ground_truth_available':False},
                'aws':{'run_id':aws['run_id'],'resources':aws['aws_discovery']['counts'],'metric_count':aws['aws_collection']['observed_metric_count'],
                    'status':aws['assessment']['status'],'eligible_series':aws['assessment']['eligible_metric_series'],
                    'measurement_gaps':aws['assessment']['measurement_gaps'],'evidence':aws['assessment']['evidence'],
                    'probe_values':[t for t in aws['graph']['telemetry'] if '@' in t['node_id']],
                    'source':'aws_cloudwatch','workload':'measured lab SELECT 1 probes; not production banking transactions'},
                'postgresql':database,'analytics_store':local['analytics_store'],
                'synthetic_observations_used':False,'causal_fault_confirmed':False,'supervised_accuracy':None}
        out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2),encoding='utf-8')
        print(json.dumps({'saved':str(out.resolve()),'alibaba_gnn_heldout_mse':alibaba['assessment']['gnn_evidence']['latest_masked_mse'],
                          'aws_metric_count':report['aws']['metric_count'],'aws_status':report['aws']['status'],
                          'aws_eligible_series':report['aws']['eligible_series'],'postgres_blocked_sessions':database['observation']['blocked_sessions'],
                          'probe_values':report['aws']['probe_values'],'analytics_query_ms':local['analytics_store']['dashboard_query_ms']},indent=2))


if __name__=='__main__':
    main()
