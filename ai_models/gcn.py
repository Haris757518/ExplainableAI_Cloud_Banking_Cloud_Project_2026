from __future__ import annotations
import torch
from torch import nn
import torch.nn.functional as F
from graph.builder import normalized_adjacency

class GraphConvolution(nn.Module):
    def __init__(self, in_features: int, out_features: int):
        super().__init__()
        self.linear = nn.Linear(in_features, out_features)

    def forward(self, x: torch.Tensor, adjacency: torch.Tensor) -> torch.Tensor:
        return adjacency @ self.linear(x)

class BaselineGCN(nn.Module):
    def __init__(self, in_features: int = 16, hidden: int = 32):
        super().__init__()
        self.gcn1 = GraphConvolution(in_features, hidden)
        self.gcn2 = GraphConvolution(hidden, hidden)
        self.node_head = nn.Linear(hidden, 1)

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor) -> tuple[torch.Tensor, torch.Tensor]:
        adj = normalized_adjacency(edge_index, x.size(0)).to(x.device)
        h = F.relu(self.gcn1(x, adj))
        h = F.dropout(h, p=0.1, training=self.training)
        h = F.relu(self.gcn2(h, adj))
        node_logits = self.node_head(h).squeeze(-1)
        graph_logit = node_logits.max()
        return graph_logit, node_logits
