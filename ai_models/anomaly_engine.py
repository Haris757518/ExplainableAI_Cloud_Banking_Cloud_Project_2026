from __future__ import annotations
from pathlib import Path
import torch
from ai_models.gcn import BaselineGCN
from graph.builder import build_graph
from common.schema import AnalysisSample, AffectedNode

class AIEngine:
    def __init__(self, model_path: str | Path, threshold: float = 0.5, device: str = "cpu"):
        self.model_path = str(model_path)
        self.threshold = threshold
        self.device = torch.device(device)
        self.model = BaselineGCN()
        self.loaded = False
        self._load()

    def _load(self):
        path = Path(self.model_path)
        if path.exists():
            state = torch.load(path, map_location=self.device, weights_only=True)
            self.model.load_state_dict(state["model_state"])
            self.threshold = float(state.get("threshold", self.threshold))
            self.loaded = True
        self.model.to(self.device)
        self.model.eval()

    def analyze(self, sample: AnalysisSample) -> dict:
        graph = build_graph(sample)
        x = graph.x.to(self.device)
        edges = graph.edge_index.to(self.device)
        with torch.no_grad():
            graph_logit, node_logits = self.model(x, edges)
            graph_score = torch.sigmoid(graph_logit).item()
            node_scores = torch.sigmoid(node_logits).cpu().tolist()
        affected = [AffectedNode(node=nid, score=float(score), node_type=graph.node_types[i]) for i, (nid, score) in enumerate(zip(graph.node_ids, node_scores))]
        affected.sort(key=lambda x: x.score, reverse=True)
        return {
            "anomaly_score": graph_score,
            "is_anomaly": graph_score >= self.threshold,
            "affected_nodes": [a.model_dump() for a in affected],
            "node_scores": dict(zip(graph.node_ids, node_scores)),
            "model_loaded": self.loaded,
        }
