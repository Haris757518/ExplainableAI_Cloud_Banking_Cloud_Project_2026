"""Readable label-blind investigations; no cloud mutations or fault injection."""
from pathlib import Path
import hashlib,json
from datetime import datetime,timezone
from typing import Literal
from fastapi import APIRouter,HTTPException
from pydantic import BaseModel,Field
from dataset.real_banking.store import ROOT,read_json,write_json
from dataset.re2 import entries,load_re2
from analysis.re2_log_evidence import get_re2_log_evidence
from analysis.incident_engine import analyze_case
from analysis.probe_xai import investigate
from ai_models.re2_inference import infer,checkpoint_path
from analysis.banking_replay import run_replay
from analysis.banking_followup import attach_followups,verified_corrective_code,verified_final_study,readable_followup_report
from ai_models.re2_detection import calibrated_scores,decide
from fastapi.responses import PlainTextResponse

router=APIRouter(prefix='/api/cloud-investigation',tags=['PROBE-XAI investigations'])
OUT=ROOT/'results/probe_xai'
AWS_STATUS_PATH=ROOT/'results/aws_workload/status.json'
_DETECTION_CACHE={}

@router.post('/banking-replay')
def banking_replay():
    try:return attach_followups(run_replay())
    except (OSError,ValueError,KeyError) as exc:
        raise HTTPException(409,'Banking evidence is missing or failed validation; no findings were assumed.') from exc

@router.get('/banking-report',response_class=PlainTextResponse)
def banking_report():
    return PlainTextResponse(readable_followup_report(banking_replay()),headers={'Content-Disposition':'attachment; filename="banking-investigation-report.md"'})

@router.get('/banking-study')
def banking_study():
    initial=read_json(ROOT/'results/banking_study/v1/report.json',{})
    revision=read_json(ROOT/'results/banking_study/localization-revision.json',{})
    final=verified_final_study() or {}
    return {'initial':{k:initial.get(k) for k in ('status','methods','limitations','recovery_gate_ablation')},
            'development_revision':{'cases':revision.get('cases'),'scores':[{k:r.get(k) for k in ('phase','method','seed','gnn_top1','evidence_localization_top1')} for r in revision.get('scores',[])],'limitations':revision.get('limitations',[])},
            'final':{k:final.get(k) for k in ('status','source','method_summary','submitted_requests','ledger_matches','corrective_code','limitations')},
            'normal_holdout':[r for r in final.get('model_study',{}).get('methods',[]) if r['method']=='graph'],
            'corrective_code':verified_corrective_code(),'detection_calibration':read_json(OUT/'calibrated-detection.json',{})}

def verified_workload():
    status=read_json(AWS_STATUS_PATH,{})
    if status.get('source')!='executed-aws-bank-of-anthos' or status.get('evidence_status')!='verified_transfer':return None
    proof_path=AWS_STATUS_PATH.parent/'first-transfer-verification.json'
    if not proof_path.exists() or hashlib.sha256(proof_path.read_bytes()).hexdigest()!=status.get('proof_sha256'):return None
    proof=read_json(proof_path,{})
    if proof.get('status')!='verified' or not proof.get('history_record_found') or proof.get('ledger_new_records')!=1:return None
    return status

class InvestigationRequest(BaseModel):
    case_id:str
    as_of:float|None=None
    query_budget:int=Field(default=12,ge=0,le=64)
    policy:Literal['progressive','conventional','none']='progressive'
    ranker:Literal['gnn','statistical','identity']='gnn'

@router.get('/overview')
def overview():
    storage=read_json(ROOT/'results/real_banking/deployment.json',{})
    workload=verified_workload()
    result={'title':'Banking Investigation Monitor','monitoring_status':'not_deployed',
        'summary':{'banking_services':None,'active_issues':None,'payment_latency_ms':None,'transaction_success_percent':None},
        'explanation':'No Bank of Anthos workload is deployed or monitored. Unknown values stay unknown.',
        'aws':{'storage':storage.get('status','not_verified'),'region':storage.get('region'),
            'compute':'Read-only EKS and EC2 discovery denied by current IAM permissions.','new_compute_budget_inr':0},
        'issues':[], 'partitions':[{'id':'A','name':'RCAEval RE2','recordings':len(entries()['cases']),'scope':'Independent recorded controlled microservice experiments'},
        {'id':'B','name':'Banking workload','recordings':0,'scope':'No executed Bank of Anthos recording imported; deployment pending'},
        {'id':'C','name':'Published bank reference','scope':'Monzo and Starling aggregate statistics, kept separate from root-cause labels'}],
        'blockers':['Docker and Kubernetes tools unavailable locally.','AWS compute discovery permissions denied.','No new paid compute is approved.']}
    if workload:
        result.update(monitoring_status='recorded_aws_execution',workload=workload,
            explanation=f"A real AWS demo transfer (transaction {workload['transaction_id']}) was verified in the ledger, transaction history and measured frontend-to-ledgerwriter trace. {workload['experiment_status']}",
            summary={'banking_services':workload['pods_ready'],'active_issues':None,
                     'payment_latency_ms':round(workload['payment_roundtrip_ms']),
                     'transaction_success_percent':None,'verified_transfers':workload['verified_transfers']},
            blockers=['Banking findings use measured-signature replay; a banking-domain GNN and independent detection accuracy are not validated.',
                      'Backend server and SQL trace coverage is partial. The balance-cache permanent fix is not implemented.'])
        result['aws'].update(compute='Research instance terminated; checksum-verified evidence retained locally.',new_compute_budget_inr=None,approved_budget_usd=workload['approved_budget_usd'])
        result['partitions'][1].update(recordings=1,scope='Executed AWS Bank of Anthos workload, controlled integrity probe and later recovery checks; read-only local replay available')
        correction=verified_corrective_code()
        if correction and correction['verified']:
            result['corrective_code']=correction
            result['blockers']=['GNN rankings alone do not establish a cause. Revised localization is evaluated separately against direct measurements.',
                                'The implemented reader correction passed repeated AWS tests; broader production capacity and generalization are outside this bounded study.']
    return result

