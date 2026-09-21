from __future__ import annotations
from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
import json
from common.config import get_settings
from common.schema import AnalysisSample
from database.db import init_db, get_db
from database.models import AnalysisRun
from dataset.generator import generate_sample
from backend.services.pipeline import AnalysisPipeline
from aws.cloudwatch_adapter import CloudWatchAdapter
from aws.normalizer import normalize_aws_observations
from contextlib import asynccontextmanager

settings=get_settings()

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield

app=FastAPI(title="Digital Banking Cloud Performance Analytics", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[settings.frontend_origin,"http://127.0.0.1:5173"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])
pipeline=AnalysisPipeline()

@app.get("/api/health")
def health():
    return {"status":"ok","aws_mode":settings.aws_mode,"model_loaded":pipeline.engine.loaded}

@app.get("/api/dashboard")
def dashboard(db: Session = Depends(get_db)):
    rows=db.query(AnalysisRun).order_by(AnalysisRun.created_at.desc()).limit(20).all()
    return {
        "project":"Explainable AI-Based Cloud Performance Analytics for Digital Banking using Graph Neural Networks",
        "aws_mode":settings.aws_mode,
        "recent_runs":[{"id":r.id,"transaction_id":r.transaction_id,"scenario":r.scenario,"anomaly_score":r.anomaly_score,"is_anomaly":r.is_anomaly,"root_cause":r.root_cause,"source":r.source,"created_at":r.created_at.isoformat()} for r in rows]
    }

@app.get("/api/anomalies")
def anomalies(db: Session = Depends(get_db)):
    rows=db.query(AnalysisRun).filter(AnalysisRun.is_anomaly==True).order_by(AnalysisRun.created_at.desc()).limit(50).all()  # noqa: E712
    return [{"id":r.id,"scenario":r.scenario,"score":r.anomaly_score,"root_cause":r.root_cause,"source":r.source,"created_at":r.created_at.isoformat()} for r in rows]

@app.post("/api/analyze")
def analyze(sample: AnalysisSample, db: Session = Depends(get_db)):
    result=pipeline.analyze(sample, source="api")
    root=result.root_causes[0].node if result.root_causes else "none"
    row=AnalysisRun(transaction_id=result.transaction.id, scenario=result.scenario, anomaly_score=result.anomaly_score, is_anomaly=result.is_anomaly, root_cause=root, source=result.source, payload=result.model_dump_json())
    db.add(row); db.commit()
    return result

@app.post("/api/simulate")
def simulate(scenario: str = "DATABASE_LATENCY", seed: int = 42, db: Session = Depends(get_db)):
    try: sample=generate_sample(scenario, seed=seed, index=seed)
    except ValueError as exc: raise HTTPException(status_code=400, detail=str(exc))
    result=pipeline.analyze(sample, source="simulation")
    root=result.root_causes[0].node if result.root_causes else "none"
    row=AnalysisRun(transaction_id=result.transaction.id, scenario=result.scenario, anomaly_score=result.anomaly_score, is_anomaly=result.is_anomaly, root_cause=root, source=result.source, payload=result.model_dump_json())
    db.add(row); db.commit()
    return result

@app.get("/api/graph/{run_id}")
def graph(run_id: int, db: Session = Depends(get_db)):
    row=db.get(AnalysisRun, run_id)
    if not row: raise HTTPException(status_code=404, detail="analysis not found")
    payload=json.loads(row.payload)
    return {"nodes":payload["graph"]["nodes"],"edges":payload["graph"]["edges"],"affected_nodes":payload["affected_nodes"]}

@app.get("/api/rca/{run_id}")
def rca(run_id: int, db: Session = Depends(get_db)):
    row=db.get(AnalysisRun, run_id)
    if not row: raise HTTPException(status_code=404, detail="analysis not found")
    payload=json.loads(row.payload)
    return {"root_causes":payload["root_causes"],"explanation":payload["explanation"]}

@app.get("/api/cfao/{run_id}")
def cfao(run_id: int, db: Session = Depends(get_db)):
    row=db.get(AnalysisRun, run_id)
    if not row: raise HTTPException(status_code=404, detail="analysis not found")
    payload=json.loads(row.payload)
    return payload["cfao"]


@app.post("/api/aws/analyze")
def analyze_aws():
    if not settings.aws_mode:
        raise HTTPException(status_code=400, detail="AWS_MODE=false. Enable AWS mode to analyze CloudWatch telemetry.")
    adapter=CloudWatchAdapter(settings.aws_region, settings.cloudwatch_lookback_minutes, settings.cloudwatch_period_seconds)
    raw=adapter.collect(settings.ec2_ids, settings.rds_ids)
    sample=normalize_aws_observations(raw)
    return pipeline.analyze(sample, source="aws_cloudwatch")

@app.get("/api/metrics")
def metrics():
    return {"metric_names":["cpu_percent","memory_percent","network_in_mbps","network_out_mbps","latency_ms","error_rate","request_rate","db_latency_ms","disk_io"]}

@app.post("/api/aws/collect")
def collect_aws():
    if not settings.aws_mode:
        raise HTTPException(status_code=400, detail="AWS_MODE=false. Enable AWS mode to collect CloudWatch metrics.")
    adapter=CloudWatchAdapter(settings.aws_region, settings.cloudwatch_lookback_minutes, settings.cloudwatch_period_seconds)
    return adapter.collect(settings.ec2_ids, settings.rds_ids)
