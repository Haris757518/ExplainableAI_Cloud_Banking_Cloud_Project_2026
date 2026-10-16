# Explainable AI-Based Cloud Performance Analytics for Digital Banking using Graph Neural Networks

## Implemented system and status

This update extends the existing FastAPI, React/Vite, SQLAlchemy, Alibaba importer, measured GNN, AWS collector, PostgreSQL diagnostics and TC-CFAO policy. The official title is unchanged. Git history, licensing, historical results, synthetic-only artifacts, current observed records and previously uncommitted work are preserved. It is a functioning research application with explicit scientific limitations, not a claim of a production-validated banking fault detector.

**Working:** four source selections; typed telemetry/incident/forecast/evidence contracts; official benchmark import; chronological replay; evaluated statistical detection and forecasts; candidate retrieval/reranking; computed model explanations; bounded follow-up requests; conditional recommendations; incident persistence; actual subsequent-reference comparison; source-specific graph views; read-only AWS and PostgreSQL monitoring; research result tables and model metadata.

**Not implemented/validated:** RE2 multi-source import, supervised graph-based RCA, calibrated failure probabilities, confirmed memory leak/pool exhaustion/packet loss without those measurements, autonomous remediation, proof of novelty, production banking SLOs, cross-system model transfer, guaranteed prediction intervals, and an empirical real AWS failure/recovery event. Controlled cloud experiments remain disabled; the earlier prototype is preserved separately. No cloud resource changes or faults were performed under this request.

## Baseline and audit

Baseline revision: `7adcc5eb437e011c898c65c275920f1fac3a0523`. This release includes the preserved working changes. Baseline: 46 tests passed, three deprecation warnings; frontend build passed. Full baseline and prior model performance: `docs/MASTER_RESEARCH_BASELINE.json`.

Backup before implementation: `D:\ExplainableAI_Project_Archived_Versions_2026_10_16\Before_master_research_093011`. Current data files remain in place. Original `results/observed/` and `results/observed_v2/` are untouched.

Audit findings:

- `AIEngine`, `analysis/rca.py`, `analysis/evaluation.py` and the old five-second TC-CFAO policy belong to the historical synthetic experiment. They remain available but are excluded from observed-data inference/evaluation. The legacy checkpoint is not transferred to real AWS or benchmarks.
- `analysis/observed.py` provides the preserved measured median/MAD path. `analysis/incident_engine.py` adds label-blind incident evidence, persistence, retrieval, explicit heuristic reranking and abstention. Scores are not probabilities. Recommendations are deterministic statements derived from measured evidence, not learned causal facts.
- `ai_models/observed_gnn.py` is a genuine masked graph autoencoder, trained on observed Alibaba windows with training-only scaling and chronological validation. Runtime application checks the exact documented series digest and domain. The original checkpoint remains a disclosed transductive experiment. A new comparison selects nodes/edges from the training period only.
- AWS commonly displays no deviation because the existing lightweight SELECT 1 probe and eligible native metrics have not shown a significant supported deviation. That is not a bug to fix by manufacturing failures. Memory agents, real banking requests, pool occupancy and packet-loss measurements remain unavailable.
- Missing values, ambiguous source rows and unavailable evidence are not replaced by zero. Source-local Microsoft timestamps without a timezone are identified as such. Alibaba window-start coordinates are preserved; the new forecast bridge uses window-end availability and retains the original timestamp.

## Data and provenance

| Source | Imported/used | Purpose and boundaries |
|---|---|---|
| Alibaba production trace | Existing 100,000-row bounded selection; 77,375 valid measured calls; original 40-node/80-edge experiment preserved | Measured latency, recorded dependencies and masked reconstruction; no fault/banking labels |
| Microsoft cloud-monitoring dataset | All 60 official CSV series; 225,445 raw rows | Expert-labelled point detection and forecasting; no service graph or RCA labels |
| RCAEval RE1 | 150 recorded controlled cases: 50 per Online Boutique, Sock Shop and Train Ticket | Two lexicographic root-service selections per system, all five faults and five repeats; 90 train / 30 validation / 30 test |
| AWS | Existing EC2, CloudWatch and PostgreSQL observability probe | Actual live measurements; no independently labelled live fault accuracy |

