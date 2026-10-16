from __future__ import annotations
import json
import time
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from contextlib import asynccontextmanager
from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from common.config import get_settings
from common.schema import AnalysisSample
from database.db import init_db, get_db
from database.models import AnalysisRun
from dataset.generator import generate_sample, generate_sequence
from backend.services.pipeline import AnalysisPipeline
from analysis.temporal import analyze_temporal_window
from aws.cloudwatch_adapter import CloudWatchAdapter
from aws.discovery import AWSDiscovery, AWSDiscoveryError
from aws.mapping import load_mapping
from aws.normalizer import build_aws_sample
from dataset.alibaba_adapter import build_snapshot

settings=get_settings()
@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db(); yield

app=FastAPI(title="Explainable AI-Based Cloud Performance Analytics for Digital Banking using Graph Neural Networks",version="1.0.0",lifespan=lifespan)
app.add_middleware(CORSMiddleware,allow_origins=[settings.frontend_origin,"http://127.0.0.1:5173","http://localhost:5173"],allow_credentials=True,allow_methods=["*"],allow_headers=["*"])
pipeline=AnalysisPipeline()
init_db()

def persist(result, db: Session):
    root=result.root_causes[0].node if result.root_causes else "none"
    row=AnalysisRun(transaction_id=result.transaction.id,scenario=result.scenario,anomaly_score=result.anomaly_score,is_anomaly=result.is_anomaly,root_cause=root,source=result.source,payload=result.model_dump_json())
    try:
        db.add(row); db.commit(); db.refresh(row); return row.id
    except Exception:
        db.rollback()
        raise

@app.get("/api/health")
def health():
    return {"status":"ok","aws_mode":settings.aws_mode,"model_loaded":Path("results/observed/observed_gnn.pt").exists(),"simulation_enabled":settings.enable_simulation,"observed_method":"chronological median/MAD holdout","synthetic_gnn_excluded_from_observed_inference":True,"model_version":"observed-median-mad-v2; Alibaba-only measured graph autoencoder","aws_region":settings.aws_region}

@app.get("/api/config")
def config():
    return {"simulation_enabled":settings.enable_simulation,"aws_mode":settings.aws_mode,"region":settings.aws_region,"model_version":"observed-median-mad-v2; Alibaba-only measured graph autoencoder","scenarios":["NORMAL","CPU_SPIKE","DATABASE_LATENCY","SERVICE_OVERLOAD","NETWORK_DEGRADATION","CASCADING_FAILURE"],"transaction_types":["UPI_PAYMENT","FUND_TRANSFER","CARD_PAYMENT","BALANCE_INQUIRY","BILL_PAYMENT"]}

@app.get("/api/dashboard")
def dashboard(db: Session=Depends(get_db)):
    rows=db.query(AnalysisRun).order_by(AnalysisRun.created_at.desc()).limit(20).all()
    return {"project":"Explainable AI-Based Cloud Performance Analytics for Digital Banking using Graph Neural Networks","aws_mode":settings.aws_mode,"recent_runs":[{"id":r.id,"transaction_id":r.transaction_id,"scenario":r.scenario,"anomaly_score":r.anomaly_score,"is_anomaly":r.is_anomaly,"root_cause":r.root_cause,"source":r.source,"created_at":r.created_at.isoformat()} for r in rows]}

@app.get("/api/anomalies")
def anomalies(db: Session=Depends(get_db)):
    rows=db.query(AnalysisRun).filter(AnalysisRun.is_anomaly==True).order_by(AnalysisRun.created_at.desc()).limit(50).all()
    return [{"id":r.id,"scenario":r.scenario,"score":r.anomaly_score,"root_cause":r.root_cause,"source":r.source,"created_at":r.created_at.isoformat()} for r in rows]

@app.post("/api/analyze")
def analyze(sample: AnalysisSample, db: Session=Depends(get_db)):
    if sample.source in {'simulation', 'adaptive_high_resolution'} and not settings.enable_simulation:
        raise HTTPException(403, 'Synthetic analysis is disabled.')
    try:
        result=pipeline.analyze(sample,source=sample.source)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    run_id=persist(result,db)
    payload=result.model_dump(mode="json"); payload["run_id"]=run_id; return payload

@app.post("/api/simulate")
def simulate(scenario: str="DATABASE_LATENCY",seed: int=42,tx_type: str="UPI_PAYMENT",db: Session=Depends(get_db)):
    if not settings.enable_simulation:
        raise HTTPException(403, "Synthetic simulation is disabled. Use Alibaba or AWS.")
    if tx_type == "ALIBABA_BENCHMARK":
        raise HTTPException(status_code=400, detail="ALIBABA_BENCHMARK is unsupported here. Use /api/alibaba/analyze.")
    try: sample=generate_sample(scenario,seed=seed,index=0,tx_type=tx_type)
    except ValueError as exc: raise HTTPException(status_code=400,detail=str(exc))
    result=pipeline.analyze(sample,source="simulation"); run_id=persist(result,db)
    payload=result.model_dump(mode="json"); payload["run_id"]=run_id; return payload

