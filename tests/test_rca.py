from dataset.generator import generate_sample
from analysis.rca import rank_root_causes

def test_rca_returns_candidates():
    s=generate_sample("DATABASE_LATENCY",42,0)
    causes=rank_root_causes(s,{n.id:0.8 for n in s.nodes})
    assert causes