Official sources: [Microsoft](https://github.com/microsoft/cloud-monitoring-dataset), [RCAEval official repository](https://github.com/phamquiluan/RCAEval), [author-maintained Parquet distribution](https://huggingface.co/datasets/phamquiluan/RCAEval), [Alibaba](https://github.com/alibaba/clusterdata/tree/master/cluster-trace-microservices-v2021).

Pinned Microsoft revision: `6a07a53c2fac495fb6831811df4c980d6c04bd10`. RCAEval revision: `afeacb11bcc94dadfd1c8f483ee4377b2b8b614e`. The manifest records each raw checksum. MIT source notices/metadata are downloaded with the data. Raw research data and live operational reports are ignored by Git.

The Microsoft files contain 241 duplicate timestamps: identical recordings are counted once, with original row positions retained. Two conflicting annotations are excluded from scoring; one conflicting measurement stays unknown. Blank measurements stay missing. Original CSV values and labels are never overwritten. Normalization and labels remain aligned after chronological ordering.

RCAEval labels are stored separately from typed inference inputs. Case names that encode the cause are replaced with opaque IDs before inference. All repetitions of a system/service/fault setting remain in one split, ordered deterministically by a SHA-256 group key. The test partition contains Sock Shop and Train Ticket cases; it is not evidence of held-out Online Boutique generalization.

## Shared architecture and algorithms

`import -> validated source case -> chronological prefix -> measured evidence -> candidate retrieval -> evidence reranking -> TC-CFAO bounded requests -> recommendation/forecast -> immutable investigation snapshot -> optional independent scoring`.

`common/research.py` defines sources, observations, series, edges, forecasts, evidence, candidates, recommendations, incidents and evaluation records. Existing public observed endpoints remain compatible. `backend/services/research_bridge.py` adapts Alibaba/AWS to the same incident engine. `backend/research_api.py` supplies source status, catalog, capabilities, recording metadata, replay, incident history/detail, independent scoring, results and model metadata. Long training/evaluations run through explicit offline commands, not on dashboard startup.

The detector compares a valid current measurement with a preceding median. Scale is `max(1.4826*MAD, 5% of reference magnitude, 1e-8)`. Microsoft uses a validation-selected two-sided threshold; live/recorded mechanism cues are direction-aware and remain relative deviations. Persistence rejects short noise under the selected source rule. Data quality and missing evidence are reported separately.

RCA candidates are retrieved from abnormal measured resources. Reranking is `log(1 + maximum deviation) + 0.15 * supporting metrics + 0.2 * supported recorded upstream relationships with compatible onset`. These are explicit heuristic weights, not learned explanation/confidence values. RE1 has no recorded call topology, so its graph term is zero and no graph is fabricated. The extended `CFAOEngine.evidence_frontier` uses a bounded top-three budget, reports genuine transaction-path availability and requests discriminating measurements. AWS logical probe resources map to their recorded host before recollection; no resolution increase or cost saving is assumed.

Capabilities are queried per case. Relative latency changes, query/connection timing changes, CPU/memory deviations when measured, throughput decreases, sustained changes and data-quality/recovery mechanics are implemented. Direct lock/session evidence is available through PostgreSQL diagnostics. Exhaustion, saturation limits, packet loss, specific disk/network faults and cascading causal claims remain unsupported unless the required independent measurements/topology exist. An official fault annotation does not turn an unsupported predicted mechanism into a confirmed diagnosis.

## Actual detection results

Microsoft split: first 60% of each chronological series for training, next 20% validation, final 20% test. Both detectors use the same 45,017 valid held-out points; 35 unscorable/conflicting points are excluded and counted. No point adjustment or test-label threshold tuning is used.

| Detector | Precision | Recall | F1 | FP | FN | False-alarm rate |
|---|---:|---:|---:|---:|---:|---:|
| median_mad | 0.2587 | 0.4441 | 0.3269 | 728 | 318 | 0.0164 |
| forecast_residual | 0.0681 | 0.5717 | 0.1216 | 4478 | 245 | 0.1008 |

The median/MAD rule uses threshold 5 and persistence 1, selected on validation. Forecast residuals perform worse; no ensemble improvement is claimed. The runtime Microsoft view uses the same frozen validated rule when completed result artifacts are available. Its score is still not calibrated failure probability.

## Actual localization results

RCAEval uses a predeclared checkpoint at recording midpoint plus 120 seconds, without passing injection time or root labels into prediction. A frozen reference covers the first `min(600 seconds, 20% of recording duration)`. The recording bounds are source catalog metadata, not future metric values. Every baseline precedes the annotated injection in the completed audit. Each method sees the same prefix; labels are read only after predictions.

| Method, 30 held-out cases | Top-1 | Top-3 | MRR | Retrieval@20 |
|---|---:|---:|---:|---:|
| temporal | 0.2333 | 0.6000 | 0.4454 | 1.0000 |
| without_gate | 0.2667 | 0.6333 | 0.4726 | 1.0000 |
| evidence_gated | 0.6000 | 0.8667 | 0.7445 | 1.0000 |

This is fixed-checkpoint localization, not alert-triggered end-to-end incident accuracy. Checkpoints are approximately 63.5-120 seconds after the actual annotations. Per-fault/system results are in the JSON. After completing replay, independent scoring returns to this same checkpoint rather than comparing an unrelated end-of-recording prediction.

The separate chronological timing evaluation found post-injection alerts in 30/30 cases, but **all 30 cases also had pre-injection alerts**. Conditional delay was zero seconds because an any-resource alert could already be active. This is a material false-alarm limitation, not evidence of an excellent zero-latency detector. Broader normal-history calibration and an independently frozen external test set are needed before operational alert deployment.

## Actual graph and explanation comparison

Same seed (42), optimizer/architecture, 100 epochs, measured features, chronological split and train-only scaling:

| Method | Held-out reconstruction MSE |
|---|---:|
| Training-mean reference | 1.050895 |
| Feature autoencoder, identity adjacency | 0.000947 |
| Genuine GNN, training-selected recorded topology | 0.517233 |

Nodes/edges are selected only from calls through 175,000 relative milliseconds, within the training period. The recorded direction is retained in source graphs; the preserved model symmetrizes adjacency internally. The no-graph model reconstructs much better on this task. Reconstruction has an identity-learning shortcut and is not detection/localization accuracy. No GNN detection advantage or graph RCA superiority is established. Full-slice historical transductive results remain preserved separately.

The graph experiment also measures exact held-out reconstruction contributions and prediction changes when each input feature or recorded edge is removed internally. These are computed sensitivity/fidelity probes, not claims of causality or a reproduction of GNNExplainer's optimized-mask algorithm. No source telemetry is altered.

## Actual forecasting results

Persistence, seasonal-naive lag 24 and ridge autoregression on 12 preceding observed records are compared. Ridge penalty is 1; preprocessing uses training only. The selected model minimizes validation MAE. Test MAE/RMSE are computed without refitting on test labels. All 60 series were evaluated. Different series have different units, so their raw MAE values are not pooled into an invented single score.

Examples below are the first series in each source category, not a selection of winners:

| Official series | Validation-selected model | Test MAE | Test RMSE | Persistence test MAE | Empirical interval coverage |
|---|---|---:|---:|---:|---:|
| application-crash-rate-1/app1-01.csv | ridge_ar12 | 40.31 | 93.28 | 31.21 | 0.671 |
| application-crash-rate-2/app2-01.csv | persistence | 0.02343 | 0.04094 | 0.02343 | 0.864 |
| consumer-purchase-rate/purchase-01.csv | persistence | 0 | 0 | 0 | 1.000 |
| data-ingress-rate/ingress-01.csv | persistence | 1.966e+04 | 2.855e+04 | 1.966e+04 | 0.934 |
| ecommerce-api-incoming-rps/api-01.csv | ridge_ar12 | 5.728 | 12.37 | 7.089 | 0.906 |
| middle-tier-api-dependency-latency/outbound-01.csv | persistence | 1.361 | 1.8 | 1.361 | 0.965 |
| mongodb-application-rps/mongo-01.csv | ridge_ar12 | 34.84 | 94.21 | 38.08 | 0.939 |
| mongodb-machine-rps/machine-01.csv | ridge_ar12 | 44.98 | 91.46 | 54.1 | 0.852 |
| service-unavailable/unavail-01.csv | persistence | 0 | 0 | 0 | 1.000 |

Intervals use the validation 90th-percentile absolute residual; time-series dependence means coverage is not guaranteed and may be well below 90%. Threshold warnings refer to a training-only 95th percentile, not a banking SLO or independent incident label. Forecasts are one observed-record ahead. A calendar timestamp is emitted only for a regular observed cadence; irregular histories have an unknown calendar horizon. These forecasts are visibly distinguished from real observations.

## Actual TC-CFAO follow-up evaluation

Thirty held-out cases; actual Parquet column reads and 60 additional seconds of already recorded observations. All methods start from the same initial detection evidence. No new test workload, fake telemetry or AWS resource action is introduced.

| Strategy | Mean resources | Mean metric columns | File calls | Top-1 | Top-3 |
|---|---:|---:|---:|---:|---:|
| broad | 55.83 | 190.67 | 1 | 0.5667 | 0.8333 |
| uniform_first3 | 3.00 | 10.30 | 1 | 0.1667 | 0.1667 |
| random3_seed42 | 3.00 | 11.17 | 1 | 0.1667 | 0.1667 |
| static_one_hop | 2.93 | 15.33 | 1 | 0.7667 | 0.8667 |
| evidence_frontier | 2.93 | 15.33 | 1 | 0.7667 | 0.8667 |
| legacy_top1_frontier | 1.00 | 5.27 | 1 | 0.6000 | 0.6000 |

Initial broad detection cost is excluded from marginal follow-up accounting. Static one-hop and the evidence frontier coincide when no topology is available, so that comparison does not establish an additional graph benefit. Every nonempty strategy makes one file call. `table_memory_bytes` is materialized data volume, not bytes billed/read from disk. Fixed strategy order and OS cache affect local timing; no cloud-cost or controlled latency-improvement claim is made. These are exploratory subset results, not proof of established novelty.

## AWS verification and boundaries

`results/research_v3/aws_validation_20261016.json` records an actual read-only verification: nine observed metrics, five eligible legacy temporal series, no deviation in eligible observed metrics, and zero blocked PostgreSQL sessions. Probe execution was approximately 4.03034 ms and query time 0.263378 ms in that snapshot. It is SELECT 1 observability traffic, not a payment request. Missing production banking spans, pool utilization, memory and packet-loss telemetry remain unavailable. Current source errors never mean healthy operation.

The earlier controlled-trial interval remains excluded from live analysis through 2026-10-16 08:05 UTC. No service, cloud resource, security rule, credential, authentication setting or database workload was reconfigured under this request. Optional lab execution requires a separate explicit authorization and remains disabled. The existing idle archived lab installation was not restarted or removed.

## Verification and remaining limits

Latest backend checks: **63 tests passed**, three existing library deprecation warnings. Production build passed (32 modules). Seven real/fixture browser tests passed before the final acceptance rerun; the final browser result is recorded in the acceptance note. The browser tests exercise actual Alibaba rendering, Microsoft source/recording/history and RCAEval replay/scoring plus four isolated empty/normal/deviation/unavailable fixtures. Rendered screenshots were inspected and encoding/control-style issues were repaired.

The core live/dataset smoke verification passed. Fixture databases are isolated; test labels/measurements are not research artifacts. Benchmark downloads are not required for pure mechanic tests; the importer/real commands validate their presence and checksums explicitly.

Remaining scientific work: independently selected Alibaba partitions beyond the bounded slice; official RE2 logs/traces and a time-valid service-call graph; supervised graph-RCA comparison; calibrated alert false-positive control; genuine recorded recovery-end labels or future passive incident evidence; unseen-series/system generalization; confidence/calibration and external confirmatory evaluation. Earlier exploratory runs and protocol corrections remain saved, so the final test is not presented as an untouched confirmatory external benchmark. Recommendation efficacy cannot be quantified without actual authorized mitigation outcomes. No root cause is inferred from fault names, and no operational action is executed automatically.

## Reproduce and demonstrate (PowerShell)

```powershell
Set-Location -LiteralPath 'D:\ExplainableAI_Cloud_Banking_Cloud_Project_2026_RESEARCH_V1\ExplainableAI_Cloud_Banking_Cloud_Project_2026'
# Existing virtual environment; create one first with: py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-benchmarks.txt
npm ci --prefix frontend
.\.venv\Scripts\python.exe scripts/import_research_benchmarks.py
.\.venv\Scripts\python.exe scripts/run_benchmark_research.py --dataset all --out results/research_v3/reproduction_NEW
.\.venv\Scripts\python.exe scripts/run_graph_ablation.py --out results/research_v3/graph_NEW --training-topology --epochs 100
.\.venv\Scripts\python.exe scripts/evaluate_investigation.py --out results/research_v3/investigation_NEW.json
.\.venv\Scripts\python.exe scripts/evaluate_detection_timing.py --out results/research_v3/detection_timing_NEW.json
.\.venv\Scripts\python.exe scripts/run_observed_research.py --out results/observed_v2/reproduction_NEW --epochs 100
.\.venv\Scripts\python.exe -m pytest -q
npm run build --prefix frontend
$env:ENABLE_SIMULATION = 'false'
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

From a second window in the same project:

```powershell
Push-Location frontend
npx playwright test
# Development UI, if needed: npm run dev
Pop-Location
.\.venv\Scripts\python.exe scripts/verify_live.py --out results/research_v3/aws_validation_NEW.json
```

Use a fresh output directory/name for each experiment; never overwrite historical results. AWS uses the existing local shared-credential profile. Refresh that local Academy/SSO session if expired; do not paste or commit keys. The browser checks use installed Microsoft Edge on Windows.

Open `http://127.0.0.1:8000/`. Choose Microsoft to inspect actual labelled histories, selected forecasts and measured research scores. Choose RCAEval, select a published CPU/delay/memory/disk/loss recording, and replay from the beginning. Before injection, describe relative baseline behaviour honestly; do not claim verified health from incomplete metrics. Pause/seek to inspect only the recorded prefix. Record an investigation, then advance and record again for subsequent-reference comparisons. At the end, score independently: the interface returns to the declared benchmark checkpoint and shows the actual root annotation and predicted rank, including incorrect predictions. Dataset fault names are viewer context, not model inputs.

For a network-labelled recording, explicitly distinguish its published injection annotation from an unsupported predicted packet-loss mechanism. For cascading failure, current Alibaba relationships show potential affected dependencies; no verified cascade label is available, so that requested demonstration is not claimed as validated. AWS demonstrates actual telemetry independently of benchmark replay. An actual normal AWS observation must remain unchanged. Controlled lab demonstrations are disabled pending separate authorization.

Current machine-readable primary outputs: `results/research_v3/run_20261016_final/`, `graph_ablation_train_topology/`, `investigation_20261016_02.json`, and `detection_timing_20261016.json`. `run_20261016_04` used an unsuitable warm-up for short recordings and is superseded; `_05` corrected that issue but the final run also applies a common valid-point mask to Microsoft comparisons. Original results are preserved, not silently replaced.

## Implementation inventory

New and extended source files:

- `ai_models/observed_gnn.py`
- `analysis/benchmark_evaluation.py`
- `analysis/forecasting.py`
- `analysis/incident_engine.py`
- `aws/normalizer.py`
- `backend/main.py`
- `backend/research_api.py`
- `backend/services/pipeline.py`
- `backend/services/research_bridge.py`
- `cfao/policy.py`
- `common/research.py`
- `dataset/benchmarks.py`
- `dataset/observed_trace.py`
- `frontend/e2e/investigation.spec.js`
- `frontend/e2e/research.spec.js`
- `frontend/index.html`
- `frontend/src/App.jsx`
- `frontend/src/ResearchWorkbench.jsx`
- `frontend/src/styles.css`
- `scripts/evaluate_detection_timing.py`
- `scripts/evaluate_investigation.py`
- `scripts/import_research_benchmarks.py`
- `scripts/run_benchmark_research.py`
- `scripts/run_graph_ablation.py`
- `tests/test_research_v3.py`

Also added `requirements-benchmarks.txt`; preserved/updated `.gitignore`, source index title, completion/setup documentation and versioned research outputs. Publication revisions are recorded in Git history; prior history and research outputs are preserved.

## Final acceptance note

The final backend regression run passed **63 tests** with 3 existing deprecation warnings (4.48 seconds); the final seven-test browser run passed in **16.0 seconds**. Original annotations for all 150 RCAEval cases were subsequently cross-validated against both the author-supplied Parquet index and original inject_time files, without changing labels or predictions. Sixty training-only ridge forecast states were serialized and their predictions verified after JSON round-trip; artifact: `results/research_v3/forecast_models_20261016.json`. Reproduce with `scripts/export_forecast_models.py --out NEW_MODEL_ARTIFACT.json`.

For consistency, runtime prefix forecasts use the same 60% fit / 20% model-selection protocol as the evaluation; the remaining already observed prefix supplies lag inputs but never test-label fitting. An irregular calendar cadence suppresses a dated forecast marker rather than inventing its time. Forecast warnings use training-only quantiles and do not establish future failure probability.

No input-level dataset failure was hidden: the initial parser rejected genuine duplicated rows and missing values before its explicit conflict/missingness policy was implemented. An earlier browser run failed because legacy source details were collapsed; the tests were updated to open those details, then all seven passed. The initial handover write was temporarily blocked by an automatic approval-review account limit; the same approved path succeeded after retry. The final AWS authorization blocker is recorded below.

## Final external AWS access blocker

At **16:51 IST on 16 October 2026**, STS authentication succeeded but the existing default session denied `ec2:DescribeInstances` (`UnauthorizedOperation`) and `rds:DescribeDBInstances` (`AccessDenied`). The final live verification therefore did **not** pass. Earlier successful live measurements remain historical evidence in `aws_validation_20261016.json`; they are not described as current monitoring success. Current authorization status is recorded in `results/research_v3/aws_validation_access_final_20261016.json` (local/ignored).

The application correctly returns an access error, never a healthy classification. The UI distinguishes authenticated credentials from successful resource collection. AWS permission changes were not attempted. The specific external prerequisite is restoration of these read permissions in the active Academy/lab role (or restoration of the authorized lab session by its operator/administrator), followed by rerunning `scripts/verify_live.py` to a fresh output path. Simply passing STS is insufficient. No credentials should be pasted into chat or committed.

This currently blocks live resource discovery/collection verification; local benchmark replay, forecasts, model evaluation and incident history remain usable. There is no local implementation permission blocker.

Final added utility: `scripts/export_forecast_models.py`; verified 60 serialized models. Final added regression verifies authenticated-but-unauthorized AWS discovery returns an error rather than healthy status. `git diff --check` passed. The final acceptance manifest is `results/research_v3/acceptance_final_20261016.json`.
