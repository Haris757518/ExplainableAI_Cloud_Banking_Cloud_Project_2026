from __future__ import annotations
import torch
from ai_models.anomaly_engine import AIEngine
from graph.builder import build_graph
from common.features import FEATURE_NAMES
from common.schema import AnalysisSample


def explain(engine: AIEngine, sample: AnalysisSample, top_k: int = 7) -> dict:
    graph = build_graph(sample)
    x = graph.x.to(engine.device)
    edges = graph.edge_index.to(engine.device)
    weights = graph.edge_weight.to(engine.device) if graph.edge_weight is not None else None
    
    with torch.no_grad():
        base_logit, _ = engine.model(x, edges, weights)
        baseline = float(base_logit.item())

    importances = []
    for j, feature in enumerate(FEATURE_NAMES):
        perturbed = x.clone()
        perturbed[:, j] = x[:, j].mean()
        with torch.no_grad():
            graph_logit, _ = engine.model(perturbed, edges, weights)
            score = float(graph_logit.item())
        importances.append({"feature": feature, "importance": max(0.0, baseline - score)})
    
    total = sum(x["importance"] for x in importances)
    if total > 0:
        for x in importances:
            x["importance"] /= total

    importances.sort(key=lambda x: x["importance"], reverse=True)
    nodes = engine.analyze(sample)["affected_nodes"][:top_k]
    return {"important_features": importances[:top_k], "important_nodes": nodes}
