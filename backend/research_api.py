"""Integrated, bounded replay and incident history APIs. No cloud mutations."""
import json,math
from pathlib import Path
from datetime import datetime,timezone
from fastapi import APIRouter,HTTPException,Query,Depends
from sqlalchemy import Column,String,Text,DateTime
from sqlalchemy.orm import Session
from database.db import Base,get_db
from dataset.benchmarks import catalog,load_case,manifest,labels_for_evaluation
from analysis.incident_engine import analyze_case,capabilities

router=APIRouter(prefix='/api/research',tags=['evidence-gated research'])
class ResearchIncident(Base):
    __tablename__='research_incidents'
    id=Column(String,primary_key=True)
    case_id=Column(String,index=True,nullable=False)
    source=Column(String,index=True,nullable=False)
    payload=Column(Text,nullable=False)
    created_at=Column(DateTime(timezone=True),default=lambda:datetime.now(timezone.utc),index=True)

def read_case(case_id):
    try:return load_case(case_id)
    except FileNotFoundError as exc:raise HTTPException(404,str(exc)) from exc
    except (ValueError,OSError) as exc:raise HTTPException(424,str(exc)) from exc

@router.get('/sources')
def sources():
    rows=catalog()
    return {'sources':[{'id':source,'imported_cases':sum(r['source']==source for r in rows),'kind':'expert-labelled series' if source=='microsoft' else 'recorded controlled benchmark','graph':'RE1 unavailable; RE2 recorded parent-child traces where imported' if source=='rcaeval' else 'unavailable'} for source in ('microsoft','rcaeval')],'controlled_lab':{'enabled':False,'reason':'Archived prototype; no faults or AWS changes are authorized by this implementation request.'},'official_title':'Explainable AI-Based Cloud Performance Analytics for Digital Banking using Graph Neural Networks'}

@router.get('/catalog')
def case_catalog(source:str|None=None):
    rows=catalog()
    return {'cases':[r for r in rows if source is None or r['source']==source]}

@router.get('/capabilities')
def capability_registry(case_id:str|None=None):
    case=read_case(case_id) if case_id else None
    return {'capabilities':capabilities([s.metric for s in case.series] if case else [],bool(case.edges) if case else False),'note':'Support depends on observed columns, units and topology. A supported deviation mechanic is not verified mechanism classification.'}

@router.get('/case-info/{case_id}')
def case_info(case_id:str):
    case=read_case(case_id)
    return {'case_id':case_id,'source':case.source.model_dump(),'start':min(p.timestamp for s in case.series for p in s.observations),'end':max(p.timestamp for s in case.series for p in s.observations),'metric_count':len(case.series),'resources':len({s.resource for s in case.series}),'label_policy':'Only recording bounds are exposed here; future telemetry and labels are not inference inputs.'}

def frame(case_id,as_of,metric_id=None,forecast=True):
    case=read_case(case_id)
    start=min((p.timestamp for s in case.series for p in s.observations),default=None)
    end=max((p.timestamp for s in case.series for p in s.observations),default=None)
    if start is None:raise HTTPException(424,'No observations in imported case')
    cutoff=end if as_of is None else as_of
    if not math.isfinite(cutoff) or cutoff<start or cutoff>end:raise HTTPException(422,'Replay time is outside the recorded interval')
    incident=analyze_case(case,cutoff,forecast_enabled=forecast)
    wanted=[s for s in case.series if s.id==metric_id] if metric_id else sorted(case.series,key=lambda s:next((e.score for e in incident.evidence if e.resource==s.resource and e.metric==s.metric),0),reverse=True)[:4]
    if metric_id and forecast and not any(f.series_id==metric_id for f in incident.forecasts):
        from analysis.forecasting import forecast_next
        selected=next((s for s in case.series if s.id==metric_id),None)
        if selected:
            observed=selected.model_copy(update={'observations':[p for p in selected.observations if p.timestamp<=cutoff]})
            incident.forecasts=[forecast_next(observed)]+incident.forecasts[:3]
    histories=[]
    for series in wanted:
        points=[p for p in series.observations if p.timestamp<=cutoff]
        histories.append({**series.model_dump(exclude={'observations'}),'observations':[p.model_dump() for p in points[-1200:]],'earlier_points_omitted_from_chart':max(0,len(points)-1200)})
    return {'case_id':case_id,'start':start,'end':end,'as_of':cutoff,'incident':incident.model_dump(),'histories':histories,'available_series':[{'id':s.id,'metric':s.metric,'resource':s.resource} for s in case.series],'label_policy':'Fault and point labels are excluded from inference. Ground truth is scored only through the separate completed-case scoring endpoint.'}

