# Explainable AI-Based Cloud Performance Analytics for Digital Banking using Graph Neural Networks

## Implementation status

Research V4 continues the published V3 checkout at `5a37d9b21fec73deec4d9691e71f092ddac0cac5`. The application is running at http://127.0.0.1:8000/. Publication revisions for this redesign are recorded in Git history. No cloud resources, permissions or faults were changed.

The default investigation now follows **Detect → Locate → Explain → Recommend → Verify**. A suspected service and a possible mechanism are separate outputs. Mechanism findings remain hypotheses, with explicit supporting, contradictory and missing evidence. Latency alone returns Unknown instead of a database-lock explanation.

Source backup: `D:\ExplainableAI_Project_Archived_Versions_2026_10_16\Before_root_cause_redesign\published_5a37d9b.zip`. The original Git history, V3 results, raw recordings, SQLite history, Alibaba checkpoints and earlier experiments remain in place. New outputs use `results/research_v4/`; empty directories from failed attempts contain no successful research results.

## Audit and preserved features

The audit covered App, ResearchWorkbench, styles, incident engine, benchmark evaluation, forecasts, observed analysis, evidence helpers, measured GNN, research API, bridge, pipeline, typed contracts, benchmark importer, TC-CFAO policy, tests and V3 documentation/results. Baseline: **63 backend tests and 7 browser tests passed** before changes.

Preserved: all four sources; actual Alibaba call topology and measured GNN; Microsoft point detection/forecast evaluation; all 150 RE1 recordings and published 90/30/30 split; chronological preprocessing and forecasting; ranked candidate retrieval; bounded TC-CFAO frontier; read-only AWS/PostgreSQL collection; independent benchmark scoring; incident persistence and measured follow-up comparisons. Legacy source-specific technical panels remain expandable.

The main dashboard has three navigation entries: Incident Investigation, Live Monitoring and Research Evidence. Research tables no longer dominate the investigation. Normal and insufficient-history states do not render empty cause/action panels. AWS authentication and resource access are separate; authentication success cannot produce a Healthy resource status.

## Two-level diagnosis

`import → chronological prefix → existing detector → resource ranking → resource-local mechanism evidence → conditional recommendation → measured follow-up / independent annotation comparison`.

The statistical ranking formula and published V3 localization protocol are unchanged. The new model version is `evidence-gated-mechanisms-v4`, so new incident snapshots do not overwrite V3 snapshots with the same observation time.

Mechanism assessment inspects only supplied measured evidence on the leading resource. It uses the incident's actual threshold/persistence gate. It does not inspect case names, injection annotations or future values. Scores are relative deviations, never failure probabilities. A CPU deviation is a CPU-pressure hypothesis; it does not prove saturation. Memory deviation does not establish exhaustion or a leak.

| Investigation family | Required direct evidence / boundary |
|---|---|
| CPU pressure | Persistent CPU deviation; workload, limits and throttling still require corroboration |
| Memory pressure | Persistent memory deviation; allocation/limits needed for a stronger conclusion |
| Disk/I/O degradation | Recorded disk timing, queue, I/O-wait or diskio deviation; I/O demand alone does not prove storage failure |
| Network delay | Direct network timing/RTT/retransmission measurement; request latency is insufficient |
| Packet loss | Direct loss/drop measurement |
| Database query delay | Measured query execution or database latency |
| Lock contention | Direct blocked-session/lock-wait evidence; no latency-to-lock shortcut |
| Connection delay | Direct establishment/acquisition timing |
| Pool exhaustion | Wait evidence plus measured occupancy at a measured limit |
| Request overload | Joint demand and resource/queue evidence; request rate alone is insufficient |
| Application processing delay | Direct processing/server/self-time measurement |
| Service failures | Measured errors/timeouts; logs/spans still needed for attribution |
| Dependency degradation/failure | Actual dependency edge plus abnormal dependency metrics; failure wording requires measured errors |
| Unknown | Mechanism-specific evidence absent or inadequate |

Every hypothesis exposes its measurements, missing corroboration and normal contradictory measurements. No mechanism is marked independently verified. Recommendations include investigation, conditional mitigation and a verification signal. At most three are shown. TC-CFAO follow-up questions now use the mechanism assessment instead of a generic database-wait suggestion for every latency anomaly.

