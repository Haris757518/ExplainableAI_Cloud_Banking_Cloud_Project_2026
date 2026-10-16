from __future__ import annotations
import networkx as nx
from common.schema import AnalysisSample, CFAOResult, TelemetryPolicy

class CFAOEngine:
    def evidence_frontier(self, candidates, maximum=3, transaction_path=()):
        """Bounded evidence requests; never claim unavailable source resolution."""
        selected=list(candidates[:maximum])
        requests=[]
        for candidate in selected:
            metrics=[e.metric.lower() for e in candidate.supporting_evidence]
            if any('connection' in m for m in metrics):diagnostic='Compare connection establishment, query time and measured pool occupancy.'
            elif any('latency' in m or 'query' in m for m in metrics):diagnostic='Collect available database waits, blocking sessions and caller/server timing.'
            elif any('cpu' in m for m in metrics):diagnostic='Compare CPU with actual request demand, process metrics and measured throttling.'
            elif any('mem' in m for m in metrics):diagnostic='Inspect measured memory trend, limits and workload before inferring a leak.'
            else:diagnostic='Verify metric semantics and collect available discriminating resource/error evidence.'
            requests.append({'resource':candidate.resource,'purpose':diagnostic,'missing':candidate.missing_evidence,'on_recorded_transaction_path':candidate.resource in transaction_path})
        return {'resources':[c.resource for c in selected],'requests':requests,'transaction_conditioning_available':bool(transaction_path),'selection_rule':'Highest evidence-ranked candidates, bounded budget; transaction context reported only when supplied from recorded/configured paths. No learned information-gain claim.','sampling_changed':False,'measured_cost_savings':None}

    def build(self, sample: AnalysisSample, root_nodes: list[str], is_anomaly: bool) -> CFAOResult:
        g = nx.DiGraph()
        g.add_nodes_from([n.id for n in sample.nodes])
        g.add_edges_from([(e.source, e.target) for e in sample.edges])
        frontier=[]
        if is_anomaly:
            for root in root_nodes[:2]:
                if root not in frontier: frontier.append(root)
                for pred in g.predecessors(root):
                    if pred not in frontier: frontier.append(pred)
                    for pred2 in g.predecessors(pred):
                        if pred2 not in frontier: frontier.append(pred2)
                for succ in g.successors(root):
                    if succ not in frontier: frontier.append(succ)
        policy={n.id:(5 if n.id in frontier else 60) for n in sample.nodes}
        if frontier:
            # Compare against the investigation baseline where every node is sampled every 5 seconds.
            # The adaptive policy keeps only the causal frontier at 5 seconds and all other nodes at 60 seconds.
            adaptive_rate=sum(1.0/p for p in policy.values())
            full_high_res_rate=len(policy) / 5.0
            estimated_reduction=max(0.0, 100.0 * (1.0 - adaptive_rate/full_high_res_rate))
        else:
            estimated_reduction=0.0
        return CFAOResult(
            causal_frontier=frontier,
            telemetry_policy=TelemetryPolicy(
                resolution_seconds=policy,
                baseline_resolution_seconds=60,
                focused_resolution_seconds=5,
                estimated_high_resolution_reduction_percent=round(estimated_reduction,2),
            ),
            trigger="anomaly_and_root_cause" if is_anomaly else "normal_baseline",
        )

def refine_policy_after_high_resolution(cfao: CFAOResult, score_before: float, score_after: float) -> CFAOResult:
    improved = max(0.0, score_after - score_before)
    data=dict(cfao.refinement)
    data.update({
        "score_before": round(score_before,4),
        "score_after": round(score_after,4),
        "refinement_delta": round(improved,4),
        "note": "Evidence delta from a second simulated telemetry window focused on the causal frontier."
    })
    return cfao.model_copy(update={"refinement": data})
