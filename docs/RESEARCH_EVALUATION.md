# Research Evaluation Plan

The final evaluation separates three data roles.

## Controlled banking experiments

Synthetic banking telemetry provides known anomaly and root-cause labels for reproducible experiments across multiple transaction-specific graph topologies.

## External benchmark

Alibaba Cluster Trace v2021 is an external microservice benchmark. It is not banking data and is never labeled as a banking transaction. The adapter uses `ALIBABA_BENCHMARK` only as a neutral compatibility context.

## AWS validation

AWS telemetry is a deployment validation source and is kept separate from controlled benchmark labels.

## Metrics

Anomaly detection: accuracy, precision, recall, F1.

Root-cause localization: Top-1 / Top-3 accuracy where labels are available.

Explainability: feature-ablation faithfulness proxy.

Counterfactual verification: anomaly-score reduction after a simulated intervention.

TC-CFAO: causal-frontier size, estimated observation reduction, and diagnosis consistency after focused re-analysis.

Temporal behavior: anomaly onset, peak, recovery, and topology-change steps.
