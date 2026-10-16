from __future__ import annotations
import networkx as nx
from common.schema import AnalysisSample


def telemetry_only_anomaly(sample: AnalysisSample, threshold: float = 0.75) -> tuple[float, bool]:
    scores=[]
    for t in sample.telemetry:
        values=[t.cpu_percent/100.0,t.memory_percent/100.0,min(t.latency_ms/500.0,1.0),min(t.db_latency_ms/500.0,1.0),min(t.error_rate/0.20,1.0)]
        scores.append(max(values))
    score=max(scores,default=0.0)
    return score,score>=threshold


def telemetry_only_rca(sample: AnalysisSample, top_k:int=3)->list[str]:
    scored=[]
    for t in sample.telemetry:
        score=max(t.cpu_percent/100.0,t.memory_percent/100.0,min(t.latency_ms/1000.0,1.0),min(t.db_latency_ms/1000.0,1.0),min(t.error_rate/0.30,1.0))
        scored.append((score,t.node_id))
    return [n for _,n in sorted(scored,reverse=True)[:top_k]]


def graph_centrality_rca(sample: AnalysisSample, top_k:int=3)->list[str]:
    g=nx.DiGraph(); g.add_nodes_from(n.id for n in sample.nodes); g.add_edges_from((e.source,e.target) for e in sample.edges)
    centrality=nx.betweenness_centrality(g,normalized=True)
    relevance={n.id:(1.0 if n.id in sample.transaction.path else 0.1) for n in sample.nodes}
    scores=[(centrality.get(n,0.0)*relevance.get(n,0.1),n) for n in g.nodes]
    return [n for _,n in sorted(scores,reverse=True)[:top_k]]
