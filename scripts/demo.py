import sys
from pathlib import Path as _Path
ROOT=_Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import argparse, json
from dataset.generator import generate_sample
from backend.services.pipeline import AnalysisPipeline
p=argparse.ArgumentParser(); p.add_argument("--scenario", default="DATABASE_LATENCY"); p.add_argument("--seed", type=int, default=42)
a=p.parse_args(); result=AnalysisPipeline().analyze(generate_sample(a.scenario,a.seed,0), source="demo")
print(json.dumps(result.model_dump(mode="json"), indent=2))
