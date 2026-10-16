# Explainable AI-Based Cloud Performance Analytics for Digital Banking using Graph Neural Networks

## Final review build

This is the final banking-focused completion pass in the existing repository and `main` working tree. It is not a new project or development-version scheme. Baseline: published commit `800b4f0ced1a30205b84c291ed70d2ac54f870f6`. Source backup: `D:\ExplainableAI_Project_Archived_Versions_2026_10_16\Before_final_banking\published_800b4f0.zip`. There were no uncommitted files at the initial audit.

**Implemented and verified:** a genuine instrumented academic banking application, three real local HTTP processes, dedicated SQLite test balances/ledger, real measured spans, frozen normal calibration, a bounded application-delay experiment, evidence-based service/mechanism investigation, compatible banking GNN inference and comparison, conditional recommendations, independent annotation comparison, measured follow-up, banking-first dashboard, and preserved research/cloud interfaces.

**Implemented but not established as beneficial:** graph next-request prediction evidence. It runs on the compatible banking source, but does not determine primary resource ranking because a localization advantage has not been established. The graph predictor was slightly worse than the identity model on normal held-out prediction error.

**Blocked / not implemented in this environment:** the PostgreSQL lock-contention experiment. No local PostgreSQL or Docker installation was found, and no safely isolated PostgreSQL database was provisioned. The endpoint refuses to start this scenario. No SQLite measurements are labelled PostgreSQL locks. The actual PostgreSQL lock injector and dedicated wait-monitoring experiment are not implemented or claimed as verified.

**Outside scope / not implemented:** real money, payment gateways, UPI, financial credentials, production bank authentication, Kubernetes deployment, new AWS infrastructure, cloud fault injection, autonomous remediation, proven causal identification, proven algorithmic novelty and production generalization. No new demo video was created for this final pass.

## 1. Working banking operations

The default screen is **Digital Banking Performance Intelligence**. Primary navigation contains only Digital Banking, Research Validation and Cloud Monitoring. The official project title remains exactly unchanged.

| Operation | Actual implementation and verification |
|---|---|
| Balance Enquiry | Banking API calls Account Service over loopback HTTP; validates a fictitious account and reads its stored integer-cent balance |
| Fund Transfer | Banking API calls Ledger Service; `BEGIN IMMEDIATE`, balance verification, conditional debit, credit and ledger insert execute atomically in the dedicated database |
| Transaction History | Account Service queries and returns actual test ledger entries, with measured SQL timing |
| Idempotent retry | Reusing a transfer ID with identical input returns the original transfer without another debit; different input returns conflict |
| Insufficient funds / concurrency | Transactions roll back on insufficient balance; concurrent debits cannot produce a negative balance; concurrent duplicate IDs execute once |

Only `test-a` and `test-b` are seeded, initially with 10,000,000 test cents each. These are fictitious balances and remain clearly labelled test units. Repeated startup does not reset balances or overwrite the ledger. No account credentials, real payment accounts or external financial services exist.

## 2. Actual deployment and data isolation

| Component | Address | Role |
|---|---|---|
| Banking API / existing dashboard backend | `127.0.0.1:8000` | UI, gateway HTTP calls, analytics and explicit local control routes |
| Account Service | `127.0.0.1:8101` | Balance and history |
| Ledger Service | `127.0.0.1:8102` | Transactional test fund transfer |
| SQLite database adapter | Local file access by the relevant process | Dedicated academic fallback, not PostgreSQL and not a cloud machine |

The services are separate FastAPI processes on one Windows machine. The graph shows only actual calls for the selected operation: API → Account → Database or API → Ledger → Database. It does not mix RCAEval service names into banking transactions.

`BANKING_DATA_DIR` controls the dedicated banking data directory. Default: `results/runtime/banking/` under the main project. It contains separate `accounts.db`, `telemetry.db` and `controls.db` files, local model checkpoints and server logs. It is ignored by Git. It never points to the existing observed analytics database or AWS PostgreSQL database by default.

## 3. Measured telemetry and timing meaning

Custom compatible tracing records real trace IDs, span IDs, parent IDs, operation names, timestamps, service/caller identity, process ID, monotonic durations and response status. HTTP propagation links real processes; database spans surround actual SQLite execution and fetch operations. No chart values are fabricated.