Propagation displays only recorded/configured edges and compatible or contradictory observed ordering. The existing onset estimate covers the trailing six valid observations; it is not the independently annotated fault start. Recovery uses newer observations and the original saved reference/threshold. Returning toward reference is distinguished from verified causal recovery.

## Dataset and topology verification

Official sources: [RCAEval repository](https://github.com/phamquiluan/RCAEval), [author-maintained Parquet data](https://huggingface.co/datasets/phamquiluan/RCAEval), [upstream RE1 disk-measurement limitation](https://github.com/phamquiluan/RCAEval/releases).

The actual official index describes CPU stress, memory stress, disk I/O stress, network delay and network packet loss. These are published controlled-injection annotations, not independently proven physical mechanisms in arbitrary live systems. RE1 lacks direct disk-I/O telemetry; its disk cases cannot establish disk failure merely from latency. RE1 also lacks recorded dependencies. No RE1 arrows were invented.

Five RE2-OB recordings were downloaded separately at the existing pinned author revision `afeacb11bcc94dadfd1c8f483ee4377b2b8b614e`: repetition 1, one per five fault categories paired with sorted distinct root services, selected before inference. There are now 155 imported RCAEval recordings (150 original RE1 plus 5 illustrative RE2); Microsoft remains 60 series. Raw files remain ignored by Git.

| New recording | Fault annotation |
|---|---|
| re2ob_checkoutservice_cpu_1 | CPU stress |
| re2ob_currencyservice_mem_1 | Memory stress |
| re2ob_emailservice_disk_1 | Disk I/O stress |
| re2ob_productcatalogservice_delay_1 | Network delay |
| re2ob_recommendationservice_loss_1 | Network packet loss |

RE2 edges match `traceID` and `parentSpanID` to actual recorded parents. Both spans must have completed before an edge is available. Jaeger microsecond start/duration coordinates are retained for completion calculations. The only explicit service alias is trace `frontendservice` to metric `frontend`; unmatched trace services are reported rather than assigned fictional nodes. Direction remains caller → callee in the UI. Checksums, revision and selection live in `dataset/raw/research_v4/manifest.json`; label-bearing metadata never becomes an inference feature.

## Actual experimental findings

### Published V3 results preserved

- Microsoft median/MAD F1: **0.3269**, with 728 false-positive points on the common held-out valid mask. Forecast residual F1: **0.1216**. No new detector superiority claim.
- Original 30-case RE1 test split: service Top-1 **60%**, Top-3 **86.67%**.
- All 30 V3 test cases had pre-injection alerts. Zero conditional post-injection delay does not establish useful onset detection.
- Alibaba training-only-topology GNN reconstruction MSE **0.51723**, identity feature model **0.000947**. The non-graph model is better on that reconstruction task; this negative finding remains visible.
- Existing forecast and TC-CFAO results remain accessible. No AWS cost reduction or independently verified AWS fault accuracy is claimed.

### Separate mechanism study

Artifact: `results/research_v4/mechanisms_20261016/report.json`; classifier state: `model.json` alongside it.

All original 150 RE1 cases are retained. A new fault-stratified grouped split assigns the six system/service groups within each fault to four train, one validation and one test group using a declared SHA-256 ordering. All five repetitions of a service/system/fault setting remain together: **100 train / 25 validation / 25 test**. Each test fault has five recordings. V3 partitions and files are untouched. Systems and service identities can recur across different fault groups; this is not cross-system generalization.

Features are constructed before reading annotations: max log-deviation and persistent-deviation fraction for recorded CPU, memory, latency, load and directly measurable optional mechanism columns, on the leading resource and recording prefix. IDs, injected service, fault names and injection time are excluded. Diagnosis uses the same midpoint + 120-second checkpoint and frozen early reference. A standardized nearest-centroid classifier fits training cases only; abstention margin **0.2** is selected using validation macro-F1. It is an experimental injected-label predictor and is **not deployed as a physical mechanism diagnosis**.

| 25-case new test split | Evidence rules | Nearest centroid |
|---|---:|---:|
| Service Top-1 (shared localization) | 96% | 96% |
| Service Top-3 | 100% | 100% |
| Mechanism annotation accuracy | 28% | 24% |
| Mechanism macro-F1 (five classes) | 0.2500 | 0.3310 |
| Diagnosis coverage | 56% | 48% |
| Abstention rate | 44% | 52% |
| Joint service + mechanism accuracy | 28% | 24% |

Confusion matrices and per-case outcomes are preserved in the report and shown through expandable heatmaps. The rules confuse several disk annotations with CPU pressure. The classifier confuses delay/loss and often abstains. A symptom signature is not sufficient for verified fault classification. The new favorable service split must not be presented as an improvement over V3's different test set.

On the original V3 30-case test set, new mechanism rules score **30% annotation accuracy**, **0.2133 macro-F1**, **66.67% coverage** and **30% joint accuracy**; service scores remain 60%/86.67%. That test has no delay cases, which is why the separate representative study was added.

### Recorded RE2 graph comparison

Artifact: `results/research_v4/re2_graph_20261016_02/report.json`; ten small model checkpoints alongside it.

This is an illustrative five-recording study, not a representative aggregate benchmark. Each case trains a fresh lightweight graph next-observation predictor on its first 20% of measurements, selects weights on the next 10%, and ranks recent prediction residuals at midpoint + 120 seconds. All five validation prefixes end before their independent injection annotations. CPU, memory, p90 latency and workload are used at source scale with training-only normalization and masks. No Alibaba weights or fault labels are transferred.

The identity and graph models use the same architecture, seed 42, 100 epochs and validation selection. Next-observation prediction avoids the previous identity reconstruction shortcut. Graph edges come only from completed training-prefix spans (nine measured relationships per recording); message passing symmetrizes these edges, while UI arrows retain their recorded direction.

| Five illustrative cases | Identity | Recorded graph |
|---|---:|---:|
| Service Top-1 | 60% | 60% |
| Service Top-3 | 80% | 80% |

There is **no demonstrated graph advantage**. The experiment establishes a valid recorded-topology comparison, not a claim of novelty, robust RCA accuracy or real-world causality. Online candidate ranking remains the transparent evaluated evidence method; these experimental graph checkpoints are research evidence, not silently activated production models.

## Interface and guided demonstration

Visuals include a chronological measured chart with reference/threshold, separate next-observation prediction and interval, top-three ranking bars, a resource anomaly map for metric-only data, a clickable recorded dependency graph with visible arrowheads, before/reference comparison cards, competing evidence panels, conditional action cards, and independent service/mechanism comparison cards. Unknown-unit data is not relabelled as milliseconds or percent.

Concise aliases are stable over the sorted complete resource set. Recognizable recorded identifiers provide service names; opaque IDs become Resource NN. Original IDs and numerical evidence remain in tooltips/details. No chart substitutes labels for model predictions. Selected-metric loading cannot display a different metric under the newly selected label.

The guided catalog contains CPU, memory, disk, delay, loss, a recorded RE2 graph example, and a Microsoft example without service/mechanism labels. Case selection is deterministic by published category/opaque ID, not prediction correctness. Wrong predictions and Unknown are retained. Demo titles can hint at the published experiment category to the viewer; those titles are never model inputs. These examples are instructional, not the aggregate evaluation sample.

On completed replay, the server verifies bounds and computes the prediction before loading the independent annotation. The UI then displays the declared evaluation checkpoint so its diagnosis and annotation comparison share the exact same prefix. Restart/seek clears revealed truth. The old V3 score endpoint is retained for compatibility; the new UI uses the completed-replay-gated endpoint.

### Three-to-five-minute faculty walkthrough

1. **0:00–0:40 — Purpose.** Open the dashboard. Keep the exact official title. Explain the difference between an abnormal metric, a suspected resource and a physical mechanism. Choose RCAEval and Guided Demo. Explain that these are real recordings of published controlled experiments, not an operating banking deployment.
2. **0:40–1:40 — Stronger measured example.** Select **Recorded trace dependencies (RE2)**. Restart, play at 600 seconds per step, and finish the recording. Inspect Checkout Service's actual CPU chart and the three status cards. The CPU-pressure hypothesis must remain unverified. Click a recorded graph node; explain that arrows come from actual parent/child spans, not a fictional architecture.
3. **1:40–2:40 — Explain and recommend.** Open Locate, Explain and Recommend. Inspect the actual supporting values, missing capacity/throttling corroboration and conditional action. Do not describe a CPU z-score as utilization percent or saturation probability. Use Verify and reveal the independent annotation. The view returns to the declared checkpoint; compare predictions honestly, including a mismatch if one occurs.
4. **2:40–3:30 — Insufficient mechanism evidence.** Choose **Delay annotation: distinguish symptom from mechanism** or the disk example. Play/finish. Show Unknown or a competing pressure hypothesis when direct network/storage evidence is absent. Reveal the injected category only for comparison. This demonstrates the difference between locating an abnormal resource and verifying its cause.
5. **3:30–4:30 — Scientific evidence.** Open Research Evidence. Show V3 60%/86.67% service results, the separate mechanism confusion matrix and the tied RE2 graph comparison. State the false-alarm and negative GNN findings. Optionally show Microsoft as anomaly-only and Alibaba as production call topology without verified cause labels.

The demo does not claim recovery: these recordings do not supply independently verified recovery endpoints. Save a deviation snapshot and a later snapshot to inspect actual follow-up when available. Never invent a return-to-normal event.

## Start and reproduce in Windows PowerShell

Use the main checkout, not the empty old V2 directory:

```powershell
Set-Location 'D:\ExplainableAI_Cloud_Banking_Cloud_Project_2026_RESEARCH_V1\ExplainableAI_Cloud_Banking_Cloud_Project_2026'
.\.venv\Scripts\python.exe -m pip install -r requirements-benchmarks.txt
npm --prefix frontend ci
npm --prefix frontend run build
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000/. If this server is already running, use the existing page and refresh it. No AWS session is required for the recorded demonstrations.

Fresh data setup and independent experiments (each output folder must be new):

```powershell
.\.venv\Scripts\python.exe scripts/import_research_benchmarks.py --help
# Run the existing documented V3 import commands in docs/RESEARCH_PLATFORM_V3.md.
# They create the pinned RE1 official index required by the bounded RE2 importer.
.\.venv\Scripts\python.exe scripts/import_re2_graph.py
.\.venv\Scripts\python.exe scripts/evaluate_mechanisms.py --out results/research_v4/mechanisms_NEW_RUN
.\.venv\Scripts\python.exe scripts/evaluate_re2_graph.py --out results/research_v4/re2_graph_NEW_RUN
.\.venv\Scripts\python.exe -m pytest -q
npm --prefix frontend run test:e2e
```

The UI exposes explicitly versioned current V4 reports; a new experimental run does not silently replace the published/current result merely by being newer. Import refuses to overwrite an existing RE2 manifest. Raw credentials/data remain ignored.

## Files changed or added

| Area | Files |
|---|---|
| Shared mechanism inference | `analysis/mechanisms.py`, `analysis/incident_engine.py` |
| Recorded topology and contracts | `dataset/re2.py`, `dataset/benchmarks.py`, `common/research.py` |
| Integration and independent verification | `backend/research_api.py` |
| Visual investigation and navigation | `frontend/src/App.jsx`, `frontend/src/ResearchWorkbench.jsx`, `frontend/src/InvestigationView.jsx`, `frontend/src/ResearchEvidence.jsx`, `frontend/src/styles.css` |
| Reproduction | `scripts/import_re2_graph.py`, `scripts/evaluate_mechanisms.py`, `scripts/evaluate_re2_graph.py` |
| Regression coverage | `tests/test_mechanisms.py`, `tests/test_research_v3.py`, `frontend/e2e/research.spec.js` |
| Measured outputs | `results/research_v4/mechanisms_20261016/`, `results/research_v4/re2_graph_20261016_02/` |
| Handover | this document, `README.md`, `COMPLETION_REPORT.md` |

## Verification and remaining limitations

Final acceptance details are recorded in `results/research_v4/acceptance_final_20261016.json`. Backend: **87 passed**, three existing deprecation warnings. Browser: **12 passed**. Vite production build passed. Browser tests exercise both required resolutions, the complete recorded investigation, actual RE2 graph, source restrictions, normal/insufficient states and authenticated-but-denied AWS access. Screenshots in `frontend/test-results/` were inspected and visual issues corrected; they remain ignored operational artifacts.

AWS has not been changed or fault-tested. The last V3 live check authenticated but EC2/RDS discovery was denied by the lab role. This redesign tests the denial presentation in isolation, not a claim that current resource permissions were restored. Live fault accuracy remains unverified.

Mechanisms remain only partly identifiable. RE1 lacks critical storage/network/wait/pool evidence. New supervised classification is weak and not deployed. Five RE2 examples are too small and curated for general accuracy claims. The original Microsoft false positives, all-case pre-injection alert limitation, negative Alibaba reconstruction comparison and absence of verified live AWS failure/recovery accuracy remain prominently accessible. This project provides evidence-constrained investigation, not established causal identification or proven research novelty.
