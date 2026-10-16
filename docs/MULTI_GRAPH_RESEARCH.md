# Multi-Graph and Temporal Research Design

## Motivation

A single fixed infrastructure topology is insufficient for a transaction-conditioned performance model. The research build therefore creates a collection of workflow-specific graphs and temporal graph sequences.

## Transaction graph family

Each supported transaction type selects a distinct service path and dependency structure. Some infrastructure nodes are shared, while service and compute nodes may differ.

| Transaction | Main path | Topology characteristics |
|---|---|---|
| UPI_PAYMENT | API → Payment → EC2 → DB | cache dependency |
| FUND_TRANSFER | API → Transfer → EC2 → DB | Account Service + second compute node |
| CARD_PAYMENT | API → Card → EC2 → DB | Risk Service + queue/notification |
| BALANCE_INQUIRY | API → Account → EC2 → DB | cache dependency |
| BILL_PAYMENT | API → Bill → EC2 → DB → Queue → Notification | asynchronous notification path |

## Temporal graph sequence

Each sequence is represented as `G(t1) ... G(tn)`. Controlled experiments contain normal, degradation/anomaly, and recovery phases. A temporary fallback dependency can be introduced during the anomaly window so that the sequence can contain both telemetry drift and topology drift.

## Transaction conditioning

The 20-dimensional node representation contains transaction one-hot flags, transaction-path relevance, and path depth. Graph edges on the active transaction path receive stronger message-passing weights than unrelated dependencies.

## Model

The baseline model remains a lightweight two-layer GCN. The temporal model pools each snapshot embedding, computes a temporal delta against the previous snapshot, and sends the sequence through a GRU before graph-level classification.

This keeps the existing `build_graph(sample)` interface while adding a first-class temporal representation through `graph.temporal.build_temporal_graph(samples)`.
