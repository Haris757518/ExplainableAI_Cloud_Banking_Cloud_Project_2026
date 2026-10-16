# AWS banking telemetry integration

The existing academic banking services run locally. Their observed measurements can now be published explicitly to `ExplainableAI/Banking` in `us-east-1` and retrieved independently of EC2/RDS discovery. No banking service is claimed to be hosted on AWS.

## Verified on 16 October 2026

- Existing AWS session authenticated successfully in `us-east-1`.
- Discovery: one running EC2 instance; zero RDS databases. Existing infrastructure collection returned three metric series without API errors.
- After explicit user approval, ten already measured requests were published as 118 individual metric values, with original timestamps, standard resolution and only Environment/Service/Operation dimensions.
- First read returned 13 series during propagation; subsequent independent reads returned 30 series across eight metric types. CloudWatch request totals were balance 4, transfer 3, history 3, matching the ten published requests. This small historical subset is not a fresh workload or an additional research experiment.
- The dashboard offers operation and metric selectors, request/error counts, latency/service/database histories, publication checkpoint preview, collection status, and missing-data evidence.
- Insufficient time windows correctly produce `insufficient_evidence`; root cause and causal recovery remain `not_established`. No GNN weights are applied to aggregated CloudWatch metrics.
- Backend: 124 tests passed; production frontend build passed. Live browser checks verified all three operation selections, metric selection, provenance and returned measurements. Existing banking balances, selected frozen report and 48 protected artifact hashes were unchanged.

## Commands from the project folder

```powershell
.\.venv\Scripts\python.exe -c "from common.config import get_settings; from aws.discovery import AWSDiscovery; s=get_settings(); r=AWSDiscovery(s.aws_region,s.profile).status(); print({k:v for k,v in r.items() if k!='account_id'})"
.\.venv\Scripts\python.exe -c "from common.config import get_settings; from aws.discovery import AWSDiscovery; s=get_settings(); d=AWSDiscovery(s.aws_region,s.profile); print('Region:',s.aws_region); print('EC2:',len(d.discover_ec2())); print('RDS:',len(d.discover_rds()))"
.\scripts\start_banking.ps1
.\.venv\Scripts\python.exe scripts/aws_banking_telemetry.py --dry-run --limit 10
# Explicitly requested publication only; the following advances to the NEXT unpublished requests.
.\.venv\Scripts\python.exe scripts/aws_banking_telemetry.py --publish --confirm-publish --limit 10
.\.venv\Scripts\python.exe scripts/aws_banking_telemetry.py --read --lookback-minutes 1440
.\.venv\Scripts\python.exe -m pytest -q
npm --prefix frontend run build
```

Open `http://127.0.0.1:8000`, select **Cloud Monitoring**, and click **Read banking CloudWatch**. The banking panel is independent of the existing **Analyze observed data** infrastructure workflow. Restart the backend after installing the changes; already running Python processes retain their earlier imported code. The isolated review server used for the screenshots is `http://127.0.0.1:8200` and leaves existing services untouched.

API: `GET /api/aws/banking/preview`, `GET /api/aws/banking/metrics?lookback_minutes=1440`. There is no publication API, startup hook, scheduled publisher or automatic fault injection.

Optional `AWS_BANKING_TELEMETRY_DB` selects a read-only telemetry source for the preview; the default is `BANKING_DATA_DIR/telemetry.db` or the existing project runtime path. CLI `--database` and `--checkpoint` permit explicit isolated sources. No `.env` values were changed.

## Measurement and retry semantics

RequestCount and ErrorCount represent completed measured handlers. Latency metrics preserve their source units and individual timestamps; CloudWatch computes 60-second Sum counts and Average timings from the original samples. Database execution metrics are per SQL span, not total per-transaction database time. Handler time, client round-trip time, service time and exclusive processing are distinct. Missing client or span values are omitted, never invented.

Only observed rows in the existing telemetry database are read, using SQLite read-only mode. No accounts, balances, transfer IDs, trace IDs, span IDs, credentials or raw payloads enter CloudWatch dimensions or values. Batches are bounded to one measured request per API call, at most 20 requests per CLI invocation; default ten. No per-request dimension exists. Custom metric charges are possible even for small values; the bounded dimension set limits cardinality.

The persistent runtime checkpoint advances only after confirmed success. It is keyed by telemetry source and region. Definite AWS rejections retain the failed sequence for a safe retry; successful earlier sequences are not resent. CloudWatch has no idempotency key: a network error or process interruption after a send is ambiguous. Its durable pending intent blocks automatic replay. Automatic SDK write retries are disabled. A cross-process lock covers sends and checkpoint commits. Do not clear pending rows or delete/reuse checkpoints blindly; verify the uncertain CloudWatch bucket and source before manual reconciliation. A hard process crash can leave a stale lock, intentionally requiring inspection. Exactly-once delivery across arbitrary network failure is not claimed.

The collector preserves dimensions, source, region, units, statistic, timestamps, sampling period, empty/missing status, response completeness and API message codes. Pagination is bounded. Earlier controlled AWS trials before `2026-10-16T08:05:00Z` remain excluded. Missing RDS resources do not affect custom banking reads. The new banking metrics remain separate from existing `ExplainableAI/ObservedLab` probe observations.

## Analysis limits and troubleshooting

The provisional AWS analysis requires at least ten complete observed minute windows per series. It uses the earliest 60% as an exploratory reference, a median/MAD threshold, two-point persistence and a three-minute freshness gate. It does not reuse the frozen local detector calibration, claim a verified normal production baseline, infer a root cause from aggregates, or join local banking measurements to an unrelated EC2/RDS resource. Collect separately verified normal windows and matched traces before making a mechanism claim.

`AccessDenied` indicates the reported AWS API permission is unavailable; no IAM policies are changed. `ExpiredToken` requires normal session refresh. Empty datapoints may reflect publication propagation, wrong region, original measurement timestamps outside the read window, or an unpublished metric. Perform a bounded fresh read rather than republishing the same rows. Old observations are never re-timestamped. Lookback is capped at 14 days. This verification used existing data only and did not change the ledger or start controlled delays.

## Changed implementation files

- `aws/banking_publisher.py`
- `aws/banking_cloudwatch.py`
- `aws/cloudwatch_adapter.py` (additive banking collector method)
- `backend/aws_banking_api.py`
- `backend/main.py` (register AWS-only routes)
- `frontend/src/AwsBankingPanel.jsx`
- `frontend/src/ReferenceConsole.jsx` (Cloud Monitoring-only panel mount)
- `scripts/aws_banking_telemetry.py`
- `tests/test_aws_banking_integration.py`

Supporting evidence: `docs/aws_banking_evidence/`; the existing report is revised under its original filename rather than replaced with a new report series.
