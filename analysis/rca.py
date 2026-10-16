from __future__ import annotations
import networkx as nx
from common.schema import AnalysisSample, RootCause

FEATURE_WEIGHTS = {
    "latency_ms": 0.26,
    "db_latency_ms": 0.30,
    "cpu_percent": 0.18,
    "memory_percent": 0.08,
    "error_rate": 0.10,
    "network_in_mbps": 0.04,
    "network_out_mbps": 0.04,
}

def _telemetry_abnormality(t) -> tuple[float, list[str]]:
    signals = {
        "latency_ms": min(t.latency_ms / 500.0, 2.0),
        "db_latency_ms": min(t.db_latency_ms / 500.0, 2.0),
        "cpu_percent": t.cpu_percent / 100.0,
        "memory_percent": t.memory_percent / 100.0,
        "error_rate": min(t.error_rate / 0.20, 2.0),
        "network_in_mbps": max(0.0, 1.0 - t.network_in_mbps / 50.0),
        "network_out_mbps": max(0.0, 1.0 - t.network_out_mbps / 50.0),
    }
    contributions = {k: v * FEATURE_WEIGHTS[k] for k, v in signals.items()}
    score = min(sum(contributions.values()), 1.0)
    evidence = [k for k, v in sorted(contributions.items(), key=lambda x: x[1], reverse=True) if v > 0.05][:4]
    return score, evidence

def rank_root_causes(sample: AnalysisSample, node_scores: dict[str, float], top_k: int = 3) -> list[RootCause]:
    g = nx.DiGraph()
    g.add_nodes_from([n.id for n in sample.nodes])
    g.add_edges_from([(e.source, e.target) for e in sample.edges])
    telem = {t.node_id: t for t in sample.telemetry}
    path_nodes = set(sample.transaction.path)
    results = []
    for node in sample.nodes:
        abnormality, evidence = _telemetry_abnormality(telem[node.id])
        graph_score = float(node_scores.get(node.id, 0.0))
        downstream = len(nx.descendants(g, node.id))
        upstream = len(nx.ancestors(g, node.id))
        
        if node.id in path_nodes:
            tx_relevance = 1.0
        else:
            connected = any(g.has_edge(node.id, p) or g.has_edge(p, node.id) for p in path_nodes)
            tx_relevance = 0.5 if connected else 0.0
            
        # A node near the transaction path, with strong telemetry evidence and
        # downstream propagation, ranks higher than an isolated abnormal metric.
        propagation = min((downstream + upstream) / 6.0, 1.0)
        score = (
            0.50 * graph_score
            + 0.27 * abnormality
            + 0.13 * tx_relevance
            + 0.10 * propagation
        )
        reason = ", ".join(evidence) if evidence else "graph anomaly score"
        
        path_class = "ACTIVE" if tx_relevance == 1.0 else "SECONDARY" if tx_relevance == 0.5 else "UNRELATED"
        
        results.append(RootCause(
            node=node.id,
            score=round(score, 4),
            reason=f"elevated {reason}",
            evidence=evidence,
            transaction_relevance=round(tx_relevance, 3),
            graph_propagation=round(propagation, 3),
            path_classification=path_class
        ))
    results.sort(key=lambda x: x.score, reverse=True)
    return results[:top_k]
