# Current implementation status — 16 October 2026

Current specification: [Observed data implementation](REAL_DATA_IMPLEMENTATION.md).

Implemented: bounded measured-trace ingestion, missing-value preservation, chronological deviation diagnosis, explanation and evidence frontier, real-data graph-autoencoder study with chronological holdout and baseline, read-only batched/paginated CloudWatch collection, explicit AWS topology mapping, focused evidence recollection, independent analytics-store timing, optional PostgreSQL waits/blocking diagnostics, observed-results persistence, and a real-data dashboard served by FastAPI.

Measured Alibaba study: 100,000 source rows, 77,375 usable deduplicated calls, 40 selected nodes, 80 selected dependencies. At five-second aggregation: 36 training, 12 validation and 12 held-out windows; 489 held-out measured targets. Source archive SHA-256 and exact output metrics are in results/observed/report.json. This is a bounded prefix, not a representative full-dataset evaluation. Failure-label accuracy and causal accuracy are unmeasured.

Live AWS access was verified after refreshing the lab session. One running EC2 server and self-hosted PostgreSQL were observed; no RDS instance is present. An isolated xai_observability database and observed-lab-probe service were configured on the existing EC2 host. It publishes measured execution, DB connection, DB query, DB round-trip, request-count and error-count metrics to ExplainableAI/ObservedLab. These are real lab probe measurements, not production banking transactions. The first verified probe published successfully. Read-only PostgreSQL system-view snapshots are available through the SSM endpoint.

The previous synthetic accuracy figures are historical and do not apply to this implementation. No synthetic-trained GNN is used for observed-data inference. Existing simulation tests may explicitly opt in for legacy regression coverage.
