from __future__ import annotations
from statistics import mean
from common.schema import AnalysisSample
from ai_models.anomaly_engine import AIEngine
from graph.temporal import build_temporal_graph


def analyze_temporal_window(engine: AIEngine, samples: list[AnalysisSample]) -> dict:
    if not samples:
        return {"steps": [], "onset_step": None, "peak": None, "mean_score": 0.0, "recovered": False, "topology_change_steps": []}
    temporal_graph = build_temporal_graph(samples)
    points=[]
    for sample in samples:
        r=engine.analyze(sample)
        points.append({
            "step": sample.sequence_index,
            "scenario": sample.scenario,
            "transaction_type": sample.transaction.type,
            "anomaly_score": round(float(r["anomaly_score"]),4),
            "top_node": r["affected_nodes"][0]["node"] if r["affected_nodes"] else None,
            "top_node_score": round(float(r["affected_nodes"][0]["score"]),4) if r["affected_nodes"] else 0.0,
            "topology_signature": temporal_graph.sequence.snapshots[len(points)].topology_signature,
        })
    scores=[p["anomaly_score"] for p in points]
    onset=next((p["step"] for p in points if p["anomaly_score"] >= engine.threshold), None)
    peak=max(points, key=lambda x:x["anomaly_score"]) if points else None
    return {
        "steps": points,
        "onset_step": onset,
        "peak": peak,
        "mean_score": round(mean(scores),4) if scores else 0.0,
        "recovered": bool(points and points[-1]["anomaly_score"] < engine.threshold),
        "topology_change_steps": temporal_graph.topology_change_steps,
        "unique_topologies": len(set(temporal_graph.sequence.topology_signatures)),
    }
