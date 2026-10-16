# Main project: observed-data implementation

The main working directory is `D:\ExplainableAI_Cloud_Banking_Cloud_Project_2026_RESEARCH_V1\ExplainableAI_Cloud_Banking_Cloud_Project_2026`. Seven older versions are under `D:\ExplainableAI_Project_Archived_Versions_2026_10_16`.

## Data decision

Keep the already downloaded Alibaba Microservices v2021 trace as a production microservice source. Its call table contains actual response times and explicitly marks DB/cache protocols. It has no banking identities or verified fault/root-cause labels. It is neither AWS telemetry nor a complete substitute for an AWS deployment. Missing measurements remain null; no transaction label or normal/fault label is assigned to the trace.

Official schema: https://github.com/alibaba/clusterdata/tree/master/cluster-trace-microservices-v2021 . Caller response times are positive and server response times are negative; magnitudes are stored in separate measured series. Trace timestamps are relative milliseconds. The default import is a documented bounded prefix, not a statistically representative full-release sample. Selection, row limit, rejection counts, time range, source path, and observed metrics are retained. The research report also hashes the actual source archive. A bounded prefix can contain incomplete time bins, so results require validation on other slices.

RCAEval provides measured telemetry from controlled fault experiments (https://github.com/phamquiluan/RCAEval). Those measurements are useful for a separate supervised evaluation, but injected failures must be disclosed. They are not substituted for organically occurring banking outages. No alternative dataset is silently downloaded or relabeled.

## Implemented stages

1. Stream measured Alibaba durations without decompressing the entire archive first.
2. Retain per-resource missingness, units, relative time, and observed metric names.
3. Construct trace dependencies or explicitly configured AWS dependencies.
4. Diagnose chronological deviations using each metric's earlier median and MAD, holding out its latest observed window. Require at least five earlier windows. The robust-z threshold is a configurable-method convention, not a validated fault label.
5. Rank evidence-supported candidates and explain the exact measured deviation. Report insufficient evidence instead of a healthy classification when history is missing.
6. Build a one-hop frontier from those candidates and recorded/configured dependencies; propose the next measurements needed to distinguish mechanisms.
7. Recollect frontier AWS resources at the available native resolution. Report whether newer datapoints actually appeared. Never claim a change in sampling rate, independent confirmation, or measured cost savings from repeated reads.
8. Train a separate masked graph autoencoder on measured trace windows with chronological training/validation/test partitions, training-only scaling, reconstruction-error attribution, a training-mean baseline, and immutable report artifacts. Missing-feature filler tensors are masked out of training targets. The existing synthetic GNN is excluded from observed inference. The measured-data checkpoint also supplies reconstruction evidence for its exact documented held-out trace slice at runtime. Candidate ranking remains based on chronological deviations; unseen domains and mismatched slices abstain from GNN inference.
9. Persist observed runs separately, expose query timing, and display the actual evidence and limits in the dashboard.

## AWS and database diagnosis

CloudWatch requests now put `ReturnData` at the documented query level, batch up to 500 metrics, follow pagination, preserve full returned series, retain errors, and bound network waits. Read and write latency are retained separately. Bytes are converted to decimal megabits/second; IOPS are not called transaction throughput. No default CPU, memory, application latency, payment-service telemetry, or guessed first-resource topology is introduced.

AWS API: https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_GetMetricData.html . Sub-minute CloudWatch resolution requires an actual high-resolution source; requesting five-second native EC2/RDS metrics cannot manufacture it.

`GET /api/diagnostics/database` measures the analytics store independently of the monitored application's database. If `MONITORED_DATABASE_URL` is configured for PostgreSQL, it queries read-only system views for waits, blocking sessions, and cumulative statistics with a statement timeout. It does not fetch customer rows or query text. Set a least-privilege monitoring connection locally, e.g. a `postgresql+psycopg` URL. Do not commit credentials. Two observations are required to calculate rates from cumulative counters.

RDS storage read/write latency does not by itself establish slow SQL, lock contention, or application transaction latency. Corroborate with database waits and application spans. AWS reference: https://docs.aws.amazon.com/AmazonRDS/latest/UserGuide/USER_DatabaseInsights.html .

## Research hypothesis and limits

The proposed extension to TC-CFAO is **evidence-constrained frontier selection**: withhold an unsupported causal conclusion, identify competing mechanisms, and request discriminating evidence on the observed dependency frontier. This is a testable design, not a claim of established novelty. The current implementation uses explicit rules for those evidence requests, not learned information gain or causal discovery.

Required future evaluation: multiple independent real trace slices; resource-only and unfocused collection baselines; no-topology and no-abstention ablations; diagnosis coverage versus error using independently verified incident labels; measured query count, API latency, storage, and resource costs. Report supervised accuracy/Top-k only when genuine ground truth exists. The current Alibaba report deliberately leaves them null. No causal or cost-reduction claim is established by reconstruction loss.

## Run

From the main project directory:

```powershell
.\.venv\Scripts\python.exe scripts/run_observed_research.py
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 . The built dashboard is served by FastAPI. For UI development, run the frontend separately with `npm run dev`.

`ENABLE_SIMULATION=false` is the default. Historical synthetic scripts, checkpoints, documentation and results are retained for reproducibility but are not current real-data evidence. Do not run legacy `run_full_research.py` to produce the observed report. `results/observed/` is the new measured-data output; `OBSERVED_DATABASE_URL` defaults to a separate SQLite database, preserving the old experiment history.

Refresh AWS Academy credentials under the local `[default]` profile when STS reports `InvalidClientTokenId`. AWS resource creation, deployment costs, and live incident reproduction are not performed by these read-only collectors.


## Verified AWS lab configuration

After the lab credentials were refreshed, the configured us-east-1 account contained one running EC2 instance and no RDS instances. Read-only SSM checks found PostgreSQL 16 running on that EC2 instance, no HTTP application listener, and no blocked sessions in the initial snapshot. The prior RDS-only view could not observe this self-hosted database.

The isolated xai_observability database, least-privilege xaiobserver role/OS user, and explainableai-observer systemd service were installed without altering existing database authentication or network rules. The service binds to 127.0.0.1:8080, makes an actual read-only SELECT 1 health probe once per minute, logs measured durations, and publishes them to ExplainableAI/ObservedLab at standard resolution. It does not create artificial bank customers or transactions. CloudWatch custom-metric charges may apply; stopping the lab/service stops new publication.

The application execution timer excludes publishing/logging overhead. DB connection, query, and total round-trip timing are separate. A one-minute series needs six observed windows before the current temporal method can assess it; no backdated points are generated to fill the wait. AWS graph edges for these probe nodes derive from the deployed probe's measured database calls, not guessed banking dependencies.

POST /api/aws/database/diagnostics?instance_id=... verifies the target against discovered instances and runs a fixed read-only PostgreSQL system-view query through SSM. It persists snapshots separately and includes the prior snapshot for comparison. It does not retrieve SQL text or customer data. I/O timing was off in the first snapshot; zero blk_read_time therefore cannot prove fast disk I/O.

Use scripts/configure_aws_lab.py --instance-id INSTANCE_ID to reproduce the isolated installation after an AWS lab reset. The script requires a running managed instance with an instance profile permitted to publish metrics. Stop new probe publication on the EC2 host with sudo systemctl disable --now explainableai-observer; retained measurement logs and the isolated database remain intact.

## Strict observed-only update (16 October 2026)

The current acceptance report is `COMPLETION_REPORT.md`; baseline is `docs/STRICT_OBSERVED_BASELINE.md`. Controlled prototype code/results were archived outside the main project. Current live AWS analysis excludes the earlier trial period through 08:05 UTC and never uses it as a baseline. Stale/future observations and conflicting duplicate timestamps abstain from current anomaly classification. Database evidence is independent snapshot evidence, and three newer below-threshold points indicate only a return toward reference. Current rendered-browser checks supersede the earlier browser-helper limitation.
