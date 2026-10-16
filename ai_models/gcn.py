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
        h = self.linear(x)
        if h.ndim == 3 and adjacency.ndim == 2:
            adjacency = adjacency.unsqueeze(0)
        return torch.matmul(adjacency, h)


class BaselineGCN(nn.Module):
    def __init__(self, in_features: int = 20, hidden: int = 48):
        super().__init__()
        self.in_features = in_features
        self.hidden = hidden
        self.gcn1 = GraphConvolution(in_features, hidden)
        self.gcn2 = GraphConvolution(hidden, hidden)
        self.node_head = nn.Linear(hidden, 1)
        self.graph_head = nn.Linear(hidden, 1)

    def encode(self, x: torch.Tensor, edge_index: torch.Tensor, edge_weight: torch.Tensor | None = None) -> torch.Tensor:
        adj = normalized_adjacency(edge_index, x.size(-2), edge_weight=edge_weight).to(x.device)
        h = F.relu(self.gcn1(x, adj))
        h = F.dropout(h, p=0.1, training=self.training)
        h = F.relu(self.gcn2(h, adj))
        return h

    def forward(self, x: torch.Tensor, edge_index: torch.Tensor, edge_weight: torch.Tensor | None = None) -> tuple[torch.Tensor, torch.Tensor]:
        h = self.encode(x, edge_index, edge_weight)
        node_logits = self.node_head(h).squeeze(-1)
        graph_embedding = h.mean(dim=1) if h.ndim == 3 else h.mean(dim=0)
        graph_logit = self.graph_head(graph_embedding).squeeze(-1)
        return graph_logit, node_logits


class TemporalGCN(nn.Module):
    """Temporal graph model: transaction-conditioned GCN snapshots + delta-aware GRU."""
    def __init__(self, in_features: int = 20, hidden: int = 48, temporal_hidden: int = 40):
        super().__init__()
        self.gcn = BaselineGCN(in_features=in_features, hidden=hidden)
        self.gru = nn.GRU(hidden * 2, temporal_hidden, batch_first=True)
        self.head = nn.Linear(temporal_hidden, 1)

    def forward(self, graphs) -> torch.Tensor:
        embeddings = []
        previous = None
        for graph in graphs:
            if hasattr(graph, "x"):
                x, edge_index, edge_weight = graph.x, graph.edge_index, graph.edge_weight
            else:
                x, edge_index, edge_weight = graph
            h = self.gcn.encode(x, edge_index, edge_weight)
            pooled = h.mean(dim=0)
            delta = torch.zeros_like(pooled) if previous is None else pooled - previous
            embeddings.append(torch.cat([pooled, delta], dim=-1))
            previous = pooled
        sequence = torch.stack(embeddings, dim=0).unsqueeze(0)
        out, _ = self.gru(sequence)
        return self.head(out[:, -1]).squeeze(-1)
