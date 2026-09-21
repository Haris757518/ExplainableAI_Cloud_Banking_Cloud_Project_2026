from __future__ import annotations
import torch
from ai_models.anomaly_engine import AIEngine
from graph.builder import build_graph
from common.features import FEATURE_NAMES
from common.schema import AnalysisSample


def explain(engine: AIEngine, sample: AnalysisSample, top_k: int = 6) -> dict:
    graph = build_graph(sample)
    baseline = engine.analyze(sample)["anomaly_score"]
    importances = []
    for j, feature in enumerate(FEATURE_NAMES):
        perturbed = graph.x.clone()
        perturbed[:, j] = 0.0
        with torch.no_grad():
            _, node_logits = engine.model(perturbed, graph.edge_index)
            score = torch.sigmoid(node_logits.max()).item()
        importances.append({"feature": feature, "importance": max(0.0, baseline - score)})
    importances.sort(key=lambda x: x["importance"], reverse=True)
    important_nodes = engine.analyze(sample)["affected_nodes"][:top_k]
    return {"important_features": importances[:top_k], "important_nodes": important_nodes}
