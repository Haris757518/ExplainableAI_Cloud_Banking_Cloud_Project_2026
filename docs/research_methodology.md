# Research Methodology

Baseline hypothesis: cloud-performance anomalies can be localized more usefully when telemetry is represented as a dependency graph instead of independent rows.

Evaluation layers:
- graph-level anomaly detection
- node-level affected-component detection
- root-cause ranking
- explanation quality
- telemetry focus through TC-CFAO

The current implementation is a baseline system. Stronger causal verification, counterfactual intervention and real adaptive telemetry control are intentionally left as later research extensions.
