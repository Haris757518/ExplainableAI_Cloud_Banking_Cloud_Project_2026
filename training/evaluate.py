import sys
from pathlib import Path as _Path
ROOT=_Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import json
from pathlib import Path
from training.train import run_training

if __name__ == "__main__":
    metrics = run_training(epochs=35, samples=600, seed=42)
    print(json.dumps(metrics, indent=2))