- Handler latency includes local execution and downstream HTTP work. It excludes final response serialization and final root-span export. It is not labelled complete network/client latency.
- The workload driver separately measures full client request duration and stores `client_latency_ms`.
- Exclusive processing subtracts the **union** of local child intervals, avoiding double-counting overlapping child time.
- SQL time includes execution/fetch and separately measured transaction statements, including commit. Summed SQL-span time is distinct from full ledger transaction time.
- Connection acquisition is separately timed. Trace export is batched outside the measured service span; downstream instrumentation overhead can still appear in caller HTTP duration and is disclosed.
- Process CPU time is measured over span intervals and is not presented as CPU utilization or saturation. Memory, throttling, packet loss, PostgreSQL wait/lock evidence and capacity limits are unavailable in the banking fallback.
- Request timestamps, success/error status and job counts allow observed workload throughput/accounting. These describe instrumented completed handlers; they are not a claim to count every possible rejected connection or pre-validation failure.
- Original milliseconds, integer test cents and timestamps are preserved. Chart lines break across intervals with no observed request; gaps are not invented measurements.

## 4. Frozen normal baseline

The verified normal collection issued **270 actual HTTP banking requests**: 90 balance enquiries, 90 transfers and 90 history requests, in fixed interleaved order, concurrency 1, seed 42 for account direction. UUIDs remain unique for idempotency and trace identity. The machine/OS/Python/CPU-count metadata and request counts are stored with the workload job.

The first 60% of normal requests define the reference, the next 20% calibrate the common robust-deviation threshold, and the final 20% are held out. Existing median/MAD evidence and two-point persistence rules are reused. The final threshold was approximately **75.1464**, selected from normal validation scores before controlled evaluation. It is an empirical detector threshold, not a fault probability or production SLO.

Held-out normal result: **0 false-positive requests / 54 requests**. This is a small, same-machine normal recording and does not establish a general false-alarm guarantee.

## 5. Controlled experiment and independent labels

The only active fault implementation is a deliberate application wait inside the dedicated Ledger Service. An operator must explicitly trigger it through the local UI or CLI. It defaults to 150 milliseconds per transfer for at most 12 seconds; accepted configuration is capped at 250 milliseconds and 30 seconds. The condition expires automatically, can be stopped, and is cleared in the workload's cleanup path. No workload or fault starts on application import/startup.

The condition changes actual execution using a bounded wait, not recorded metric values or chart coordinates. It is not described as CPU saturation or an organic application bug.

The separate control database holds the type, injected target, start, expiry, stop and independent label. The incident adapter reads measured request/span records and normal calibration only. It never reads the experiment button name, injected target, fault category or fault-start annotation. The frozen prediction is computed at the predeclared **tenth completed transfer** before the evaluator reads control annotations.

After cleanup, the driver executes 15 actual transfer requests. The final three relevant measured values are compared against the incident's frozen reference. An annotation match alone never creates a recovery result.

## 6. Actual banking evaluation results

Immutable report: `results/banking/measured_20261016/report.json`. `results/banking/FINAL.json` explicitly selects that report by checksum. New experiments refuse to overwrite an existing output directory; the frozen selection is not silently replaced by a newer run.

Three predeclared repetitions used the same frozen baseline, same 150-ms bounded condition, 12-second duration and checkpoint protocol. All repetitions are reported, including abstention/failure fields.

| Result | Observed |
|---|---:|
| Controlled repetitions | 3 |
| Performance degradation detected | 3 / 3 |
| Root-service Top-1 / Top-3 | 3 / 3; 3 / 3 |
| Mechanism annotation match | 3 / 3 |
| Joint service + mechanism match | 3 / 3 |
| Abstention | 0 / 3 |
| Measured return toward frozen reference | 3 / 3 |
| Normal held-out false-positive requests | 0 / 54 |

The matched service was **Ledger Service**, with **application processing delay**. Exclusive ledger processing distinguished origin work from inherited gateway/HTTP latency; database timing was retained as corroborating or competing evidence. It was not diagnosed by recognizing the experiment ID.

Normal median transfer-handler latency was **26.113 ms**. The three condition medians were **181.240 ms**, **167.189 ms** and **167.640 ms**, respectively. There were 45, 46 and 46 completed transfer requests within the independently recorded condition intervals. Boundary requests and post-condition requests are not relabelled to improve these numbers.

These results concern **one mechanism, three repetitions, one machine and a deliberate wait**. They are not production accuracy, proof of physical causality, broad banking validation or an improvement over a differently partitioned RCAEval benchmark. Additional browser-test runs are integration checks and are not pooled into this frozen three-case experiment report.

## 7. Banking graph model and non-graph comparison

The existing lightweight `MeasuredGraphAutoencoder` architecture is reused with fresh banking weights, a separate feature/domain contract and a **next-request target**. It is not called an exact GDN reproduction and does not transfer Alibaba weights.

Features: measured handler latency, exclusive processing, database SQL time and connection acquisition, with missing-value masks. Transfer requests provide 90 request windows: 54 training, 18 validation and 18 held-out. Means/scales use training points only. The models use the same seed 42, architecture, 100-epoch budget and validation weight selection. Directed call edges are preserved in the UI; message passing symmetrizes training-prefix edges and row-normalizes adjacency. Saved weights were round-trip checked.

