from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dataset.alibaba_adapter import build_snapshot


def main() -> None:
    p = argparse.ArgumentParser(description="Summarize a real Alibaba Microservices Trace slice for the research review.")
    p.add_argument("--root", required=True)
    p.add_argument("--trace-id", default=None)
    p.add_argument("--timestamp", type=int, default=None)
    p.add_argument("--max-services", type=int, default=40)
    p.add_argument("--max-edges", type=int, default=80)
    args = p.parse_args()
    s = build_snapshot(args.root, trace_id=args.trace_id, timestamp=args.timestamp, max_services=args.max_services, max_edges=args.max_edges)
    degree = {}
    for e in s.edges:
        degree[e["source"]] = degree.get(e["source"], 0) + e["weight"]
        degree[e["target"]] = degree.get(e["target"], 0) + e["weight"]
    observed = sorted({m for t in s.telemetry for m in t["observed_metrics"]})
    print(json.dumps({
        "dataset": s.source,
        "claim": "real Alibaba production microservice trace slice; not banking telemetry",
        "timestamp": s.timestamp,
        "nodes": len(s.nodes),
        "edges": len(s.edges),
        "observed_metrics": observed,
        "top_services_by_graph_degree": sorted(degree.items(), key=lambda kv: kv[1], reverse=True)[:10],
        "graph_relationships": sorted({e["relationship"] for e in s.edges}),
        "next_step": "Use this as a benchmark/structure dataset; use controlled anomaly injection separately for supervised anomaly/RCA labels."
    }, indent=2))


if __name__ == "__main__":
    main()
