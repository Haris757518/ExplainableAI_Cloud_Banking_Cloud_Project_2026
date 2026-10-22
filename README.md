> **22 October redesign:** Start with [REDESIGN_README.md](REDESIGN_README.md). The application now has two primary modes and imported Monzo/Starling history. The documentation below describes the preserved earlier implementation.

# Explainable AI-Based Cloud Performance Analytics for Digital Banking using Graph Neural Networks

An instrumented academic banking application for measured performance investigation. Balance enquiries, atomic/idempotent test transfers and transaction history execute through separate local FastAPI processes. The dashboard connects detection, resource localization, mechanism evidence, recommendations and independent verification.

**Test funds only.** The banking database is a dedicated SQLite fallback, separate from existing analytics and AWS databases. PostgreSQL lock-contention validation is blocked. The application-delay scenario is implemented, bounded and measured; no cloud fault is triggered.

## Start on Windows

From this project directory, with Python 3.12 and Node.js installed:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-benchmarks.txt
npm --prefix frontend ci
npm --prefix frontend run build
.\.venv\Scripts\python.exe scripts/start_banking.py
```

For the existing prepared checkout, simply run:

```powershell
Set-Location 'D:\ExplainableAI_Cloud_Banking_Cloud_Project_2026_RESEARCH_V1\ExplainableAI_Cloud_Banking_Cloud_Project_2026'
.\scripts\start_banking.ps1
```

Open [the local dashboard](http://127.0.0.1:8000/). Keep the launcher open; Ctrl+C stops its owned processes. It starts/reuses API port 8000, Account port 8101 and Ledger port 8102. **Startup never runs a workload or fault.** The final source package also contains the built frontend; rebuilding it is optional when using that exact package.

## Collect normal measurements and run the supported experiment

In a second terminal from the project directory:

```powershell
.\.venv\Scripts\python.exe scripts/banking_workload.py --normal --per-operation 90
.\.venv\Scripts\python.exe scripts/banking_workload.py --application-delay --confirm-local-test --duration 12 --delay-ms 150
```

The same actions are available on Digital Banking. Choose Balance Enquiry, Fund Transfer or Transaction History to execute individual operations. Fictitious accounts are seeded once; startup preserves their ledger. Repeating a transfer ID does not debit twice.

The normal workload collects 270 actual requests and freezes chronological 60/20/20 calibration before fault evaluation. The explicit experiment waits inside the real local Ledger Service, automatically expires and collects actual follow-up. Use the UI Stop button or:

```powershell
Invoke-RestMethod -Method Post -Uri 'http://127.0.0.1:8000/api/banking/stop'
```

`BANKING_DATA_DIR` optionally selects a dedicated local runtime directory. Its default, `results/runtime/banking/`, is ignored by Git. No AWS credentials are needed for banking. This build does not provision PostgreSQL or use an AWS database for contention experiments.

## Verified findings

| Independent local measurement | Result |
|---|---:|
| Normal held-out false-positive requests | 0 / 54 |
| Controlled application-delay repetitions | 3 |
| Degradation / service / mechanism matches | 3 / 3 for each |
| Measured return toward frozen reference | 3 / 3 |
| Identity versus graph next-request MSE | 0.574412 versus 0.575263 |
| Follow-up fields examined | 3 of 8 across 2 of 3 available resources |

These are small same-machine results for one deliberately bounded mechanism, not production accuracy or causal proof. The graph model did not establish an advantage and does not control the primary root-service ranking. Compatible graph/identity inference is displayed separately; no Alibaba weights are transferred. PostgreSQL locks, real AWS failure/recovery and production generalization are unvalidated.

The frozen local study is [results/banking/measured_20261016/report.json](results/banking/measured_20261016/report.json). Earlier Alibaba, Microsoft and RCAEval results remain unchanged under Research Validation; their false alarms and negative model findings remain accessible. Cloud Monitoring preserves the independent AWS integration. Current authentication/resource discovery passed; CloudWatch collection was not freshly evaluated in this completion pass.

## Verify

```powershell
.\.venv\Scripts\python.exe -m pytest -q
npm --prefix frontend run build
npm --prefix frontend run test:e2e
```

Recorded final checks: **113 backend tests and 16 browser tests passed**, with screenshots inspected at both required desktop resolutions. Browser banking tests require running services and a frozen normal baseline and explicitly execute the bounded local test condition.

## Authoritative handover

See [docs/FINAL_HANDOVER.md](docs/FINAL_HANDOVER.md) for architecture, telemetry semantics, actual model results, scope/blocked items, exact reproduction commands and a four-to-five-minute faculty walkthrough. [COMPLETION_REPORT.md](COMPLETION_REPORT.md) provides the acceptance summary.

Historical documentation remains in [Research V3](docs/RESEARCH_PLATFORM_V3.md), [root-cause redesign](docs/ROOT_CAUSE_V4.md) and [research foundation](docs/RESEARCH_FOUNDATION.md); pre-banking README/completion snapshots are archived under `docs/archive/`. Do not treat those historical status notes as the current setup guide.
