from __future__ import annotations
import json
from common.config import get_settings
from common.schema import AnalysisSample, AnalysisResult, Explanation, FeatureImportance
from ai_models.anomaly_engine import AIEngine
from ai_models.explain import explain
from analysis.rca import rank_root_causes
from cfao.policy import CFAOEngine

class AnalysisPipeline:
    def __init__(self):
        s=get_settings()
        self.engine=AIEngine(s.model_path, threshold=s.anomaly_threshold)
        self.cfao=CFAOEngine()

    def analyze(self, sample: AnalysisSample, source: str = "simulation") -> AnalysisResult:
        ai=self.engine.analyze(sample)
        roots=rank_root_causes(sample, ai["node_scores"]) if ai["is_anomaly"] else []
        explanation_raw=explain(self.engine, sample)
        selected_root_nodes=[r.node for r in roots[:1]]
        cfao=self.cfao.build(sample, selected_root_nodes, ai["is_anomaly"])
        explanation=Explanation(
            important_features=[FeatureImportance(**x) for x in explanation_raw["important_features"]],
            important_nodes=explanation_raw["important_nodes"],
            dependency_path=self._dependency_path(sample, selected_root_nodes[0] if selected_root_nodes else None)
        )
        return AnalysisResult(
            anomaly_score=ai["anomaly_score"], is_anomaly=ai["is_anomaly"], affected_nodes=ai["affected_nodes"],
            root_causes=roots, explanation=explanation, cfao=cfao, source=source,
            scenario=sample.scenario, transaction=sample.transaction, graph=sample
        )

    def _dependency_path(self, sample: AnalysisSample, root: str | None) -> list[str]:
        if not root: return []
        names={n.id:n.label for n in sample.nodes}
        # Prefer the business-to-resource path for easy demo explanation.
        preferred=["api-gateway","payment-service","ec2-01","rds-01"]
        if root in preferred:
            i=preferred.index(root)
            return preferred[:i+1]
        return [root]
