from __future__ import annotations
from common.config import get_settings
from common.schema import AnalysisSample, AnalysisResult, Explanation, FeatureImportance
from ai_models.anomaly_engine import AIEngine
from ai_models.explain import explain
from analysis.rca import rank_root_causes
from analysis.counterfactual import evaluate_counterfactual
from cfao.policy import CFAOEngine, refine_policy_after_high_resolution

class AnalysisPipeline:
    def __init__(self):
        s=get_settings()
        self.engine=AIEngine(s.model_path, threshold=s.anomaly_threshold)
        self.cfao=CFAOEngine()

    def analyze(self, sample: AnalysisSample, source: str = "simulation", include_counterfactual: bool = True) -> AnalysisResult:
        if sample.source not in {'simulation', 'adaptive_high_resolution'}:
            from analysis.observed import analyze_observed
            if sample.source not in {'alibaba', 'alibaba_trace', 'alibaba_microservices_v2021', 'aws_cloudwatch'}:
                raise ValueError('Unsupported observed-data source.')
            period = sample.metadata.get('collection', {}).get('period_seconds', max(1, sample.metadata.get('window_ms',60000)//1000))
            result = analyze_observed(sample, period_seconds=period)
            from ai_models.observed_gnn import explain_observed_checkpoint
            gnn = explain_observed_checkpoint(sample)
            result.assessment['gnn_evidence']=gnn
            result.assessment['gnn_used']=gnn['status']=='evaluated'
            result.assessment['gnn_reason']=('A measured-data GNN provides held-out reconstruction evidence; temporal deviations still determine candidate ranking.' if gnn['status']=='evaluated' else gnn['reason']+' Synthetic-trained checkpoints remain excluded.')
            return result
        if not get_settings().enable_simulation:
            raise ValueError('Synthetic analysis is disabled. Use Alibaba or live AWS telemetry.')
        ai=self.engine.analyze(sample)
        roots=rank_root_causes(sample, ai["node_scores"]) if ai["is_anomaly"] else []
        explanation_raw=explain(self.engine, sample)
        selected_root=roots[0].node if roots else None
        frontier=self.cfao.build(sample, [selected_root] if selected_root else [], ai["is_anomaly"])
        counterfactual = evaluate_counterfactual(self.engine, sample, selected_root) if selected_root and include_counterfactual else None
        explanation=Explanation(
            important_features=[FeatureImportance(**x) for x in explanation_raw["important_features"]],
            important_nodes=explanation_raw["important_nodes"],
            dependency_path=self._dependency_path(sample, selected_root),
            narrative=self._narrative(sample, selected_root, explanation_raw["important_features"]),
        )
        return AnalysisResult(
            anomaly_score=ai["anomaly_score"],
            is_anomaly=ai["is_anomaly"],
            affected_nodes=ai["affected_nodes"],
            root_causes=roots,
            explanation=explanation,
            cfao=frontier,
            counterfactual=counterfactual,
            source=source,
            scenario=sample.scenario,
            transaction=sample.transaction,
            graph=sample,
            model_version=ai["model_version"],
        )

    def run_adaptive_refinement(self, sample: AnalysisSample) -> dict:
        if sample.source != 'simulation' or not get_settings().enable_simulation:
            raise ValueError('Synthetic refinement is disabled for observed telemetry.')
        first=self.analyze(sample, source=sample.source, include_counterfactual=True)
        if not first.is_anomaly or not first.cfao.causal_frontier:
            return {"before": first.model_dump(mode="json"), "after": first.model_dump(mode="json"), "telemetry_reduction_percent": 0.0}
        # Simulate a second, higher-resolution observation window concentrated on the frontier.
        from dataset.generator import generate_sample
        frontier=set(first.cfao.causal_frontier)
        second=generate_sample(first.scenario, seed=101, index=9, tx_type=first.transaction.type)
        for t in second.telemetry:
            if t.node_id in frontier:
                t.latency_ms *= 1.04
                t.db_latency_ms *= 1.04
            else:
                # Unrelated nodes remain at coarse resolution in the experiment; values are unchanged.
                pass
        after=self.analyze(second, source="adaptive_high_resolution", include_counterfactual=True)
        refined_cfao=refine_policy_after_high_resolution(first.cfao, first.anomaly_score, after.anomaly_score)
        return {
            "before": first.model_dump(mode="json"),
            "after": {**after.model_dump(mode="json"), "cfao": refined_cfao.model_dump(mode="json")},
            "telemetry_reduction_percent": first.cfao.telemetry_policy.estimated_high_resolution_reduction_percent,
            "frontier": list(frontier),
        }

    def _dependency_path(self, sample: AnalysisSample, root: str | None) -> list[str]:
        if not root: return []
        path=list(sample.transaction.path)
        if root in path:
            return path[:path.index(root)+1]
        return [root]

    def _narrative(self, sample: AnalysisSample, root: str | None, features: list[dict]) -> str:
        if not root:
            return "No anomaly was detected above the configured threshold."
        top=[x["feature"] for x in features[:3]]
        return (
            f"The {sample.transaction.type} transaction uses a graph path through "
            f"{' → '.join(sample.transaction.path)}. The model flagged the graph as anomalous; "
            f"{root} is the leading RCA candidate because it combines node anomaly evidence, "
            f"transaction-path relevance, and dependency propagation. Important signals include: {', '.join(top)}."
        )
