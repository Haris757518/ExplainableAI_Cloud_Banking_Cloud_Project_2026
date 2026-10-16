import sys, argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from dataset.generator import generate_dataset, write_jsonl

p=argparse.ArgumentParser(description="Generate reproducible digital-banking cloud telemetry")
p.add_argument("--samples",type=int,default=600)
p.add_argument("--seed",type=int,default=42)
p.add_argument("--out",default="dataset/generated/telemetry.jsonl")
a=p.parse_args()
items=generate_dataset(a.samples,seed=a.seed)
write_jsonl(items,a.out)
print(f"GENERATED {len(items)} samples -> {a.out}")