@router.get('/recordings')
def recordings():
    return {'recordings':[{'id':e['id'],'title':f"RE2 recording {i+1:02d}",'source':'RCAEval RE2','environment':'recorded controlled benchmark',
        'has_traces':True,'graph_model_available':checkpoint_path(e['id'],'recorded_graph').exists()} for i,e in enumerate(entries()['cases'])],
        'label_policy':'Source case names and fault labels are withheld during diagnosis.'}

def build(request):
    try:case=load_re2(request.case_id)
    except (FileNotFoundError,ValueError) as exc:raise HTTPException(404,str(exc)) from exc
    start=min(p.timestamp for s in case.series for p in s.observations);end=max(p.timestamp for s in case.series for p in s.observations)
    when=request.as_of if request.as_of is not None else start+.5*(end-start)+120
    if not start<=when<=end:raise HTTPException(422,'Observation time is outside the measured recording')
    incident=analyze_case(case,when,forecast_enabled=False)
    calibration=None
    if (OUT/'calibrated-detection.json').exists():
        key=(case.collection,case.provenance.get('trace_sha256'))
        if key not in _DETECTION_CACHE:_DETECTION_CACHE[key]=calibrated_scores(case)
        calibration=decide(_DETECTION_CACHE[key],when)
        incident.status=calibration['status']
    gnn=infer(case,when,'identity' if request.ranker=='identity' else 'recorded_graph') if request.ranker!='statistical' else None
    result=investigate(case,incident,as_of=when,budget=request.query_budget,policy=request.policy,gnn=gnn)
    prefix=[e for e in case.edges if e.observed_at is None or e.observed_at<=when]
    # Only series for the chosen candidate and the actual measured prefix are returned.
    series=[s for s in case.series if s.resource==result['resource'] and ('latency' in s.metric or s.metric in ('cpu','mem','workload'))]
    result['timeline']=[{'id':s.id,'metric':s.metric,'unit':s.unit,'points':[{'timestamp':p.timestamp,'value':p.value} for p in s.observations if p.timestamp<=when]} for s in series[:4]]
    result['graph']={'nodes':sorted({s.resource for s in case.series}),'edges':[e.model_dump() for e in prefix]}
    result['detection']={'status':incident.status,'affected_services':incident.affected_services,
        'severity':'unclassified','severity_reason':'No validated banking SLO or calibrated operational severity for this external recording.',
        'timestamp':when,'evidence':[e.model_dump() for e in incident.evidence if e.resource==result['resource']]}
    if calibration:result['detection']['calibration']=calibration
    result['ranking']=[c.model_dump() for c in incident.candidates] if not gnn or gnn.get('status')!='evaluated' else gnn['scores']
    from analysis.mechanisms import resource_labels
    result['resource_labels']=resource_labels(result['graph']['nodes'])
    result['resource_label']=result['resource_labels'].get(result['resource'],result['resource'])
    if result['resource'] and result['resource_label']:
        result['summary']=result['summary'].replace(result['resource'],result['resource_label'])
    result['log_evidence']=get_re2_log_evidence(case.id,as_of=when,resource=result['resource'])
    result['recording_id']=case.id
    detector_version='calibrated-re2-prefix-v1' if calibration else 'legacy'
    result['detection']['version']=detector_version
    result['id']=hashlib.sha256(f'{case.collection}:{when}:{request.policy}:{request.ranker}:{request.query_budget}:{detector_version}'.encode()).hexdigest()[:24]
    if result['log_evidence']['status']=='available':
        result['id']=hashlib.sha256((result['id']+':'+result['log_evidence']['sha256']).encode()).hexdigest()[:24]
    return result

@router.post('/investigate')
def run(request:InvestigationRequest):
    result=build(request);write_json(OUT/'investigations'/f"{result['id']}.json",result)
    return result

@router.get('/results')
def results():
    path=OUT/'evaluation_expanded.json'
    return read_json(path if path.exists() else OUT/'evaluation.json',{'status':'not_evaluated','message':'No new PROBE-XAI comparison has completed.'})

@router.get('/history')
def history():
    return {'investigations':[{'id':p.stem,**{k:v for k,v in read_json(p,{}).items() if k in ['recording_id','resource','summary','deepest_supported_level']}} for p in (OUT/'investigations').glob('*.json')]}