| Banking normal next-request task | Identity feature model | Graph model |
|---|---:|---:|
| Held-out masked MSE | 0.574412 | 0.575263 |
| Evaluated held-out predictions | 17 | 17 |
| Normal residual false-alarm rate | 17.65% | 23.53% |
| Separate controlled residual Top-1 | 3 / 3 | 3 / 3 |

There is **no established graph advantage**. Top-3 is trivial over this three-resource transfer graph. The statistical detector's 0/54 result is a different task from the graph residual detector's 17 predictions and must not be conflated with it.

Compatible current transfer prefixes run real graph and identity inference, producing per-node and per-feature residuals. Source, calibration, node order, feature order, topology and training-time gates prevent unsupported inference. A historical prefix before training completion cannot use future-trained weights. The graph results are displayed as separate evidence, with `ranking_used=false`; primary root localization uses actual own-time attribution until incremental GNN localization value is independently established. Balance/history do not pretend to use this transfer-only GNN.

## 8. Detection, localization, explanation and TC-CFAO

The existing typed incident contract, detector, evidence gates, mechanism rules, recommendation contract and TC-CFAO are reused. Banking adds trace-based exclusive-time attribution so an inclusive caller slowdown alone does not outrank the component doing the excess work.

The visible flow is **Detect → Locate → Explain → Recommend → Verify**. The selected snapshot is identified and retained when an independent annotation is revealed. Service location, mechanism hypothesis, annotation match and measured recovery remain separate concepts. The displayed mechanism stays a hypothesis rather than being rewritten to the annotation.

Recommendations follow measured evidence: compare exclusive processing with downstream/database timing, inspect slow application work, and conditionally optimize the confirmed bottleneck. Latency does not automatically produce a database-lock recommendation.

Measured TC-CFAO follow-up scope in each of the three study cases was **3 fields across 2 resources**, compared with **8 fields across 3 resources** available after broad detection. This is inspection of existing measured fields, not measured total collection savings, altered sampling or AWS billing reduction. Actual additional external calls: 0. Transaction conditioning uses the actual banking path.

## 9. Preserved research and current AWS status

All original Alibaba, Microsoft, RE1/RE2 imports, data files, experiment reports, checkpoints, forecast methods and earlier scientific limitations remain unchanged. They are available under Research Validation. Earlier documentation is retained in `docs/RESEARCH_PLATFORM_V3.md`, `docs/ROOT_CAUSE_V4.md`, `docs/RESEARCH_FOUNDATION.md` and the archived pre-banking README/completion report.

The Microsoft F1 approximately 0.3269, original RCAEval service 60%/86.67%, weaker mechanism classification, negative Alibaba reconstruction comparison, tied small RE2 graph comparison and pre-injection false alarms remain visible. They are not presented as measurements from the banking test application.

Read-only AWS recheck on **16 October 2026, 14:07 UTC**: authentication succeeded in `us-east-1`, and EC2/RDS resource discovery returned HTTP 200. This differs from the historical denied-permission state, which remains preserved in earlier reports. The local operational status record is ignored by Git. CloudWatch collection and the existing EC2/PostgreSQL probe code remain preserved, but were not freshly exercised as part of the final banking study. No live AWS fault accuracy or recovery accuracy was established. A lightweight `SELECT 1` probe is never renamed as payment processing. No cloud infrastructure was created/changed and no cloud fault was executed.

## 10. Research foundation and attribution

