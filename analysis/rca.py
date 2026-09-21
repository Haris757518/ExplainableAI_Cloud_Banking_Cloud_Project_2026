from __future__ import annotations
import networkx as nx
from common.schema import AnalysisSample, RootCause

FEATURE_WEIGHTS = {
    "latency_ms": 0.28,
    "db_latency_ms": 0.34,
    "cpu_percent": 0.18,
    "memory_percent": 0.08,
    "error_rate": 0.08,
    "network_in_mbps": 0.02,
    "network_out_mbps": 0.02,
}


def _telemetry_abnormality(t) -> tuple[float, list[str]]:
    signals = {
        "latency_ms": min(t.latency_ms / 500.0, 2.0),
        "db_latency_ms": min(t.db_latency_ms / 500.0, 2.0),
        "cpu_percent": t.cpu_percent / 100.0,
        "memory_percent": t.memory_percent / 100.0,
        "error_rate": t.error_rate,
        "network_in_mbps": max(0.0, 1.0 - t.network_in_mbps / 50.0),
        "network_out_mbps": max(0.0, 1.0 - t.network_out_mbps / 50.0),
    }
    contributions = {k: v * FEATURE_WEIGHTS[k] for k, v in signals.items()}
    score = min(sum(contributions.values()), 1.0)
    evidence = [k for k, v in sorted(contributions.items(), key=lambda x: x[1], reverse=True) if v > 0.05][:3]
    return score, evidence


def rank_root_causes(sample: AnalysisSample, node_scores: dict[str, float]) -> list[RootCause]:
    g = nx.DiGraph()
    g.add_nodes_from([n.id for n in sample.nodes])
    g.add_edges_from([(e.source, e.target) for e in sample.edges])
    telem = {t.node_id: t for t in sample.telemetry}
    results = []
    for node in sample.nodes:
        abnormality, evidence = _telemetry_abnormality(telem[node.id])
        graph_score = float(node_scores.get(node.id, 0.0))
        downstream = len(nx.descendants(g, node.id))
        tx_relevance = 1.0 if node.id in {"payment-service", "ec2-01", "rds-01", "api-gateway"} else 0.5
        score = 0.5 * graph_score + 0.35 * abnormality + 0.10 * min(downstream / 4, 1) + 0.05 * tx_relevance
        reason = ", ".join(evidence) if evidence else "graph anomaly score"
        results.append(RootCause(node=node.id, score=round(score, 4), reason=f"elevated {reason}", evidence=evidence))
    results.sort(key=lambda x: x.score, reverse=True)
    return results[:3]
