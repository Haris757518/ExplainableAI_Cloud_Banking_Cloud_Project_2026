from __future__ import annotations
import argparse
from pathlib import Path
from urllib.request import Request, urlopen

BASE = "http://aliopentrace.oss-cn-beijing.aliyuncs.com/v2021MicroservicesTraces"


def download(url: str, out: Path) -> None:
    out.parent.mkdir(parents=True, exist_ok=True)
    req = Request(url, headers={"User-Agent": "ExplainableAI-Cloud-Banking/1.0"})
    with urlopen(req, timeout=60) as r, out.open("wb") as f:
        total = 0
        while True:
            chunk = r.read(1024 * 1024)
            if not chunk:
                break
            f.write(chunk)
            total += len(chunk)
            if total and total % (50 * 1024 * 1024) < len(chunk):
                print(f"downloaded {total / (1024*1024):.0f} MiB -> {out}")


def main() -> None:
    p = argparse.ArgumentParser(description="Fetch selected Alibaba Microservices Trace v2021 archives; never fetches the full dataset unless explicitly requested.")
    p.add_argument("--out", default="dataset/raw/alibaba_microservices_v2021")
    p.add_argument("--callgraph-index", type=int, default=0)
    p.add_argument("--include-resource", action="store_true")
    p.add_argument("--include-rtqps", action="store_true")
    p.add_argument("--include-node", action="store_true")
    args = p.parse_args()
    root = Path(args.out)
    download(f"{BASE}/MSCallGraph/MSCallGraph_{args.callgraph_index}.tar.gz", root / "MSCallGraph" / f"MSCallGraph_{args.callgraph_index}.tar.gz")
    if args.include_resource:
        download(f"{BASE}/MSResource/MSResource_0.tar.gz", root / "MSResource" / "MSResource_0.tar.gz")
    if args.include_rtqps:
        download(f"{BASE}/MSRTQps/MSRTQps_0.tar.gz", root / "MSRTQps" / "MSRTQps_0.tar.gz")
    if args.include_node:
        download(f"{BASE}/node/Node_0.tar.gz", root / "Node" / "Node_0.tar.gz")
    print("Subset download complete. See docs/ALIBABA_TRACE_DATASET.md for extraction/import steps and licensing/citation notes.")


if __name__ == "__main__":
    main()