Architectural reference: [Bank of Anthos](https://github.com/GoogleCloudPlatform/bank-of-anthos). This implementation uses the service-separation idea only; no upstream application code or Kubernetes deployment was copied. The existing FastAPI stack implements the local workload.

Methodological references: [MicroRCA](https://github.com/elastisys/MicroRCA) for service/resource evidence, [MicroRank](https://github.com/IntelligentDDS/MicroRank) for measured execution-path reasoning, [GDN](https://ojs.aaai.org/index.php/AAAI/article/view/16523) for graph prediction/deviation, and the existing verified Eadro, RCAEval and GNNExplainer references in `docs/RESEARCH_FOUNDATION.md`. The project does not claim to reproduce those complete algorithms or prove novelty/superiority.

## 11. Startup and exact Windows commands

Authoritative project:

```powershell
Set-Location 'D:\ExplainableAI_Cloud_Banking_Cloud_Project_2026_RESEARCH_V1\ExplainableAI_Cloud_Banking_Cloud_Project_2026'
```

One-time dependency/build setup, only when needed:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-benchmarks.txt
npm --prefix frontend ci
npm --prefix frontend run build
```

Start the complete banking application:

```powershell
.\scripts\start_banking.ps1
```

Equivalent command if PowerShell script policy disallows the wrapper (no security-policy change required):

```powershell
.\.venv\Scripts\python.exe scripts/start_banking.py
```

Open http://127.0.0.1:8000/. Keep the launcher open. Ctrl+C stops only its owned processes. It reuses verified existing services and never starts a workload or a fault. Logs are in the ignored banking runtime directory. The launcher was tested starting all three processes from stopped state.

Use a second terminal for explicit workloads:

```powershell
Set-Location 'D:\ExplainableAI_Cloud_Banking_Cloud_Project_2026_RESEARCH_V1\ExplainableAI_Cloud_Banking_Cloud_Project_2026'
.\.venv\Scripts\python.exe scripts/banking_workload.py --normal --per-operation 90
.\.venv\Scripts\python.exe scripts/banking_workload.py --application-delay --confirm-local-test --duration 12 --delay-ms 150
```

The normal command collects and freezes a new local normal baseline and trains compatible banking models. It does not overwrite the final three-case research report. The fault command explicitly triggers a bounded condition and prints independent verification after completion. The UI offers the same actions. Stop is available in the UI or by a local POST:

```powershell
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/banking/stop'
```

The PostgreSQL scenario is **not runnable in this fallback**. Its local endpoint `/api/banking/experiments/database-lock` returns a clear blocked response and starts nothing.

To repeat the declared measured study, choose a NEW output directory. Preserve `results/banking/FINAL.json`; review any new report before manually changing that frozen selection.

```powershell
.\.venv\Scripts\python.exe scripts/evaluate_banking.py --confirm-local-test --repetitions 3 --out results/banking/NEW_MEASURED_RUN
```

## 12. Four-to-five-minute faculty walkthrough

1. **0:00–0:40 — Open Digital Banking.** State that three local services perform academic banking operations with fictitious funds. Explain the SQLite fallback and independent AWS view.
2. **0:40–1:20 — Execute operations.** Select Balance Enquiry, Fund Transfer and Transaction History. Show actual responses/timings. Retry the same transfer ID to demonstrate no second debit.
3. **1:20–1:50 — Baseline.** Use an already completed normal collection, or run Collect normal baseline before the timed presentation. Show the frozen reference and 0/54 held-out result as a small local measurement, not a guarantee.
4. **1:50–2:50 — Explicit controlled delay.** Select Fund Transfer and Run 12-second application delay. Show measured request/ledger timing and the recorded service graph. Move through Detect and Locate; explain why own processing distinguishes the Ledger origin from inherited API latency.
5. **2:50–3:40 — Explain and recommend.** Show application-processing evidence, measured database comparison, missing corroboration and conditional corrective action. Complete the condition, reveal the independent annotation, and show actual later return toward reference. Do not equate annotation matching with causal recovery proof.
6. **3:40–4:20 — GNN role.** Expand the GNN details: compatible models really ran; identity MSE 0.5744 versus graph 0.5753. Explain why separate graph evidence was retained without giving it unvalidated control over ranking.
7. **4:20–5:00 — Research Validation and conclusion.** Show the three local repetitions separately from published benchmark results and their negative findings. State that PostgreSQL contention is blocked, not demonstrated. Conclude that the system connects measured banking performance to a plausible location, mechanism investigation, conditional action and independent verification.

## 13. Tests and final review evidence

- Initial baseline: 87 backend tests, 12 browser tests and frontend build passed.
- Final backend: **113 passed**, three existing deprecation warnings; 11.02 seconds in the final full regression.
- Browser: **16 passed**, including actual banking operations, duplicate handling, the full controlled banking investigation at 1366×768 and 1920×1080, preserved real benchmark replay, normal/insufficient states and authenticated-but-denied AWS rendering.
- Production build passed; the final UI was rebuilt after screenshot fixes. Two additional final visual checks passed at the required desktop sizes, with no horizontal page overflow.
- Real screenshots were inspected. The header badge and millisecond capitalization were corrected; chart lines no longer bridge long gaps without requests. Graphs use recorded calls and exclude unrelated benchmark nodes.
- Earlier tracked research results/checkpoints show no modifications. Raw account/trace databases, AWS snapshots, credentials, caches and local model runtime state remain excluded from Git and the source distribution.

Commands:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

The browser tests expect the documented local application to be running and a normal banking baseline to exist. They explicitly trigger only the bounded local academic delay. Backend fixture data uses temporary isolated databases and never enters the measured research report.

## 14. Final acceptance boundaries

The banking operations, real measurements, supported anomaly detection, plausible originating service, application-delay mechanism, explainability, recommendations, independent verification, measured follow-up, compatible graph computation, banking-first UI and Windows startup were verified.

The PostgreSQL contention scenario remains blocked/not implemented. Graph benefit, production reliability, generalized mechanism accuracy, broad fault coverage, causal identification, live AWS banking deployment and independent AWS fault accuracy remain unestablished. This is the final implemented review build with those explicit limitations, not a claim that every possible project objective passed.
