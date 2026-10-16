from __future__ import annotations
from pathlib import Path
import torch
from ai_models.gcn import BaselineGCN
from graph.builder import build_graph
from common.schema import AnalysisSample, AffectedNode

class AIEngine:
    def __init__(self, model_path: str | Path, threshold: float = 0.5, device: str = "cpu"):
        self.model_path=str(model_path); self.threshold=threshold; self.device=torch.device(device)
        self.model=BaselineGCN(); self.loaded=False; self.model_version="transaction-conditioned-gcn-v3"; self._load()
    def _load(self):
        path=Path(self.model_path)
        if path.exists():
            state=torch.load(path,map_location=self.device,weights_only=False)
            self.model.load_state_dict(state["model_state"]); self.threshold=float(state.get("threshold",self.threshold)); self.model_version=str(state.get("model_version",self.model_version)); self.loaded=True
        self.model.to(self.device); self.model.eval()
    def forward(self,sample:AnalysisSample):
        graph=build_graph(sample); x=graph.x.to(self.device); edges=graph.edge_index.to(self.device); weights=graph.edge_weight.to(self.device) if graph.edge_weight is not None else None
        return graph,self.model(x,edges,weights)
    def analyze(self,sample:AnalysisSample)->dict:
        graph,(graph_logit,node_logits)=self.forward(sample)
        with torch.no_grad(): graph_score=torch.sigmoid(graph_logit).item(); node_scores=torch.sigmoid(node_logits).cpu().tolist()
        affected=[AffectedNode(node=nid,score=float(score),node_type=graph.node_types[i]) for i,(nid,score) in enumerate(zip(graph.node_ids,node_scores))]
        affected.sort(key=lambda x:x.score,reverse=True)
        return {"anomaly_score":graph_score,"is_anomaly":graph_score>=self.threshold,"affected_nodes":[a.model_dump() for a in affected],"node_scores":dict(zip(graph.node_ids,node_scores)),"model_loaded":self.loaded,"model_version":self.model_version}
