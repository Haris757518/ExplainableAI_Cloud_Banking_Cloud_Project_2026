# Current limitations

- Alibaba is measured production microservice telemetry, not banking/AWS telemetry; it has no incident or fault-location ground truth.
- Current reports use a bounded prefix and limited topology, with potential incomplete bins and selection bias. Multiple independent slices remain necessary.
- Median/MAD deviations and graph-autoencoder reconstruction are diagnostic signals, not calibrated failure probabilities or causal proof.
- The measured-data GNN supplies additional reconstruction evidence on its exact held-out trace slice. It is not a validated fault classifier and does not override temporal candidate ranking or transfer to AWS.
- No fabricated counterfactual telemetry or artificial anomaly injection is used in the observed workflow. Historical synthetic modules remain explicitly separate.
- Live EC2 telemetry, local PostgreSQL system views and custom probe metric publication were verified after refreshing credentials. Metrics describe measured lab health probes, not production banking workloads. No RDS instance exists in the configured region.
- Native collection does not change sampling resolution. Proposed query reductions are not measured cost savings.
- PostgreSQL cause discrimination requires a monitoring connection and permissions. Analytics-store health is independent of application-database health.
