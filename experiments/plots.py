from __future__ import annotations
import json
from pathlib import Path
import matplotlib.pyplot as plt


def make_plots(results_path: str = "results/runtime/research_suite.json", out_dir: str = "results/runtime/plots"):
    results=json.loads(Path(results_path).read_text(encoding="utf-8")); out=Path(out_dir); out.mkdir(parents=True,exist_ok=True)
    anomaly=results["anomaly_and_rca"]["anomaly"]
    labels=["Accuracy","Precision","Recall","F1"]
    gnn=[anomaly["gnn"][x.lower()] for x in labels]
    base=[anomaly["telemetry_only"][x.lower()] for x in labels]
    x=range(len(labels)); width=.36
    fig,ax=plt.subplots(figsize=(8,4.5)); ax.bar([i-width/2 for i in x],base,width,label="Telemetry-only"); ax.bar([i+width/2 for i in x],gnn,width,label="Transaction-conditioned GNN"); ax.set_xticks(list(x),labels); ax.set_ylim(0,1); ax.set_ylabel("Score"); ax.set_title("Anomaly Detection Comparison"); ax.legend(); fig.tight_layout(); fig.savefig(out/"anomaly_comparison.png",dpi=160); plt.close(fig)

    rca=results["anomaly_and_rca"]["rca_top1"]; names=list(rca.keys()); vals=list(rca.values())
    fig,ax=plt.subplots(figsize=(8,4.5)); ax.bar([n.replace("_"," ") for n in names],vals); ax.set_ylim(0,1); ax.set_ylabel("Top-1 accuracy"); ax.set_title("Root Cause Localization Comparison"); ax.tick_params(axis="x",rotation=20); fig.tight_layout(); fig.savefig(out/"rca_top1.png",dpi=160); plt.close(fig)

    temporal=results["temporal"]["examples"]
    if temporal:
        seq=temporal[0]
        # Plot one representative temporal sequence by using a deterministic research demo run.
        from dataset.generator import generate_sequence
        from backend.services.pipeline import AnalysisPipeline
        from analysis.temporal import analyze_temporal_window
        samples=generate_sequence(seq["scenario"],steps=8,seed=42,anomaly_start=3,tx_type=seq["transaction_type"],topology_change=True)
        scores=analyze_temporal_window(AnalysisPipeline().engine,samples)["steps"]
        fig,ax=plt.subplots(figsize=(8,4.5)); ax.plot([p["step"] for p in scores],[p["anomaly_score"] for p in scores],marker="o"); ax.axhline(0.5,linestyle="--",label="threshold"); ax.set_xlabel("Time step"); ax.set_ylabel("Anomaly score"); ax.set_title(f"Temporal Anomaly Evolution — {seq['transaction_type']}"); ax.legend(); fig.tight_layout(); fig.savefig(out/"temporal_anomaly.png",dpi=160); plt.close(fig)
    return sorted(str(p) for p in out.glob("*.png"))
