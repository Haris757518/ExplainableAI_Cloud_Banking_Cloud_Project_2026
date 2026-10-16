from __future__ import annotations
import torch
from common.schema import AnalysisSample
from common.features import node_feature_matrix


class GraphData:
    def __init__(
        self,
        x: torch.Tensor,
        edge_index: torch.Tensor,
        node_ids: list[str],
        node_types: list[str],
        node_labels: torch.Tensor | None = None,
        edge_weight: torch.Tensor | None = None,
        edge_relationships: list[str] | None = None,
    ):
        self.x = x
        self.edge_index = edge_index
        self.node_ids = node_ids
        self.node_types = node_types
        self.node_labels = node_labels
        self.edge_weight = edge_weight
        self.edge_relationships = edge_relationships or []


def build_graph(sample: AnalysisSample) -> GraphData:
    x_np, _ = node_feature_matrix(sample)
    node_ids = [n.id for n in sample.nodes]
    index = {node_id: i for i, node_id in enumerate(node_ids)}
    tx_path = sample.transaction.path
    path_edges = {(tx_path[i], tx_path[i + 1]) for i in range(len(tx_path) - 1)}
    edges: list[tuple[int, int]] = []
    weights: list[float] = []
    relationships: list[str] = []
    for edge in sample.edges:
        s, t = index[edge.source], index[edge.target]
        # Transaction-conditioned message passing: edges on the active transaction
        # path receive stronger weight, while unrelated dependencies are down-weighted.
        w = 2.0 if (edge.source, edge.target) in path_edges else 0.75
        edges.append((s, t)); weights.append(w); relationships.append(edge.relationship)
        edges.append((t, s)); weights.append(w); relationships.append(edge.relationship)
    if edges:
        edge_index = torch.tensor(edges, dtype=torch.long).t().contiguous()
        edge_weight = torch.tensor(weights, dtype=torch.float32)
    else:
        edge_index = torch.empty((2, 0), dtype=torch.long)
        edge_weight = torch.empty((0,), dtype=torch.float32)
    labels = torch.tensor([sample.node_labels.get(i, 0) for i in node_ids], dtype=torch.float32)
    return GraphData(
        torch.from_numpy(x_np), edge_index, node_ids,
        [n.type for n in sample.nodes], labels, edge_weight, relationships
    )


def normalized_adjacency(
    edge_index: torch.Tensor,
    num_nodes: int,
    edge_weight: torch.Tensor | None = None,
) -> torch.Tensor:
    a = torch.zeros((num_nodes, num_nodes), dtype=torch.float32, device=edge_index.device)
    if edge_index.numel():
        weights = edge_weight if edge_weight is not None else torch.ones(edge_index.size(1), device=edge_index.device)
        a[edge_index[0], edge_index[1]] = weights
    a += torch.eye(num_nodes, dtype=torch.float32, device=edge_index.device)
    degree = a.sum(dim=1)
    inv_sqrt = torch.pow(degree.clamp(min=1.0), -0.5)
    return inv_sqrt[:, None] * a * inv_sqrt[None, :]
