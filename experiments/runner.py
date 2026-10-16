from __future__ import annotations
import json
from pathlib import Path
from experiments.research_suite import run_suite


def run(samples:int=180, sequences:int=30, seed:int=42):
    return run_suite(samples=samples,sequences=sequences,seed=seed)


if __name__ == "__main__":
    print(json.dumps(run(),indent=2))