@app.post("/api/alibaba/analyze")
def analyze_alibaba(db: Session=Depends(get_db)):
    started = time.perf_counter()
    try:
        snapshot = build_snapshot(settings.alibaba_root, max_services=40, max_edges=80, max_rows=settings.alibaba_max_rows, window_ms=5000)
    except FileNotFoundError as exc:
        raise HTTPException(424, str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from exc
    sample = snapshot.to_analysis_sample()
    sample.source = "alibaba"
    sample.metadata["import_duration_ms"] = round((time.perf_counter()-started)*1000, 2)
    sample.transaction.type = "ALIBABA_BENCHMARK"
    result = pipeline.analyze(sample, source="alibaba")
    run_id = persist(result, db)
    payload = result.model_dump(mode="json")
    payload["run_id"] = run_id
    return payload

@app.post("/api/research/refine")
def refine(scenario: str="DATABASE_LATENCY",seed: int=42,tx_type: str="UPI_PAYMENT"):
    if not settings.enable_simulation:
        raise HTTPException(403, "Synthetic refinement is disabled.")
    sample=generate_sample(scenario,seed=seed,index=0,tx_type=tx_type)
    return pipeline.run_adaptive_refinement(sample)

@app.post("/api/research/temporal")
def temporal(scenario: str="DATABASE_LATENCY",seed: int=42,tx_type: str="UPI_PAYMENT"):
    if not settings.enable_simulation:
        raise HTTPException(403, "Synthetic temporal generation is disabled.")
    samples=generate_sequence(scenario,steps=8,seed=seed,anomaly_start=3,tx_type=tx_type,topology_change=True)
    return analyze_temporal_window(pipeline.engine,samples)

@app.get("/api/graph/{run_id}")
def graph(run_id:int,db:Session=Depends(get_db)):
    row=db.get(AnalysisRun,run_id)
    if not row: raise HTTPException(status_code=404,detail="analysis not found")
    payload=json.loads(row.payload)
    return {"nodes":payload["graph"]["nodes"],"edges":payload["graph"]["edges"],"transaction":payload["transaction"],"affected_nodes":payload["affected_nodes"]}

@app.get("/api/rca/{run_id}")
def rca(run_id:int,db:Session=Depends(get_db)):
    row=db.get(AnalysisRun,run_id)
    if not row: raise HTTPException(status_code=404,detail="analysis not found")
    payload=json.loads(row.payload); return {"root_causes":payload["root_causes"],"explanation":payload["explanation"],"counterfactual":payload.get("counterfactual")}

@app.get("/api/cfao/{run_id}")
def cfao(run_id:int,db:Session=Depends(get_db)):
    row=db.get(AnalysisRun,run_id)
    if not row: raise HTTPException(status_code=404,detail="analysis not found")
    return json.loads(row.payload)["cfao"]

def _permitted_aws(raw):
    # Conservative source quarantine: the prior authorized controlled trials ended
    # at 08:03:34 UTC. Exclude all points through 08:05 including aggregation margin.
    from datetime import datetime
    cutoff = datetime.fromisoformat('2026-10-16T08:05:00+00:00')
    for group in ('ec2','rds','application'):
        for item in raw.get(group,[]):
            item['metrics']={}; item['observed_metrics']=[]
            retained=[]
            for series in item.get('series',[]):
                points=[p for p in series['points'] if datetime.fromisoformat(p['timestamp']) > cutoff]
                if not points: continue
                series={**series,'points':points,'timestamp':points[-1]['timestamp'],'value':points[-1]['value']}
                retained.append(series); item['metrics'][series['target']]=series['value']; item['observed_metrics'].append(series['target'])
            item['series']=retained
    raw['observed_metric_count']=sum(len(x['observed_metrics']) for g in ('ec2','rds','application') for x in raw.get(g,[]))
    raw['exclusion_policy']={'not_before':'2026-10-16T08:05:00+00:00','reason':'Conservative exclusion of earlier controlled-trial period and aggregation margin; no trial results are research evidence.'}
    return raw

def _aws_discovery() -> dict:
    status = AWSDiscovery(settings.aws_region, settings.profile).status()
    if not status["connected"]:
        raise HTTPException(status_code=503, detail={"message":"AWS credentials are unavailable or invalid.","aws":status})
    try:
        discovery = AWSDiscovery(settings.aws_region, settings.profile).discover()
    except AWSDiscoveryError as exc:
        raise HTTPException(status_code=502, detail=str(exc))
    # Optional explicit IDs narrow discovery without inventing resources.
    if settings.ec2_ids:
        discovery["ec2"] = [x for x in discovery["ec2"] if x.get("id") in set(settings.ec2_ids)]
    if settings.rds_ids:
        discovery["rds"] = [x for x in discovery["rds"] if x.get("id") in set(settings.rds_ids)]
    discovery["counts"] = {"ec2":len(discovery["ec2"]),"rds":len(discovery["rds"])}
    return discovery

@app.get("/api/aws/status")
def aws_status():
    status = AWSDiscovery(settings.aws_region, settings.profile).status()
    status["mode"] = "aws" if settings.aws_mode else "dataset"
    return status

@app.get("/api/aws/resources")
def aws_resources():
    discovery = _aws_discovery()
    return discovery

@app.post("/api/aws/collect")
def collect_aws(lookback_minutes: int=Query(60, ge=1, le=1440)):
    if not settings.aws_mode:
        raise HTTPException(status_code=400,detail="AWS_MODE=false. Set AWS_MODE=true for live AWS collection.")
    discovery = _aws_discovery()
    ec2_ids=[x["id"] for x in discovery["ec2"]]
    rds_ids=[x["id"] for x in discovery["rds"]]
    raw=CloudWatchAdapter(settings.aws_region,lookback_minutes,settings.cloudwatch_period_seconds,settings.profile).collect(ec2_ids,rds_ids,include_application=settings.collect_application_metrics)
    raw=_permitted_aws(raw)
    raw["resource_discovery"]=discovery
    return raw

@app.post("/api/aws/analyze")
def analyze_aws(transaction_type: str | None = None, lookback_minutes: int=Query(60, ge=1, le=1440), db:Session=Depends(get_db)):
    if not settings.aws_mode:
        raise HTTPException(status_code=400,detail="AWS_MODE=false. Set AWS_MODE=true for live AWS analysis.")
    discovery = _aws_discovery()
    if not discovery["ec2"] and not discovery["rds"]:
        raise HTTPException(status_code=404,detail="No EC2 or RDS resources discovered in the selected region.")
    ec2_ids=[x["id"] for x in discovery["ec2"]]
    rds_ids=[x["id"] for x in discovery["rds"]]
    raw=CloudWatchAdapter(settings.aws_region,lookback_minutes,settings.cloudwatch_period_seconds,settings.profile).collect(ec2_ids,rds_ids,include_application=settings.collect_application_metrics)
    raw=_permitted_aws(raw)
    if raw.get("observed_metric_count",0) == 0:
        detail={"message":"No CloudWatch datapoints were returned for the discovered resources in the configured lookback window.","region":settings.aws_region,"resources":discovery["counts"]}
        raise HTTPException(status_code=424,detail=detail)
    if raw.get("errors"):
        raise HTTPException(502, {"message":"CloudWatch collection was incomplete; retry before diagnosis.","errors":raw["errors"]})
    mapping=load_mapping(settings.aws_mapping_file)
    sample=build_aws_sample(discovery,raw,transaction_type or settings.aws_transaction_type,mapping)
    result=pipeline.analyze(sample,source="aws_cloudwatch")
    run_id=persist(result,db)
    payload=result.model_dump(mode="json")
    payload["run_id"]=run_id
    payload["aws_collection"]={"region":raw["region"],"timestamp":raw["timestamp"],"period_seconds":raw["period_seconds"],"observed_metric_count":raw["observed_metric_count"],"api_calls":raw["api_calls"],"exclusion_policy":raw.get("exclusion_policy")}
    payload["aws_discovery"]=discovery
    return payload

@app.get("/api/metrics")
def metrics():
    return {"metric_names":["cpu_percent","memory_percent","network_in_mbps","network_out_mbps","latency_ms","error_rate","request_rate","db_latency_ms","disk_io"]}


@app.middleware('http')
async def request_timing(request, call_next):
    started = time.perf_counter()
    response = await call_next(request)
    response.headers['Server-Timing'] = f'total;dur={(time.perf_counter()-started)*1000:.2f}'
    return response


@app.get('/api/diagnostics/database')
def database_diagnostics():
    from database.diagnostics import local_database_health, postgres_evidence
    return {'analytics_store': local_database_health(), 'monitored_database': postgres_evidence(settings.monitored_database_url)}


@app.get('/api/research/observed')
def observed_research():
    report = Path('results/observed/report.json')
    if not report.exists():
        raise HTTPException(424, 'Run scripts/run_observed_research.py to produce a measured-data study.')
    return json.loads(report.read_text(encoding='utf-8'))


@app.post('/api/aws/database/diagnostics')
def aws_database_diagnostics(instance_id: str, db: Session=Depends(get_db)):
    if not settings.aws_mode:
        raise HTTPException(400, 'Enable AWS_MODE for live database evidence.')
    discovery = _aws_discovery()
    if instance_id not in {item['id'] for item in discovery['ec2']}:
        raise HTTPException(404, 'Instance is not in the discovered EC2 resource set.')
    from aws.ssm_postgres import collect_postgres
    from database.models import DiagnosticSnapshot
    from botocore.exceptions import BotoCoreError, ClientError
    try:
        observation = collect_postgres(instance_id, settings.aws_region, settings.profile)
    except (BotoCoreError, ClientError):
        raise HTTPException(502, 'SSM read-only database diagnostics are unavailable. Check the managed instance and permissions.')
    if observation['status'] != 'observed':
        raise HTTPException(424, observation)
    previous = db.query(DiagnosticSnapshot).filter(DiagnosticSnapshot.resource_id==instance_id).order_by(DiagnosticSnapshot.created_at.desc()).first()
    if previous:
        observation['previous_observation'] = json.loads(previous.payload).get('observation')
    row=DiagnosticSnapshot(resource_id=instance_id,source='aws_ssm_postgresql',payload=json.dumps({k:v for k,v in observation.items() if k!='previous_observation'}))
    try:
        db.add(row); db.commit(); db.refresh(row)
    except Exception:
        db.rollback(); raise
    from analysis.evidence import database_findings
    observation['investigation']=database_findings(observation)
    observation['snapshot_id']=row.id
    return observation


@app.post('/api/aws/refine')
def refine_aws(run_id: int, db: Session=Depends(get_db)):
    if not settings.aws_mode:
        raise HTTPException(400, 'Enable AWS_MODE for live evidence collection.')
    row = db.get(AnalysisRun, run_id)
    if not row or row.source != 'aws_cloudwatch':
        raise HTTPException(404, 'AWS analysis run not found.')
    before = json.loads(row.payload)
    frontier = before['cfao'].get('refinement',{}).get('evidence_gated_frontier',before['cfao']['causal_frontier'])
    if not frontier:
        raise HTTPException(409, 'No evidence-supported frontier. Collect a longer baseline first.')
    physical=set(frontier)
    for edge in before['graph'].get('edges',[]):
        if edge['source'] in physical and edge.get('relationship')=='HOSTED_ON':physical.add(edge['target'])
    discovery = _aws_discovery()
    for group in ('ec2', 'rds'):
        discovery[group] = [r for r in discovery[group] if r['id'] in physical]
    raw = CloudWatchAdapter(settings.aws_region, settings.cloudwatch_lookback_minutes, settings.cloudwatch_period_seconds, settings.profile).collect(
        [r['id'] for r in discovery['ec2']], [r['id'] for r in discovery['rds']], include_application=settings.collect_application_metrics)
    raw=_permitted_aws(raw)
    if raw.get('errors') or not raw['observed_metric_count']:
        raise HTTPException(424, 'Focused AWS collection returned no complete usable evidence.')
    sample = build_aws_sample(discovery, raw, before['transaction']['type'], load_mapping(settings.aws_mapping_file))
    after = pipeline.analyze(sample, source='aws_cloudwatch')
    after_id = persist(after, db)
    from analysis.evidence import compare_series, assess_followup
    old_series = before['graph']['metadata'].get('series', {})
    comparison = compare_series(old_series, sample.metadata['series'])
    old_latest = max((p['timestamp_ms'] for metrics in old_series.values() for points in metrics.values() for p in points), default=0)
    new_latest = max((p['timestamp_ms'] for metrics in sample.metadata['series'].values() for points in metrics.values() for p in points), default=0)
    return {'before_run_id': run_id, 'after_run_id': after_id, 'after': after.model_dump(mode='json'),
            'new_observations_available': any(c['new_point_count'] for c in comparison), 'comparison': comparison, 'followup': assess_followup(before['assessment'].get('evidence',[]), old_series, sample.metadata['series']), 'recovery_status': 'not_established', 'sampling_changed': False,
            'note': 'Fresh read of frontier resources at native resolution. Overlapping windows are not independent validation.'}


# Controlled-fault routes are intentionally not registered in observed-only mode.

from backend.research_api import router as research_router
app.include_router(research_router)

frontend_dist = Path(__file__).resolve().parents[1] / 'frontend' / 'dist'
if frontend_dist.is_dir():
    app.mount('/', StaticFiles(directory=frontend_dist, html=True), name='dashboard')
