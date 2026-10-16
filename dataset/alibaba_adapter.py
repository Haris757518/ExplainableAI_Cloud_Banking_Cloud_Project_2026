from __future__ import annotations

import csv
import io
import json
import tarfile
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Iterator


@dataclass(frozen=True)
class AlibabaRowSources:
    callgraph: Path | None = None
    msresource: Path | None = None
    msrtqps: Path | None = None
    node: Path | None = None


@dataclass
class AlibabaGraphSnapshot:
    source: str
    trace_id: str | None
    timestamp: int | None
    nodes: list[dict]
    edges: list[dict]
    telemetry: list[dict]
    metadata: dict


    def to_analysis_sample(self):
        from common.schema import AnalysisSample, GraphNode, GraphEdge, TelemetryPoint, TransactionContext
        fields = ('cpu_percent', 'memory_percent', 'network_in_mbps', 'network_out_mbps', 'latency_ms', 'error_rate', 'request_rate', 'db_latency_ms', 'disk_io')
        telemetry = [TelemetryPoint(node_id=t['node_id'], timestamp=None, source='alibaba_trace',
                     observed_metrics=[k for k in t.get('observed_metrics', []) if t.get(k) is not None],
                     **{k: t[k] for k in fields if k in t.get('observed_metrics', []) and t.get(k) is not None}) for t in self.telemetry]
        return AnalysisSample(transaction=TransactionContext(id=self.trace_id or f'ALIBABA-{self.timestamp}', type='ALIBABA_BENCHMARK', path=[]),
            nodes=[GraphNode(id=n['id'], type=n.get('type','microservice'), label=n.get('label',n['id']), layer=n.get('layer','service')) for n in self.nodes],
            edges=[GraphEdge(source=e['source'], target=e['target'], relationship=e.get('relationship','CALLS')) for e in self.edges],
            telemetry=telemetry, scenario='UNLABELED', node_labels={}, root_cause_nodes=[], source='alibaba_trace', metadata=self.metadata)

    def to_json(self) -> dict:
        return {
            "source": self.source,
            "trace_id": self.trace_id,
            "timestamp": self.timestamp,
            "nodes": self.nodes,
            "edges": self.edges,
            "telemetry": self.telemetry,
            "metadata": self.metadata,
        }


def _iter_text_rows(path: Path, member_hint: str | None = None) -> Iterator[dict[str, str]]:
    """Stream delimited text from a plain file or a tar/tar.gz archive.

    The Alibaba release is distributed as tar.gz archives containing tabular text.
    Delimiter detection is intentionally conservative: tab first, then comma.
    """
    def parse_stream(stream: io.TextIOBase) -> Iterator[dict[str, str]]:
        first = stream.readline()
        if not first:
            return
        sample = first + stream.read(4096)
        stream.seek(0)
        delimiter = "\t" if "\t" in first else ","
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters="\t,")
            delimiter = dialect.delimiter
        except csv.Error:
            pass
        reader = csv.DictReader(stream, delimiter=delimiter)
        for row in reader:
            if row:
                yield {str(k).strip(): (v.strip() if isinstance(v, str) else v) for k, v in row.items()}

    name = path.name.lower()
    if name.endswith((".tar.gz", ".tgz", ".tar")):
        with tarfile.open(path, "r:*") as tf:
            members = [m for m in tf.getmembers() if m.isfile() and not m.name.endswith(("/",))]
            if member_hint:
                members = [m for m in members if member_hint.lower() in m.name.lower()] or members
            for member in members:
                f = tf.extractfile(member)
                if not f:
                    continue
                with io.TextIOWrapper(f, encoding="utf-8", errors="replace", newline="") as stream:
                    yield from parse_stream(stream)
    else:
        with path.open("r", encoding="utf-8", errors="replace", newline="") as stream:
            yield from parse_stream(stream)


def _pick_column(row: dict[str, str], *names: str) -> str | None:
    lowered = {k.lower().replace(" ", "_"): k for k in row}
    for name in names:
        k = lowered.get(name.lower().replace(" ", "_"))
        if k is not None:
            return row.get(k)
    return None


