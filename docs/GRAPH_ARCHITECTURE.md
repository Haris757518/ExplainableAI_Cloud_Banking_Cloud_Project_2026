# Graph Architecture

The research system treats cloud performance as a collection of transaction-conditioned graphs rather than one fixed topology.

## 1. Transaction-specific graphs

Supported controlled banking workflows are modeled with different service paths:

- UPI_PAYMENT: API → Payment Service → EC2 → Database (+ cache)
- FUND_TRANSFER: API → Transfer Service → EC2 → Database, with Account Service dependency
- CARD_PAYMENT: API → Card Service → EC2 → Database, with Risk and Notification branches
- BALANCE_INQUIRY: API → Account Service → EC2 → Database (+ cache)
- BILL_PAYMENT: API → Bill Service → EC2 → Database → Notification path

The graphs share infrastructure where appropriate but do not force every transaction through one topology.

## 2. Transaction-conditioned message passing

Node features contain a one-hot transaction context and path relevance. The graph builder also assigns stronger message-passing weights to edges on the active transaction path and lower weights to unrelated dependencies.

## 3. Temporal graph sequence

A temporal sample is represented as:

`G(t1) → G(t2) → … → G(tn)`

Each snapshot has telemetry and topology. Controlled sequences can include a temporary dependency change, allowing the temporal model to observe both metric drift and topology drift.

## 4. Canonical interface

`graph.builder.build_graph(sample)` remains compatible with the existing GNN. `graph.temporal.build_temporal_graph(samples)` creates a sequence of graph objects for temporal learning. Alibaba snapshots convert to the same `AnalysisSample` schema, and AWS uses the same canonical path through its adapter.

## 5. Why the graph is central

The graph is the bridge between transaction context and infrastructure behavior. RCA uses graph propagation and transaction-path relevance; TC-CFAO uses the suspected frontier to restrict high-resolution observation.
