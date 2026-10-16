# Optional high-resolution AWS banking anomaly demonstration

This opt-in demonstration extends commit `9866df1` without replacing its standard 60-second metrics, publisher checkpoint, banking APIs, ledger logic, models or frozen research results. The banking workload runs locally; AWS stores actual measured timings and counts. No AWS infrastructure fault, resource change or cloud banking hosting is implied.

## Protocol and authorization

Preparing a session records the current maximum measured request sequence and creates a separate persistent checkpoint under `results/runtime/aws-demo/<session>/`. It performs no transfers and publishes no metrics. The normal checkpoint `results/runtime/aws-banking-checkpoint.db` is not reset or advanced by this demonstration.

Running requires **all three confirmations**: `--confirm-test-transfers`, `--confirm-publish`, and `--confirm-local-delay`. Obtain explicit operator authorization before executing the run. Each complete run performs at most 60 one-cent fictitious test transfers, alternating direction through the existing local Banking API. Successful even-length runs have equal transfer counts in both directions; ledger entries are genuine new test operations and are not deleted afterwards. No balances are changed directly. A failed or interrupted run can leave a partial set of valid test transfers; the report distinguishes attempted and observed requests and does not undo or fabricate history.

The fixed protocol is:

1. Capture the existing request backlog boundary during preparation.
2. Execute four independently paced supported transfers in each of ten consecutive, complete 10-second normal windows: forty measured normal requests.
3. Publish only the session's new measured sequence manifest, using `StorageResolution=1`, namespace `ExplainableAI/Banking`, and fixed environment `academic-local-demo-10s`. No session or request identifier becomes a CloudWatch dimension. Original timestamps and units remain unchanged. At most 2,000 raw metric values may be published in a run.
4. Retrieve normal data with `GetMetricData` at 10-second periods. Validate request counts, sample counts, SQL-span sample counts, exact timestamps, chronological spacing and API completeness. Missing or duplicated samples block readiness. Freeze six reference and four calibration windows before any condition starts. Publication propagation is polled at most six times, ten seconds apart; pending data remains pending.
5. Invoke the existing `banking.store.experiment_start` operation with a 200-ms local Ledger Service wait and its existing 30-second maximum. Start before an aligned period and observe four transfers per period across two complete consecutive periods. Stop only this run's owned active condition using the existing stop operation. No new banking transaction or fault implementation is introduced.
6. Collect three subsequent complete periods, four real transfers each, after the condition is stopped. Read CloudWatch again and evaluate against the frozen normal reference. Preserve raw CloudWatch timestamps, counts, baseline statistics, per-feature scores, complete/missing periods, original local span corroboration, and follow-up readings in the session report.

Normal, controlled and follow-up phases contain 40, 8 and 12 measured requests respectively when a full run completes. These are protocol targets, not claims that a run succeeded. Consult the actual `report.json` for observed results. New demo sessions do not become frozen research experiments automatically.

## Windows PowerShell commands

From the existing project folder, ensure the normal Banking API, Account Service and Ledger Service are running:

```powershell
Set-Location 'D:\ExplainableAI_Cloud_Banking_Cloud_Project_2026_RESEARCH_V1\ExplainableAI_Cloud_Banking_Cloud_Project_2026'
.\scripts\start_banking.ps1
```

Keep the services running, and use another PowerShell window for the following. Choose a new session name for a new run:

```powershell
$demoSession = 'faculty-demo-' + (Get-Date -Format 'yyyyMMdd-HHmmss')
.\.venv\Scripts\python.exe scripts/aws_banking_demo.py --prepare --session $demoSession
```

Review the prepared session and obtain explicit authorization for the test transfers, bounded local delay and AWS publication. Then, and only then:

```powershell
.\.venv\Scripts\python.exe scripts/aws_banking_demo.py --run --session $demoSession --confirm-test-transfers --confirm-publish --confirm-local-delay
Get-Content -LiteralPath "results\runtime\aws-demo\$demoSession\report.json"
```

The run normally takes several minutes because a genuine forty-request normal reference spans at least 100 seconds. It does not compress time or replay old observations as new. The 30-second local condition is automatically bounded even if the client exits; cleanup stops an owned active condition when possible.

For a read-only follow-up after propagation, with no additional transfers, no new condition and no publication:

```powershell
.\.venv\Scripts\python.exe scripts/aws_banking_demo.py --refresh --session $demoSession
```

If baseline data is pending, the same `--run` command can continue from `awaiting_baseline_cloudwatch` within the freshness limit. It does not repeat baseline transfers. A stale baseline, an ambiguous publication, or a partially interrupted transfer phase must be inspected; do not delete or reset its checkpoint to force success. A fresh run requires a new session and new operator authorization. Avoid starting any other workload or manually triggering another local condition during a demo.

## Dashboard

Restart the backend after installing the new routes and refresh the built frontend. In **Cloud Monitoring**, expand **Optional high-resolution AWS anomaly demo** and click **Load latest AWS demo evidence**. This reads saved measured evidence only; it cannot start a run or publish metrics.

The optional section displays the actual session status, baseline, CloudWatch histories, detected consecutive periods, affected service, local span corroboration and post-condition readings. Snapshot time and age are visible. A saved successful experiment is historical evidence and does not assert that a fault is still active. The existing standard-resolution banking and infrastructure views remain separate. `GET /api/aws/banking/demo/latest` returns the current saved demo report without local source paths or per-request identifiers.

## Detector and scope

