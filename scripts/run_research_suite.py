import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import json
from experiments.research_suite import run_suite

if __name__ == "__main__":
    print(json.dumps(run_suite(), indent=2))
