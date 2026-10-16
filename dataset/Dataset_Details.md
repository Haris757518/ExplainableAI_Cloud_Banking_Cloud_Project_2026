# Dataset Details

## Primary controlled dataset

The development dataset remains synthetic digital-banking cloud telemetry generated with a fixed graph and controlled anomaly scenarios. This provides reproducible labels for anomaly detection, RCA, counterfactual and TC-CFAO experiments.

Scenarios: NORMAL, CPU_SPIKE, DATABASE_LATENCY, SERVICE_OVERLOAD, NETWORK_DEGRADATION, CASCADING_FAILURE.

## External research benchmark

The project now supports the **Alibaba Cluster Trace — Microservices v2021**, a production-cluster microservice trace associated with the SoCC 2021 paper *Characterizing Microservice Dependency and Performance: Alibaba Trace Analysis*.

The Alibaba trace is used as a real cloud/microservice benchmark for graph topology and runtime performance. It is **not** banking telemetry and does not provide digital-banking anomaly labels. Controlled anomaly injection on a real trace can be used separately when labeled experiments are required.

See `docs/ALIBABA_TRACE_DATASET.md` and `references/alibaba_trace_2021.bib`.

AWS CloudWatch telemetry remains a third data source for later deployment validation and is normalized into the same internal telemetry concepts where the metrics are available.