def discover_sources(root: str | Path) -> AlibabaRowSources:
    root = Path(root)
    candidates = [p for p in root.rglob("*") if p.is_file()]
    def find(*parts: str) -> Path | None:
        for p in candidates:
            low = p.as_posix().lower()
            if all(part.lower() in low for part in parts):
                return p
        return None
    return AlibabaRowSources(
        callgraph=find("mscallgraph"),
        msresource=find("msresource"),
        msrtqps=find("msrtqps"),
        node=find("node"),
    )


def load_callgraph_edges(path: str | Path, trace_id: str | None = None, timestamp: int | None = None, max_edges: int = 1000) -> tuple[list[dict], Counter, int | None]:
    edges_counter: Counter[tuple[str, str, str]] = Counter()
    trace_counts: Counter[str] = Counter()
    chosen_timestamp = timestamp
    for row in _iter_text_rows(Path(path)):
        tid = _pick_column(row, "traceid", "trace_id")
        ts_raw = _pick_column(row, "timestamp")
        um = _pick_column(row, "um")
        dm = _pick_column(row, "dm")
        rpc = _pick_column(row, "rpctype", "rpc_type") or "unknown"
        if not um or not dm or um in {"NAN", "nan", "(?)", ""} or dm in {"NAN", "nan", "(?)", ""}:
            continue
        ts = int(float(ts_raw)) if ts_raw not in (None, "") else None
        if trace_id is not None and tid != trace_id:
            continue
        if timestamp is not None and ts != timestamp:
            continue
        if tid:
            trace_counts[tid] += 1
        if chosen_timestamp is None:
            chosen_timestamp = ts
        edges_counter[(um, dm, rpc)] += 1
        if sum(edges_counter.values()) >= max_edges * 4:
            break
    edges = [
        {
            "source": s,
            "target": t,
            "relationship": "CALLS",
            "communication": rpc,
            "weight": count,
        }
        for (s, t, rpc), count in edges_counter.most_common(max_edges)
    ]
    return edges, trace_counts, chosen_timestamp


def load_msresource_metrics(path: str | Path, service_ids: set[str], timestamp: int | None = None) -> dict[str, dict[str, float]]:
    by_service: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in _iter_text_rows(Path(path)):
        ms = _pick_column(row, "msname", "ms_name")
        ts_raw = _pick_column(row, "timestamp")
        if not ms or ms not in service_ids:
            continue
        ts = int(float(ts_raw)) if ts_raw not in (None, "") else None
        if timestamp is not None and ts != timestamp:
            continue
        cpu = _pick_column(row, "cpu_utilization")
        mem = _pick_column(row, "memory_utilization")
        if cpu not in (None, ""):
            by_service[ms]["cpu_percent"].append(float(cpu) * 100.0 if float(cpu) <= 1.0 else float(cpu))
        if mem not in (None, ""):
            by_service[ms]["memory_percent"].append(float(mem) * 100.0 if float(mem) <= 1.0 else float(mem))
    out: dict[str, dict[str, float]] = {}
    for ms, metrics in by_service.items():
        out[ms] = {k: sum(v) / len(v) for k, v in metrics.items() if v}
    return out


def load_mcr_rt_metrics(path: str | Path, service_ids: set[str], timestamp: int | None = None) -> dict[str, dict[str, float]]:
    by_service: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    for row in _iter_text_rows(Path(path)):
        ms = _pick_column(row, "msname", "ms_name")
        ts_raw = _pick_column(row, "timestamp")
        if not ms or ms not in service_ids:
            continue
        ts = int(float(ts_raw)) if ts_raw not in (None, "") else None
        if timestamp is not None and ts != timestamp:
            continue
        metric = _pick_column(row, "metrics", "metric")
        value_raw = _pick_column(row, "value")
        if not metric or value_raw in (None, ""):
            continue
        try:
            value = float(value_raw)
        except ValueError:
            continue
        key = metric.lower()
        if "rt" in key:
            by_service[ms]["latency_ms"].append(abs(value))
        elif "mcr" in key:
            by_service[ms]["request_rate"].append(max(0.0, value))
    out: dict[str, dict[str, float]] = {}
    for ms, metrics in by_service.items():
        out[ms] = {k: sum(v) / len(v) for k, v in metrics.items() if v}
    return out


def write_snapshot(snapshot: AlibabaGraphSnapshot, out_path: str | Path) -> None:
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(snapshot.to_json(), indent=2), encoding="utf-8")


def build_snapshot(root, **kwargs):
    from dataset.observed_trace import measured_snapshot
    return measured_snapshot(root, **kwargs)
