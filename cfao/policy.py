from __future__ import annotations
from collections import deque
import networkx as nx
from common.schema import AnalysisSample, CFAOResult, TelemetryPolicy

class CFAOEngine:
    def build(self, sample: AnalysisSample, root_nodes: list[str], is_anomaly: bool) -> CFAOResult:
        g = nx.DiGraph()
        g.add_nodes_from([n.id for n in sample.nodes])
        g.add_edges_from([(e.source, e.target) for e in sample.edges])
        frontier: list[str] = []
        if is_anomaly:
            for root in root_nodes[:2]:
                if root not in frontier: frontier.append(root)
                # Include the immediate service/resource neighborhood and one upstream hop.
                for pred in g.predecessors(root):
                    if pred not in frontier: frontier.append(pred)
                    for pred2 in g.predecessors(pred):
                        if pred2 not in frontier: frontier.append(pred2)
                for succ in g.successors(root):
                    if succ not in frontier: frontier.append(succ)
        policy = {n.id: (5 if n.id in frontier else 60) for n in sample.nodes}
        return CFAOResult(
            causal_frontier=frontier,
            telemetry_policy=TelemetryPolicy(resolution_seconds=policy),
            trigger="anomaly_and_root_cause" if is_anomaly else "normal_baseline"
        )
