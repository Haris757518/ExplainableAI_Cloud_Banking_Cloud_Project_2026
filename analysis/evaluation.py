from __future__ import annotations
from dataclasses import dataclass
from statistics import mean
from typing import Callable

import numpy as np

from ai_models.anomaly_engine import AIEngine
from ai_models.explain import explain
from common.schema import AnalysisSample
from analysis.baselines import telemetry_only_anomaly, telemetry_only_rca, graph_centrality_rca
from analysis.counterfactual import evaluate_counterfactual
from analysis.rca import rank_root_causes


@dataclass
class BinaryMetrics:
    accuracy: float
    precision: float
    recall: float
    f1: float

    def as_dict(self):
        return self.__dict__


def binary_metrics(y_true: list[int], y_pred: list[int]) -> BinaryMetrics:
    tp = sum(a == 1 and b == 1 for a, b in zip(y_true, y_pred))
    tn = sum(a == 0 and b == 0 for a, b in zip(y_true, y_pred))
    fp = sum(a == 0 and b == 1 for a, b in zip(y_true, y_pred))
    fn = sum(a == 1 and b == 0 for a, b in zip(y_true, y_pred))
    precision = tp / (tp + fp) if tp + fp else 0.0
    recall = tp / (tp + fn) if tp + fn else 0.0
    f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
    accuracy = (tp + tn) / max(1, len(y_true))
    return BinaryMetrics(round(accuracy, 4), round(precision, 4), round(recall, 4), round(f1, 4))


def evaluate_anomaly_and_rca(engine: AIEngine, samples: list[AnalysisSample]) -> dict:
    truth, gnn_pred, base_pred = [], [], []
    root_true, gnn_root, telem_root, central_root = [], [], [], []
    for sample in samples:
        is_anom = int(sample.scenario != "NORMAL")
        truth.append(is_anom)
        ai = engine.analyze(sample)
        gnn_pred.append(int(ai["is_anomaly"]))
        _, baseline_flag = telemetry_only_anomaly(sample)
        base_pred.append(int(baseline_flag))
        if is_anom and sample.root_cause_nodes:
            root_true.append(sample.root_cause_nodes[0])
            gnn_candidates = rank_root_causes(sample, ai["node_scores"])
            gnn_root.append(gnn_candidates[0].node if gnn_candidates else "none")
            telem_root.append(telemetry_only_rca(sample, 1)[0])
            central_root.append(graph_centrality_rca(sample, 1)[0])
    return {
        "anomaly": {
            "gnn": binary_metrics(truth, gnn_pred).as_dict(),
            "telemetry_only": binary_metrics(truth, base_pred).as_dict(),
        },
        "rca_top1": {
            "gnn_transaction_conditioned": sum(a == b for a, b in zip(root_true, gnn_root)) / max(1, len(root_true)),
            "telemetry_only": sum(a == b for a, b in zip(root_true, telem_root)) / max(1, len(root_true)),
            "graph_centrality": sum(a == b for a, b in zip(root_true, central_root)) / max(1, len(root_true)),
        },
        "samples": len(samples),
    }


def evaluate_xai_faithfulness(engine: AIEngine, samples: list[AnalysisSample], top_k: int = 3) -> dict:
    ratios = []
    for sample in samples:
        if sample.scenario == "NORMAL":
            continue
        original = engine.analyze(sample)["anomaly_score"]
        result = explain(engine, sample, top_k=top_k)
        if not result["important_features"]:
            continue
        x, names = result["important_features"], [f["feature"] for f in result["important_features"]]
        baseline = engine.analyze(sample)["anomaly_score"]
        # Recompute importance through the public model interface and ablate selected features.
        graph = __import__("graph.builder", fromlist=["build_graph"]).build_graph(sample)
        from common.features import FEATURE_NAMES
        import torch
        selected = [FEATURE_NAMES.index(n) for n in names if n in FEATURE_NAMES]
        perturbed = graph.x.clone()
        if selected:
            perturbed[:, selected] = 0.0
        with torch.no_grad():
            logit, _ = engine.model(perturbed, graph.edge_index, graph.edge_weight)
            ablated = float(torch.sigmoid(logit).item())
        drop = max(0.0, baseline - ablated)
        ratios.append(drop / max(1e-6, original))
    return {"mean_top_feature_ablation_fraction": round(mean(ratios), 4) if ratios else 0.0, "evaluated_anomalous_samples": len(ratios)}


def evaluate_counterfactuals(engine: AIEngine, samples: list[AnalysisSample]) -> dict:
    reductions = []
    correct = 0
    for sample in samples:
        if sample.scenario == "NORMAL" or not sample.root_cause_nodes:
            continue
        for node in sample.root_cause_nodes[:1]:
            cf = evaluate_counterfactual(engine, sample, node)
            reductions.append(cf.score_reduction)
            if cf.score_reduction > 0:
                correct += 1
    return {
        "mean_score_reduction": round(mean(reductions), 4) if reductions else 0.0,
        "counterfactual_success_rate": round(correct / max(1, len(reductions)), 4),
        "evaluated_cases": len(reductions),
    }
