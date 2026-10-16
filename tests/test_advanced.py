import pytest
from common.config import get_settings
@pytest.fixture(autouse=True)
def enable_legacy_test_simulation(monkeypatch):
    monkeypatch.setattr(get_settings(), 'enable_simulation', True)

from dataset.generator import generate_sample, generate_sequence
from backend.services.pipeline import AnalysisPipeline
from analysis.temporal import analyze_temporal_window

def test_transaction_conditioned_path():
    s=generate_sample("DATABASE_LATENCY",42,0,tx_type="UPI_PAYMENT")
    assert s.transaction.path[:2]==["api-gateway","payment-service"]

def test_counterfactual_exists_and_reduces_or_matches():
    r=AnalysisPipeline().analyze(generate_sample("DATABASE_LATENCY",42,0,tx_type="UPI_PAYMENT"))
    assert r.counterfactual is not None
    assert r.counterfactual.node == r.root_causes[0].node
    assert r.counterfactual.score_reduction >= 0
    assert r.cfao.telemetry_policy.estimated_high_resolution_reduction_percent >= 0

def test_temporal_window_has_onset_and_recovery():
    p=AnalysisPipeline()
    result=analyze_temporal_window(p.engine, generate_sequence("DATABASE_LATENCY",steps=8,seed=42,anomaly_start=3,tx_type="UPI_PAYMENT",topology_change=True))
    assert len(result["steps"])==8
    assert result["onset_step"] is not None
    assert result["recovered"] is True
    assert result["unique_topologies"] >= 1
