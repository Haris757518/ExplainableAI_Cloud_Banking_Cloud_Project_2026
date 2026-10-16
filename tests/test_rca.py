from dataset.generator import generate_sample
from analysis.rca import rank_root_causes

def test_rca_returns_candidates():
    s=generate_sample("DATABASE_LATENCY",42,0)
    causes=rank_root_causes(s,{n.id:0.8 for n in s.nodes})
    assert causes

def test_fund_transfer_rca_relevance():
    s=generate_sample("NORMAL",42,0, tx_type="FUND_TRANSFER")
    causes=rank_root_causes(s,{n.id:0.8 for n in s.nodes}, top_k=100)
    rel = {c.node: c.transaction_relevance for c in causes}
    
    assert rel.get("transfer-service") == 1.0
    assert rel.get("ec2-01") == 1.0
    assert rel.get("rds-01") == 1.0
    
    assert any(v == 0.5 for v in rel.values()), "Expected at least one secondary dependency with 0.5"

def test_card_payment_unrelated_node():
    s=generate_sample("NORMAL",42,0, tx_type="CARD_PAYMENT")
    causes=rank_root_causes(s,{n.id:0.8 for n in s.nodes}, top_k=100)
    rel = {c.node: c.transaction_relevance for c in causes}
    # Some node in this larger graph should be completely unrelated (0.0)
    assert any(v == 0.0 for v in rel.values()), "Expected at least one unrelated node with 0.0 in CARD_PAYMENT"

