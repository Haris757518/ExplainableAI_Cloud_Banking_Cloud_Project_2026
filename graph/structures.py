from __future__ import annotations
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Iterable

from common.schema import AnalysisSample, GraphEdge, GraphNode, TelemetryPoint


@dataclass(frozen=True)
class GraphSnapshot:
    """One time-indexed business/infrastructure graph snapshot."""
    snapshot_id: str
    timestamp: str
    transaction_type: str
    nodes: tuple[GraphNode, ...]
    edges: tuple[GraphEdge, ...]
    telemetry: tuple[TelemetryPoint, ...]
    source: str = "simulation"
    metadata: dict = field(default_factory=dict)

    @classmethod
    def from_sample(cls, sample: AnalysisSample) -> "GraphSnapshot":
        timestamp = min((t.timestamp for t in sample.telemetry), default=None)
        return cls(
            snapshot_id=f"{sample.transaction.id}:t{sample.sequence_index}",
            timestamp=timestamp.isoformat() if timestamp else "",
            transaction_type=sample.transaction.type,
            nodes=tuple(sample.nodes),
            edges=tuple(sample.edges),
            telemetry=tuple(sample.telemetry),
            source=sample.source,
            metadata=dict(sample.metadata),
        )

    @property
    def topology_signature(self) -> str:
        return topology_signature(self.nodes, self.edges)


@dataclass(frozen=True)
class GraphSequence:
    snapshots: tuple[GraphSnapshot, ...]
    transaction_type: str

    @property
    def length(self) -> int:
        return len(self.snapshots)

    @property
    def topology_signatures(self) -> list[str]:
        return [s.topology_signature for s in self.snapshots]

    @property
    def changed_topology_steps(self) -> list[int]:
        sigs = self.topology_signatures
        return [i for i in range(1, len(sigs)) if sigs[i] != sigs[i - 1]]

    @classmethod
    def from_samples(cls, samples: Iterable[AnalysisSample]) -> "GraphSequence":
        samples = list(samples)
        if not samples:
            raise ValueError("GraphSequence requires at least one snapshot")
        tx = samples[0].transaction.type
        if any(s.transaction.type != tx for s in samples):
            raise ValueError("All snapshots in a GraphSequence must share transaction type")
        return cls(tuple(GraphSnapshot.from_sample(s) for s in samples), tx)


@dataclass(frozen=True)
class GraphCollection:
    graphs: tuple[AnalysisSample, ...]

    @property
    def transaction_types(self) -> list[str]:
        return sorted({g.transaction.type for g in self.graphs})

    @property
    def topology_count(self) -> int:
        return len({topology_signature(g.nodes, g.edges) for g in self.graphs})


def topology_signature(nodes: Iterable[GraphNode], edges: Iterable[GraphEdge]) -> str:
    node_part = ";".join(sorted(f"{n.id}:{n.type}:{n.layer}" for n in nodes))
    edge_part = ";".join(sorted(f"{e.source}>{e.target}:{e.relationship}" for e in edges))
    raw = f"{node_part}|{edge_part}".encode("utf-8")
    return sha256(raw).hexdigest()[:16]
