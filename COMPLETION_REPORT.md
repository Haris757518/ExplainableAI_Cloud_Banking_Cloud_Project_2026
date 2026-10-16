# Implementation and live verification — 16 October 2026

Main: `D:\ExplainableAI_Cloud_Banking_Cloud_Project_2026_RESEARCH_V1\ExplainableAI_Cloud_Banking_Cloud_Project_2026`.

Seven previous project versions and pre-change file backups are under `D:\ExplainableAI_Project_Archived_Versions_2026_10_16`. Existing uncommitted work was preserved. GitHub commit history records publication of the implementation. Raw AWS operational snapshots remain local.

## Working and verified

- Main-project regression suite: **36 passed**. Tests now use an isolated database; identified fixture records were removed from the observed store after backup.
- Dashboard production build passed and FastAPI serves it at http://127.0.0.1:8000 . HTTP endpoint checks passed. Automated visual browser inspection was unavailable because the browser-control helper failed to initialize; no visual QA claim is made.
- Real Alibaba trace: 100,000 source rows, 77,375 deduplicated measured calls, 40 selected nodes, 80 selected dependencies. No artificial banking labels, fault labels, or missing-value defaults are introduced.
- Measured-data graph autoencoder: 36 chronological training, 12 validation, 12 held-out windows, 489 held-out measured targets. Test masked MSE **0.549566**, training-mean baseline MSE **1.041678**. These are reconstruction errors, not classification or root-cause accuracy. The topology is transductive and selected from the full bounded slice; additional independent slices are needed for generalization claims.
- Runtime Alibaba GNN explanation verified on its documented held-out slice. AWS inference abstains from using those domain-specific weights.
- AWS credentials refreshed and live access verified in us-east-1. The account has one running EC2 server, Banking-Payment-Server, with self-hosted PostgreSQL; no RDS instance was discovered.
- Configured an isolated `xai_observability` database, least-privilege `xaiobserver` database/OS role, and local-only `explainableai-observer` service on that EC2 host. No fake customers or banking transactions are created.
- The service performs actual SELECT 1 health probes every minute, records measured timings, and publishes six custom metrics to `ExplainableAI/ObservedLab`. Along with native EC2 telemetry, the final check returned **nine observed metrics** and **five eligible temporal series**.
- SSM PostgreSQL wait/activity/blocking diagnostics and local snapshot persistence passed end to end.
- Synthetic analysis/refinement endpoints return 403 by default. Observed analysis has no fabricated counterfactual intervention, fake 5-second AWS sampling, or claimed measured cost savings.

## Actual latency findings

Before configuration, PostgreSQL was running but the host had no HTTP application listener and the analytics system was only looking for RDS metrics. That was a monitoring/deployment gap, not proof of a database performance fault.

The final saved observation measured approximately **4.106 ms** of lab probe execution, **0.384 ms** of database query time, and **0 blocked PostgreSQL sessions**. The query-time signal deviated from its short-window reference median of approximately 0.256 ms; the system reports that relative deviation without calling it a confirmed fault. Local analytics-store dashboard queries measured approximately **0.406 ms** for the current small dataset. These observations do not establish production banking performance or rule out intermittent problems.

Database I/O timing was off in the collected PostgreSQL snapshot. Zero I/O-time counters therefore do not prove zero disk latency. The probe execution timer excludes metric publishing and audit logging; connection, query, and database round-trip timings are recorded separately.

## Evidence and reproducibility

- `results/observed/live_validation.json`: real HTTP/AWS endpoint verification and actual database snapshot.
- `results/observed/report.json`: trace archive hash, selection details, model study and limitations.
- `results/observed/aws_lab_setup.json`: successful AWS service/database setup and first measured probe.
- `scripts/verify_live.py`: repeat the actual trace/GNN/AWS/database verification while the local server is running.
- `scripts/configure_aws_lab.py`: reproduce the isolated AWS host setup after a lab reset.
- `docs/REAL_DATA_IMPLEMENTATION.md`: method, source references, configuration, scope and evaluation plan.

Run `scripts/start_observed.ps1` from PowerShell to start the local dashboard. In the dashboard choose Alibaba or AWS, then Analyze observed data. AWS mode also exposes Inspect PostgreSQL on EC2 and evidence recollection when a candidate frontier exists.

## Research limits and operations

TC-CFAO now uses evidence-constrained frontier selection and explicit requests for distinguishing database waits, connection delays, query execution and application overhead. It remains a proposed research contribution. Scientific novelty, causal correctness, incident accuracy, scalability and cost improvement require evaluation; a perfect or production-ready project is not claimed.

Alibaba is measured production microservice data, not banking data. The AWS service is a measured lab probe, not a deployed banking application. Real failure-label accuracy remains unmeasured. Historical synthetic scripts/checkpoints/results are preserved separately and excluded from current observed-data conclusions.

CloudWatch custom-metric charges can apply. To stop new probe publication on EC2, run `sudo systemctl disable --now explainableai-observer`; this preserves the isolated database and recorded measurements. AWS Academy session expiry still requires refreshing credentials locally.