@router.get('/replay/{case_id}')
def replay(case_id:str,as_of:float|None=None,metric_id:str|None=None):
    return frame(case_id,as_of,metric_id)

@router.post('/incidents/{case_id}')
def save_incident(case_id:str,as_of:float|None=None,db:Session=Depends(get_db)):
    result=frame(case_id,as_of);incident=result['incident']
    previous=db.query(ResearchIncident).filter(ResearchIncident.case_id==case_id).order_by(ResearchIncident.created_at.desc()).first()
    if previous:
        prior=json.loads(previous.payload);before=prior['incident']
        if incident['observation_time']>before['observation_time'] and before['status']=='deviation_detected':
            current=read_case(case_id);followup=[]
            frozen_threshold=before.get('explanation',{}).get('detector_threshold',3.5)
            for e in before['evidence']:
                if e['score']<frozen_threshold:continue
                for s in current.series:
                    if s.resource!=e['resource'] or s.metric!=e['metric']:continue
                    new=[p for p in s.observations if before['observation_time']<p.timestamp<=incident['observation_time'] and p.value is not None]
                    normal=[abs(p.value-e['reference'])/e['scale']<frozen_threshold for p in new[-3:]]
                    followup.append({'resource':e['resource'],'metric':e['metric'],'new_points':len(new),'status':'returned_toward_original_reference' if len(normal)==3 and all(normal) else 'persists_or_insufficient_new_points'})
            incident['recovery']={'status':'observed_followup','comparisons':followup,'causal_recovery_verified':False}
    existing=db.get(ResearchIncident,incident['id'])
    if existing is None:
        db.add(ResearchIncident(id=incident['id'],case_id=case_id,source=incident['source']['id'],payload=json.dumps(result,allow_nan=False)))
        try:db.commit()
        except Exception:
            db.rollback()
            # Concurrent identical saves preserve the first immutable snapshot.
            existing=db.get(ResearchIncident,incident['id'])
            if existing is None:raise
            return json.loads(existing.payload)
    return result

@router.get('/incidents')
def history(db:Session=Depends(get_db)):
    rows=db.query(ResearchIncident).order_by(ResearchIncident.created_at.desc()).limit(50).all()
    return {'incidents':[{'id':r.id,'case_id':r.case_id,'source':r.source,'created_at':r.created_at.isoformat(),'status':json.loads(r.payload)['incident']['status']} for r in rows]}

@router.get('/incidents/detail/{incident_id}')
def detail(incident_id:str,db:Session=Depends(get_db)):
    row=db.get(ResearchIncident,incident_id)
    if row is None:raise HTTPException(404,'Recorded investigation not found')
    return json.loads(row.payload)

@router.post('/score/{case_id}')
def score_case(case_id:str):
    case=read_case(case_id)
    start=min(p.timestamp for s in case.series for p in s.observations);end=max(p.timestamp for s in case.series for p in s.observations)
    checkpoint=min(end,start+(end-start)/2+120) if case.source.id=='rcaeval' else end
    result=frame(case_id,checkpoint,forecast=False)
    # Prediction is completed before the independently stored truth is read.
    try:truth=labels_for_evaluation(case_id)
    except (ValueError,OSError,StopIteration) as exc:raise HTTPException(424,'Original benchmark annotations are unavailable or inconsistent') from exc
    if 'root_cause_service' not in truth:return {'status':'point_labels_require_chronological_evaluation','label_source':truth['label_source'],'command':'scripts/run_benchmark_research.py --dataset microsoft --out NEW_DIRECTORY'}
    order=[c['resource'] for c in result['incident']['candidates']]
    rank=order.index(truth['root_cause_service'])+1 if truth['root_cause_service'] in order else None
    return {'prediction_timestamp':result['as_of'],'prediction_kind':'Predeclared recording midpoint+120-second checkpoint, identical to the benchmark protocol; no later telemetry used.','ground_truth':truth,'rank':rank,'top1':rank==1,'top3':rank is not None and rank<=3,'mrr':1/rank if rank else 0,'prediction':order}

