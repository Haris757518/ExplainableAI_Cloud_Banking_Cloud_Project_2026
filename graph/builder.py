from __future__ import annotations
import numpy as np
import torch
from common.schema import AnalysisSample
from common.features import node_feature_matrix

class GraphData:
    def __init__(self, x: torch.Tensor, edge_index: torch.Tensor, node_ids: list[str], node_types: list[str], node_labels: torch.Tensor | None = None):
        self.x = x
        self.edge_index = edge_index
        self.node_ids = node_ids
        self.node_types = node_types
        self.node_labels = node_labels


def build_graph(sample: AnalysisSample) -> GraphData:
    x_np, _ = node_feature_matrix(sample)
    node_ids = [n.id for n in sample.nodes]
    index = {node_id: i for i, node_id in enumerate(node_ids)}
    edges = []
    for edge in sample.edges:
        s, t = index[edge.source], index[edge.target]
        edges.append((s, t)); edges.append((t, s))
    # self loops are added inside the GCN as well, but explicit edge_index keeps the topology reusable.
    edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()
    labels = torch.tensor([sample.node_labels.get(i, 0) for i in node_ids], dtype=torch.float32)
    return GraphData(torch.from_numpy(x_np), edge_index, node_ids, [n.type for n in sample.nodes], labels)


def normalized_adjacency(edge_index: torch.Tensor, num_nodes: int) -> torch.Tensor:
    a = torch.zeros((num_nodes, num_nodes), dtype=torch.float32)
    if edge_index.numel():
        a[edge_index[0], edge_index[1]] = 1.0
    a += torch.eye(num_nodes)
    degree = a.sum(dim=1)
    inv_sqrt = torch.pow(degree.clamp(min=1.0), -0.5)
    return inv_sqrt[:, None] * a * inv_sqrt[None, :]
