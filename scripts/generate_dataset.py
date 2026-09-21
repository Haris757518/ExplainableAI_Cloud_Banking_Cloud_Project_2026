import sys
from pathlib import Path as _Path
ROOT=_Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import argparse
from dataset.generator import generate_dataset, write_jsonl

p=argparse.ArgumentParser(); p.add_argument("--samples", type=int, default=600); p.add_argument("--seed", type=int, default=42); p.add_argument("--out", default="dataset/generated/telemetry.jsonl")
a=p.parse_args(); samples=generate_dataset(a.samples, a.seed); write_jsonl(samples, a.out); print(f"Generated {len(samples)} samples -> {a.out}")
