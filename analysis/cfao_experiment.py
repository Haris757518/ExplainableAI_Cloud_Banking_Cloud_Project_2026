from __future__ import annotations
from statistics import mean
from backend.services.pipeline import AnalysisPipeline
from common.schema import AnalysisSample


def observation_cost(sample: AnalysisSample, resolution_seconds: dict[str, int], horizon_seconds: int = 60) -> float:
    """Proxy telemetry volume: samples collected across nodes during one horizon."""
    return sum(horizon_seconds / max(1, int(resolution_seconds.get(n.id, 60))) for n in sample.nodes)


def evaluate_cfao_efficiency(pipeline: AnalysisPipeline, samples: list[AnalysisSample]) -> dict:
    reductions=[]
    frontier_sizes=[]
    diagnosis_consistent=0
    anomalous=0
    for sample in samples:
        result=pipeline.analyze(sample)
        if not result.is_anomaly or not result.cfao.causal_frontier:
            continue
        anomalous += 1
        frontier=set(result.cfao.causal_frontier)
        full={n.id:5 for n in sample.nodes}
        adaptive=result.cfao.telemetry_policy.resolution_seconds
        full_cost=observation_cost(sample, full)
        adaptive_cost=observation_cost(sample, adaptive)
        reduction=max(0.0, 100.0*(1.0-adaptive_cost/max(full_cost,1e-9)))
        reductions.append(reduction)
        frontier_sizes.append(len(frontier))
        refined=pipeline.run_adaptive_refinement(sample)
        before_root=(refined["before"].get("root_causes") or [{}])[0].get("node")
        after_root=(refined["after"].get("root_causes") or [{}])[0].get("node")
        if before_root and after_root and before_root == after_root:
            diagnosis_consistent += 1
    return {
        "anomalous_cases": anomalous,
        "mean_frontier_size": round(mean(frontier_sizes),3) if frontier_sizes else 0.0,
        "mean_observation_reduction_percent": round(mean(reductions),3) if reductions else 0.0,
        "diagnosis_consistency_after_refinement": round(diagnosis_consistent/max(1,anomalous),4),
        "comparison_baseline": "every node sampled at 5-second resolution for the same horizon",
    }
