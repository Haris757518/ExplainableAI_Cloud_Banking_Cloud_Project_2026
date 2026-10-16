# GNN Models

## Baseline GCN

The baseline is a two-layer Graph Convolutional Network implemented with native PyTorch matrix operations. It consumes normalized graph adjacency plus node telemetry/transaction-context features and produces graph-level and node-level anomaly logits.

The model input contains 20 features, including telemetry, transaction type flags, resource type flags, transaction-path relevance, path depth, and simple temporal position features.

The project includes an optional `graph.builder.to_pyg_data()` adapter and `requirements-optional-pyg.txt` for environments where PyTorch Geometric is available. The main baseline does not require PyG so that the review demo remains easy to run on Windows.

## Temporal GCN

`ai_models.gcn.TemporalGCN` applies the same GCN encoder across graph snapshots and feeds the sequence of graph embeddings through a GRU. It is a small experimental temporal extension, not yet the final research model.

## Upgrade path

The external inference contract remains:

```python
result = ai_engine.analyze(graph_data)
```

This allows a future GAT, GraphSAGE, TGNN, or more advanced temporal model to replace the baseline without changing the backend/API contract.
