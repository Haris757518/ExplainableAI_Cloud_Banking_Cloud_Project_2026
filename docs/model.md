# Baseline GNN Model

The baseline is a two-layer Graph Convolutional Network implemented in PyTorch so the project remains runnable without a special graph library. The adjacency matrix is normalized with self-loops. Node telemetry and transaction-context features are passed through graph convolutions, then a node-level binary classifier produces anomaly logits.

This baseline can later be replaced by PyTorch Geometric, GAT, GraphSAGE or a temporal GNN without changing the external `AIEngine.analyze()` interface.
