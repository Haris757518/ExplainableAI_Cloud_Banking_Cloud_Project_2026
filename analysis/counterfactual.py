from __future__ import annotations
from dataclasses import replace
import copy
from common.schema import AnalysisSample, CounterfactualResult
from ai_models.anomaly_engine import AIEngine

def _baseline_telemetry(sample: AnalysisSample, node_id: str):
    # A conservative synthetic intervention baseline. In real AWS mode, this is a
    # simulation of the intervention, not a claimed change to production AWS.
    for t in sample.telemetry:
        if t.node_id == node_id:
            t.db_latency_ms = min(t.db_latency_ms, 80.0)
            t.latency_ms = min(t.latency_ms, 100.0)
            t.cpu_percent = min(t.cpu_percent, 55.0)
            t.memory_percent = min(t.memory_percent, 65.0)
            t.error_rate = min(t.error_rate, 0.02)
            t.disk_io = min(t.disk_io, 250.0)
            break

def evaluate_counterfactual(engine: AIEngine, sample: AnalysisSample, node_id: str) -> CounterfactualResult:
    original = float(engine.analyze(sample)["anomaly_score"])
    intervened = copy.deepcopy(sample)
    _baseline_telemetry(intervened, node_id)
    counter = float(engine.analyze(intervened)["anomaly_score"])
    reduction = max(0.0, original - counter)
    interpretation = (
        f"Reducing abnormal telemetry at {node_id} lowered the model anomaly score by "
        f"{reduction:.3f}. This supports the node as an influential candidate in this simulated intervention."
    )
    return CounterfactualResult(
        node=node_id,
        intervention="reset abnormal telemetry toward baseline",
        original_anomaly_score=round(original, 4),
        counterfactual_anomaly_score=round(counter, 4),
        score_reduction=round(reduction, 4),
        interpretation=interpretation,
    )