@router.get('/results')
def results():
    root=Path(__file__).resolve().parents[1]/'results/research_v3'
    complete=sorted(root.glob('*/run.json'),key=lambda p:p.stat().st_mtime) if root.exists() else []
    if not complete:return {'status':'not_evaluated','results':{}}
    folder=complete[-1].parent
    values={p.stem:json.loads(p.read_text(encoding='utf-8')) for p in folder.glob('*.json')}
    graph=root/'graph_ablation_train_topology/report.json'
    if not graph.exists():graph=root/'graph_ablation/report.json'
    if graph.exists():values['graph_ablation']=json.loads(graph.read_text(encoding='utf-8'))
    updated=Path(__file__).resolve().parents[1]/'results/redesign_20261022/graph/report.json'
    if updated.exists():values['graph_ablation']=json.loads(updated.read_text(encoding='utf-8'))
    followups=sorted(root.glob('investigation_*.json'))
    if followups:values['investigation']=json.loads(followups[-1].read_text(encoding='utf-8'))
    mechanism_report=Path(__file__).resolve().parents[1]/'results/research_v4/mechanisms_20261016/report.json'
    if mechanism_report.exists():values['mechanisms']=json.loads(mechanism_report.read_text(encoding='utf-8'))
    re2_report=Path(__file__).resolve().parents[1]/'results/research_v4/re2_graph_20261016_02/report.json'
    if re2_report.exists():values['re2_graph']=json.loads(re2_report.read_text(encoding='utf-8'))
    return {'status':'evaluated','version':folder.name,'results':values}

@router.get('/models')
def models():
    root=Path(__file__).resolve().parents[1]
    paths=['results/observed/observed_gnn.json','results/research_v3/graph_ablation/report.json','results/research_v3/graph_ablation_train_topology/report.json','results/research_v3/forecast_models_20261016.json','results/research_v4/mechanisms_20261016/model.json','results/research_v4/re2_graph_20261016_02/report.json']
    return {'models':[json.loads((root/p).read_text()) for p in paths if (root/p).exists()],'domains':'Alibaba measured GNN restricted to supported trace digest; Microsoft and RCAEval use independently evaluated statistical/forecast methods.'}

@router.get('/demo')
def demo_cases():
    # Instructional curation by published category; never passed to inference.
    rows=[r for r in catalog() if r['source']=='rcaeval']
    selected=[]
    for fault,title in [('cpu','CPU signature investigation'),('mem','Memory signature investigation'),('disk','Disk annotation with limited measurements'),('delay','Delay annotation: distinguish symptom from mechanism'),('loss','Network loss annotation: missing direct measurements')]:
        candidates=[r for r in rows if '_'+fault+'_' in r['display_name']]
        if candidates:
            row=sorted(candidates,key=lambda r:r['id'])[0]
            selected.append({'id':row['id'],'source':'rcaeval','title':title,'selection':'Curated by published category, not prediction correctness; not an aggregate accuracy sample.'})
    graph_rows=[r for r in rows if r['split']=='illustrative_re2_graph']
    if graph_rows:selected.append({'id':graph_rows[0]['id'],'source':'rcaeval','title':'Recorded trace dependencies (RE2)','selection':'Bounded illustrative graph case; no aggregate claim.'})
    ms=[r for r in catalog() if r['source']=='microsoft']
    if ms:selected.append({'id':ms[0]['id'],'source':'microsoft','title':'Labelled anomaly: no mechanism annotation'})
    return {'cases':selected,'graph_demo':'Select Alibaba and Analyze observed data for genuine recorded dependencies; no labelled cause exists for that slice.'}

@router.post('/verify/{case_id}')
def verify_completed(case_id:str,as_of:float=Query(...)):
    case=read_case(case_id)
    end=max(p.timestamp for s in case.series for p in s.observations)
    if not math.isfinite(as_of) or as_of<end:raise HTTPException(409,'Complete recorded replay before revealing annotations.')
    if as_of>end:raise HTTPException(422,'Replay time exceeds recording.')
    result=score_case(case_id)
    if 'ground_truth' not in result:return result
    start=min(p.timestamp for s in case.series for p in s.observations)
    incident=analyze_case(case,min(end,start+(end-start)/2+120),forecast_enabled=False)
    mechanism=incident.explanation['diagnosis']['mechanism']
    predicted={'cpu_pressure':'cpu','memory_pressure':'mem','disk_degradation':'disk','network_delay':'delay','packet_loss':'loss'}.get(mechanism,'unknown')
    return {**result,'mechanism_prediction':mechanism,'mechanism_match':predicted==result['ground_truth']['fault'],'mechanism_verified':False,'annotation_interpretation':'Published controlled injection category; not independently established real-world causality.'}
