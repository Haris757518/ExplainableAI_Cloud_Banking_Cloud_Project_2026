import pytest
from common.config import get_settings
@pytest.fixture(autouse=True)
def enable_legacy_test_simulation(monkeypatch):
    monkeypatch.setattr(get_settings(), 'enable_simulation', True)

from dataset.generator import TX_TYPES, generate_dataset, generate_sequence
from graph.structures import topology_signature
from graph.temporal import build_temporal_graph
from analysis.baselines import telemetry_only_rca
from backend.services.pipeline import AnalysisPipeline


def test_transaction_topologies_are_distinct():
    samples=[generate_dataset(1,seed=42,tx_types=[tx])[0] for tx in TX_TYPES]
    sigs={topology_signature(s.nodes,s.edges) for s in samples}
    assert len(sigs)==len(TX_TYPES)


def test_transaction_conditioning_changes_graph_and_path():
    upi=generate_dataset(1,seed=42,tx_types=["UPI_PAYMENT"])[0]
    bill=generate_dataset(1,seed=42,tx_types=["BILL_PAYMENT"])[0]
    assert upi.transaction.path != bill.transaction.path
    assert topology_signature(upi.nodes,upi.edges) != topology_signature(bill.nodes,bill.edges)


def test_temporal_graph_has_topology_drift():
    seq=generate_sequence("CASCADING_FAILURE",steps=8,seed=42,anomaly_start=3,tx_type="CARD_PAYMENT",topology_change=True)
    tg=build_temporal_graph(seq)
    assert tg.length==8
    assert tg.topology_change_steps


def test_cfao_reduces_observation_cost_for_anomaly():
    pipeline=AnalysisPipeline()
    sample=generate_dataset(1,seed=7,scenarios=["DATABASE_LATENCY"],tx_types=["UPI_PAYMENT"])[0]
    result=pipeline.analyze(sample)
    assert result.is_anomaly
    full_cost=len(sample.nodes)*12
    adaptive=sum(12 if n in result.cfao.causal_frontier else 1 for n in sample.nodes)
    assert adaptive < full_cost
    assert telemetry_only_rca(sample,1)
