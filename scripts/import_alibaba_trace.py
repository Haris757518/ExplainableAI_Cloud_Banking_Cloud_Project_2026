from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from dataset.alibaba_adapter import build_snapshot, write_snapshot


def main() -> None:
    p = argparse.ArgumentParser(description="Import a manageable slice of Alibaba Microservices Trace v2021.")
    p.add_argument("--root", required=True, help="Directory containing extracted Alibaba trace data or trace archives")
    p.add_argument("--trace-id", default=None)
    p.add_argument("--timestamp", type=int, default=None)
    p.add_argument("--max-services", type=int, default=40)
    p.add_argument("--max-edges", type=int, default=80)
    p.add_argument("--out", default="dataset/processed/alibaba_snapshot.json")
    args = p.parse_args()
    snapshot = build_snapshot(args.root, trace_id=args.trace_id, timestamp=args.timestamp, max_services=args.max_services, max_edges=args.max_edges)
    write_snapshot(snapshot, args.out)
    print(json.dumps({"out": args.out, "source": snapshot.source, "nodes": len(snapshot.nodes), "edges": len(snapshot.edges), "timestamp": snapshot.timestamp}, indent=2))


if __name__ == "__main__":
    main()
