import sys, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from dataset.generator import generate_sequence
from pathlib import Path as P
samples=generate_sequence("DATABASE_LATENCY",steps=8,seed=42,anomaly_start=3)
out=P("dataset/generated/temporal_database_latency.jsonl"); out.parent.mkdir(parents=True,exist_ok=True)
with out.open("w",encoding="utf-8") as f:
    for s in samples: f.write(json.dumps(s.model_dump(mode="json"))+"\n")
print(out)
