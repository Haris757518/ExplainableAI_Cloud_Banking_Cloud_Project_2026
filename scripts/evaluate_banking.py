"""Predeclared repeated local delay study; explicit fault trigger, immutable output."""
from pathlib import Path
import sys,json,time,argparse,statistics,hashlib
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import httpx
from banking import store

def main():
    p=argparse.ArgumentParser();p.add_argument('--confirm-local-test',action='store_true');p.add_argument('--repetitions',type=int,default=3);p.add_argument('--out',required=True);args=p.parse_args()
    if not args.confirm_local_test:p.error('Explicit --confirm-local-test required. This runs bounded local service delays.')
    if not 1<=args.repetitions<=5:p.error('Choose 1–5 repetitions.')
    out=Path(args.out)
    if out.exists():raise SystemExit('Preserve previous results; choose a new output directory.')
    cal=store.calibration()
    if not cal:raise SystemExit('Collect a normal banking baseline first.')
    results=[]
    with httpx.Client(base_url='http://127.0.0.1:8000/api/banking',timeout=60,trust_env=False) as client:
        for index in range(args.repetitions):
            response=client.post('/experiments/application-delay',json={'confirm_local_test':True,'duration_seconds':12,'delay_ms':150});response.raise_for_status();identifier=response.json()['job_id']
            deadline=time.monotonic()+120
            while time.monotonic()<deadline:
                job=next(j for j in store.rows('SELECT * FROM jobs',name='controls.db') if j['id']==identifier)
                if job['status'] not in ('running','stopping'):break
                time.sleep(.5)
            if job['status']!='completed':raise RuntimeError(f'Local measured repetition failed: {job}')
            response=client.get('/verify/'+identifier);response.raise_for_status();verified=response.json()
            label=verified['published_control'];fault=[r for r in store.request_rows('transfer') if label['started']<=r['ts']<=label['expires']]
            baseline=[r for r in store.request_rows('transfer') if r['trace_id'] in cal['train_trace_ids']]
            verified['measured_requests_during_condition']=len(fault)
            verified['normal_median_handler_ms']=statistics.median(r['duration_ms'] for r in baseline)
            verified['condition_median_handler_ms']=statistics.median(r['duration_ms'] for r in fault) if fault else None
            results.append(verified);print('Measured repetition',index+1,'service_match',verified['service_match'],'mechanism_match',verified['mechanism_match'],flush=True)
    out.mkdir(parents=True)
    model=json.loads((store.root()/'graph-report.json').read_text())
    graph={}
    for name in ('identity','graph'):
        predictions=[r['graph_evidence']['models'][name]['ranking'] for r in results if r.get('graph_evidence',{}).get('status')=='evaluated']
        graph[name]={'compatible_cases':len(predictions),'root_service_top1':sum(order[0]=='ledger-service' for order in predictions)/len(predictions) if predictions else None,'root_service_top3':sum('ledger-service' in order[:3] for order in predictions)/len(predictions) if predictions else None}
    report={'official_title':'Explainable AI-Based Cloud Performance Analytics for Digital Banking using Graph Neural Networks','environment':'Three local FastAPI processes, actual HTTP/SQL spans, dedicated SQLite test database; no cloud deployment or real payments','protocol':{'baseline_id':cal['id'],'normal_requests':len(cal['trace_ids']),'seed':42,'concurrency':1,'repetitions':args.repetitions,'condition_seconds':12,'delay_ms':150,'diagnosis_checkpoint':'Tenth completed transfer request during each explicitly triggered condition; independent labels read afterwards','recovery':'15 actual transfer requests after cleanup; final three values against the original frozen reference','normal_split':'60/20/20 chronological; threshold chosen on validation only'},'normal_holdout':cal['normal_heldout'],'summary':{'controlled_cases':len(results),'detected_cases':sum(r['detection_status']=='deviation_detected' for r in results),'service_top3':sum(r['service_top3_match'] for r in results)/len(results),'service_top1':sum(r['service_match'] for r in results)/len(results),'mechanism_accuracy':sum(r['mechanism_match'] for r in results)/len(results),'joint_service_mechanism_accuracy':sum(r['service_match'] and r['mechanism_match'] for r in results)/len(results),'abstention_rate':sum(r['abstained'] for r in results)/len(results),'measured_return_to_reference_cases':sum(r['recovery']['status']=='returned_toward_frozen_reference' for r in results)},'banking_gnn_normal_comparison':model,'banking_gnn_controlled_localization':graph,'tc_cfao':{'broad_fields':[r['tc_cfao']['broad_metric_fields'] for r in results],'focused_fields':[r['tc_cfao']['focused_metric_fields'] for r in results],'broad_resources':[r['tc_cfao']['broad_resource_count'] for r in results],'focused_resources':[len(r['tc_cfao']['examined_resources']) for r in results],'external_calls':0,'AWS_cost_savings':None,'scope':'Marginal inspection of existing recorded fields after broad detection; not total collection savings.'},'cases':results,'blocked':{'postgres_lock_contention':'No verified dedicated PostgreSQL installation/privileges; not run. SQLite waits are not presented as PostgreSQL locks.'},'limitations':['One machine, one injected mechanism, sequential workload, small repeated sample; not production banking accuracy.','Deliberate bounded sleep measures application delay, not an organic bug or CPU saturation.','Normal calibration and GNN evaluation use one small local normal recording; no cross-machine generalization.','Graph residual rankings are evaluated separately and not fused into the main diagnosis without validated benefit.','Existing published dataset results remain independent and unchanged.','GNN Top-3 includes all three resources and is therefore trivial in this small topology.','Timing instrumentation has measured overhead; request handler time is not complete client/network latency.']}
    (out/'report.json').write_text(json.dumps(report,indent=2,allow_nan=False),encoding='utf-8',newline='\n')
    # Explicit pointer selects the frozen final report; no older report is overwritten.
    pointer=Path('results/banking/FINAL.json')
    if pointer.exists():
        print('New report saved. Existing frozen FINAL selection preserved.')
        print(json.dumps(report['summary']));return
    pointer.parent.mkdir(exist_ok=True);pointer.write_text(json.dumps({'report':str(out/'report.json').replace('\\','/'),'sha256':hashlib.sha256((out/'report.json').read_bytes()).hexdigest()},indent=2),encoding='utf-8')
    print(json.dumps(report['summary']))
if __name__=='__main__':main()
