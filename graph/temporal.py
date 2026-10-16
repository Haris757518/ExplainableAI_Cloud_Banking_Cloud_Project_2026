from __future__ import annotations
from dataclasses import dataclass
from typing import Iterable
from common.schema import AnalysisSample
from graph.builder import GraphData, build_graph
from graph.structures import GraphSequence

@dataclass(frozen=True)
class TemporalGraphData:
    sequence: GraphSequence
    graphs: tuple[GraphData, ...]
    @property
    def length(self): return len(self.graphs)
    @property
    def topology_change_steps(self): return self.sequence.changed_topology_steps


def build_temporal_graph(samples: Iterable[AnalysisSample]) -> TemporalGraphData:
    samples=list(samples)
    seq=GraphSequence.from_samples(samples)
    return TemporalGraphData(seq,tuple(build_graph(s) for s in samples))
