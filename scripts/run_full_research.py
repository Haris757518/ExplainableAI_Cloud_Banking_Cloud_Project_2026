import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
from pathlib import Path
from experiments.research_suite import run_suite

if __name__ == "__main__":
    result = run_suite(samples=180, sequences=30, seed=42)
    print(json.dumps(result, indent=2))
    print(f"\nSaved: {Path('results/runtime/research_suite.json').resolve()}")
