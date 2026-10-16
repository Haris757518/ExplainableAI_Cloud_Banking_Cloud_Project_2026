import torch
from dataset.generator import generate_sample
from common.config import get_settings
from ai_models.anomaly_engine import AIEngine
from ai_models.explain import explain

def test_mean_based_xai_feature_ablation():
    with open("ai_models/explain.py", "r", encoding="utf-8") as f:
        content = f.read()
    assert ".mean()" in content
    assert "perturbed[:,j]=0.0" not in content.replace(" ", "")

def test_database_latency_explanation():
    s=generate_sample("DATABASE_LATENCY",42,0, tx_type="FUND_TRANSFER")
    engine=AIEngine(get_settings().model_path)
    res = explain(engine, s)
    assert res["important_features"]
