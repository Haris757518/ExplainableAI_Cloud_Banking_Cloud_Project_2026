import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from experiments.plots import make_plots

if __name__ == "__main__":
    for p in make_plots(): print(p)
