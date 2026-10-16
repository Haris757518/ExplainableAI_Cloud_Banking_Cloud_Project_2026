from pathlib import Path
import tarfile

from dataset.alibaba_adapter import build_snapshot, load_callgraph_edges


def _write_tar(path: Path, files: dict[str, str]):
    with tarfile.open(path, "w:gz") as tf:
        for name, text in files.items():
            p = path.parent / name
            p.write_text(text, encoding="utf-8")
            tf.add(p, arcname=name)
            p.unlink()


def test_load_callgraph_edges_filters_trace(tmp_path):
    tar = tmp_path / "MSCallGraph_0.tar.gz"
    _write_tar(tar, {
        "cg.tsv": "timestamp\ttraceid\trpcid\tum\trpctype\tinterface\tdm\trt\n1000\tT1\t1\tA\trpc\ti\tB\t12\n1000\tT2\t1\tX\trpc\ti\tY\t20\n"
    })
    edges, counts, ts = load_callgraph_edges(tar, trace_id="T1")
    assert ts == 1000
    assert counts["T1"] == 1
    assert edges[0]["source"] == "A"
    assert edges[0]["target"] == "B"


def test_build_snapshot_uses_real_trace_fields(tmp_path):
    root = tmp_path / "data"
    (root / "MSCallGraph").mkdir(parents=True)
    (root / "MSResource").mkdir()
    (root / "MSRTQps").mkdir()
    cg = root / "MSCallGraph" / "MSCallGraph_0.tar.gz"
    _write_tar(cg, {
        "cg.tsv": "timestamp\ttraceid\trpcid\tum\trpctype\tinterface\tdm\trt\n1000\tT1\t1\tA\trpc\ti\tB\t12\n1000\tT1\t1\tB\trpc\ti\tC\t20\n"
    })
    (root / "MSResource" / "MSResource_0.tsv").write_text(
        "timestamp\tmsname\tmsinstanceid\tnodeid\tcpu_utilization\tmemory_utilization\n1000\tA\ti1\tn1\t0.5\t0.25\n1000\tB\ti2\tn2\t0.6\t0.4\n1000\tC\ti3\tn3\t0.7\t0.5\n", encoding="utf-8"
    )
    s = build_snapshot(root, trace_id="T1", max_services=10, max_edges=10)
    assert s.source == "alibaba_microservices_v2021"
    assert len(s.nodes) == 3
    assert len(s.edges) == 2
    assert any("cpu_percent" in t["observed_metrics"] for t in s.telemetry)