The normal reference is frozen from ten complete windows: six chronological reference windows and four calibration windows. For each feature the threshold is the larger of the robust median plus a margin (at least 25 ms, 75% of the median, or six scaled MADs) and 110% of the largest calibration value. API latency, exclusive Ledger processing, and SQL execution per measured request are separate measurements. SQL execution is the CloudWatch sum of genuine SQL spans divided by the observed request count; it is not relabelled client or service latency.

Detection requires both API latency and Ledger exclusive processing to exceed their frozen thresholds in two consecutive, complete 10-second periods, with matching measured sample counts and zero measured errors. Missing, partial, stale, future or nonconsecutive observations cannot establish a detection. The freshness bound is 180 seconds after a period ends. The feature score is `(observed - normal median) / (threshold - normal median)`, with values over one crossing the feature threshold.

The detector receives CloudWatch readings and the frozen normal reference, not the controlled experiment annotation. Control audit metadata is saved separately. Original local HTTP/SQL spans are matched to the independently detected timestamps for corroboration after evaluation. GNN inference is not used for this AWS detector. The affected service may be `ledger-service`, but confirmed causal root cause stays `not_established`. Follow-up requires two consecutive complete later periods returning below the reference thresholds and is measured return toward reference, not proof of causal recovery.

The exploratory thresholds and small, deliberately controlled test do not establish general anomaly accuracy, production reliability or GNN superiority. The reliable existing Digital Banking experiment remains available if AWS credentials, permissions, propagation or timing prevent a live demonstration.

## Evidence and checks

Each session retains `session.json`, `report.json`, the independent `baseline.json`, `checkpoint.db` and (only after authorization and actual invocation) `control_audit.json`. A dashboard pointer under `results/runtime/aws-demo/LATEST.json` selects only this optional demo, never the frozen research report. Runtime artifacts remain ignored by Git; publish only reviewed, sanitized copies if specifically authorized.

```powershell
.\.venv\Scripts\python.exe -m pytest -q
.\.venv\Scripts\python.exe -m pytest -q tests/test_banking.py tests/test_aws_banking_integration.py tests/test_aws_banking_demo.py
npm --prefix frontend run build
```

AWS reference documentation: [PutMetricData](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_PutMetricData.html), [MetricStat periods](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_MetricStat.html), and [GetMetricData retention and timestamp behavior](https://docs.aws.amazon.com/AmazonCloudWatch/latest/APIReference/API_GetMetricData.html). High-resolution datapoints have shorter fine-grained retention than standard metrics; preserve the observed experiment report instead of relying on fine-grained retrieval indefinitely.

## Current implementation validation

The initial implementation check passed 142 backend tests, including all existing banking/AWS checks, and the frontend production build. Those isolated tests do not count as live measurements. A prepared session is not a completed live experiment. Live results must be reported separately with actual request totals, CloudWatch completeness and detected or missing evidence; never substitute the protocol targets above for observed results.


## Verified measured run on 16 October 2026

Session `faculty-aws-demo-20261016-02` completed after separate explicit authorization. Its backlog boundary was sequence 1180. It collected forty normal transfers in ten complete consecutive 10-second windows, froze the independently retrieved CloudWatch reference, then recorded eight transfers during two controlled periods and twelve follow-up transfers. All sixty supported one-cent transfers were published as **900 actual metric values**; CloudWatch returned **15 complete periods**, with matching source sample counts and no API errors.

The reference was frozen at **17:01:19.699967 UTC (22:31:19.699967 IST)** before the local condition. API latency baseline median was **46.104 ms**, with threshold **80.681 ms**. Exclusive Ledger baseline median was **4.111 ms**, with threshold **29.111 ms**. SQL execution per request baseline median was **30.576 ms**, with threshold **55.576 ms**.

The detector identified the consecutive periods starting **17:01:30 and 17:01:40 UTC (22:31:30 and 22:31:40 IST)**. Actual API averages were **246.440 and 238.109 ms**. Actual exclusive Ledger averages were **204.423 and 205.076 ms**. API normalized scores were **5.794 and 5.553**; Ledger scores were **8.012 and 8.039**. SQL execution per request did not cross its threshold. The affected service was `ledger-service`; confirmed causal root cause remained `not_established` and no GNN weights were used.

The subsequent periods starting **17:01:50 and 17:02:00 UTC** met the measured return rule: API averages **50.482 and 46.073 ms**, Ledger exclusive averages **4.215 and 8.981 ms**. These are observed follow-up readings, not proof of causal recovery. Timestamp-matched local spans independently corroborated eight incident requests, with mean API **242.274 ms**, Ledger exclusive **204.749 ms**, and SQL execution **25.617 ms per request**.

A preliminary session was stopped before any delay after eight actual transfers because interleaved AWS publication disrupted the next normal window's sample spacing. Four requests had been published. Its evidence is retained and excluded from the completed study. The fix moves AWS sends outside timed measurement phases and drains the isolated checkpoint in bounded groups; it does not relax the failed data's validation criteria or relabel it as successful.

Final validation: **143 backend tests passed**, including all existing banking and standard AWS tests; frontend production build passed. Live browser checks showed the measured frozen baseline, positive deviation, actual histories, affected service, local spans and follow-up. The **73 protected files** were unchanged, including the original standard checkpoint and historical tests. All **625 pre-existing ledger rows** were independently compared with the pre-demo snapshot and preserved; original test-account balances were unchanged after alternating transfers. The authorized local condition is stopped.

Reviewed local evidence is under `docs/aws_demo_evidence/`: measured experiment JSON, frozen normal reference, preliminary-attempt audit, integrity/ledger verification and real dashboard screenshots. No GitHub push was performed for this extension; implementation and results await user review.
