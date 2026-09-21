import sys
from pathlib import Path as _Path
ROOT=_Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from dataset.generator import generate_sample
from backend.services.pipeline import AnalysisPipeline
r=AnalysisPipeline().analyze(generate_sample("DATABASE_LATENCY",42,0), source="smoke")
assert r.is_anomaly, "Database latency demo should be detected as anomaly after training"
assert r.root_causes, "RCA list should not be empty"
assert r.cfao.causal_frontier, "CFAO frontier should not be empty"
print("SMOKE_TEST_OK", r.anomaly_score, r.root_causes[0].node)
