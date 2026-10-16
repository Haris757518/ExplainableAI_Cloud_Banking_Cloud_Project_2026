import sys, json, argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]; sys.path.insert(0,str(ROOT))
from dataset.generator import generate_sample, generate_sequence
from backend.services.pipeline import AnalysisPipeline
from analysis.temporal import analyze_temporal_window

def main():
    p=argparse.ArgumentParser(); p.add_argument("--scenario",default="DATABASE_LATENCY"); p.add_argument("--seed",type=int,default=42); a=p.parse_args()
    pipeline=AnalysisPipeline()
    sample=generate_sample(a.scenario,seed=a.seed,index=0,tx_type="UPI_PAYMENT")
    result=pipeline.analyze(sample,source="research_demo")
    print("=== BASELINE ANALYSIS ===")
    print(json.dumps(result.model_dump(mode="json"),indent=2))
    adaptive=pipeline.run_adaptive_refinement(sample)
    print("=== TC-CFAO ADAPTIVE REFINEMENT ===")
    print(json.dumps(adaptive,indent=2))
    temporal=analyze_temporal_window(pipeline.engine,generate_sequence(a.scenario,steps=8,seed=a.seed,anomaly_start=3))
    print("=== TEMPORAL WINDOW ===")
    print(json.dumps(temporal,indent=2))

if __name__=="__main__": main()
