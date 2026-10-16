from __future__ import annotations
from statistics import mean
import torch
from ai_models.anomaly_engine import AIEngine
from ai_models.explain import explain
from graph.builder import build_graph
from common.features import FEATURE_NAMES
from common.schema import AnalysisSample


def evaluate_xai_faithfulness(engine: AIEngine, samples: list[AnalysisSample], top_k: int = 3) -> dict:
    drops=[]
    cases=0
    for sample in samples:
        if sample.scenario == "NORMAL":
            continue
        graph=build_graph(sample)
        baseline=float(engine.analyze(sample)["anomaly_score"])
        info=explain(engine,sample,top_k=top_k)
        selected=[FEATURE_NAMES.index(x["feature"]) for x in info["important_features"] if x["feature"] in FEATURE_NAMES]
        if not selected:
            continue
        perturbed=graph.x.clone(); perturbed[:, selected]=0.0
        with torch.no_grad():
            logit,_=engine.model(perturbed,graph.edge_index,graph.edge_weight)
            ablated=float(torch.sigmoid(logit).item())
        drops.append(max(0.0,baseline-ablated)/max(baseline,1e-6)); cases+=1
    return {"top_k":top_k,"cases":cases,"mean_anomaly_score_fraction_removed":round(mean(drops),4) if drops else 0.0}
