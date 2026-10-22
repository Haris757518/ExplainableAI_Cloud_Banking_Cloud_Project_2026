# Local completion protocol

Status: setup in progress on 22 October 2026. This document specifies planned
experiments; it does not assert that Docker, Kubernetes, Anthos, a transfer, or an
experiment has run. No AWS compute or additional spending is authorized.

## First execution gate

The project remains in its current `redesigned_project` directory. Large setup
files, Docker data, research datasets and outputs belong in `D:\BankingResearch`.
WSL is capped at 12 GB RAM and six processors, with a 2 GB swap file on D:.
Before any image pull, verify the actual Docker disk image location on D:.

Use only the `docker-desktop` context and the dedicated
`banking-probe-research` namespace. The prepared manifests disable GCP tracing
and metrics exporters, use ClusterIP services and set loadgenerator replicas to
zero. The upstream public JWT key is strictly a local demo key. Expose the
frontend using a port forward bound to `127.0.0.1`.

Before more AI implementation: verify healthy services and databases, execute a
uniquely identified test transfer, verify that exact transfer in history and the
ledger, and capture measured service calls. A successful HTTP redirect alone is
insufficient. Save raw evidence and the commands that obtained it. Application
logs alone are not distributed traces; traces must contain actual span and
parent identities. Missing trace coverage must remain explicit.

## Measurement contract

Record timestamped request arrivals, completed requests, failures, concurrency,
service latency, process/container CPU time, CPU throttling, resource limits,
worker capacity, queue waits, SQL execution/lock waits, trace identities, and
transfer outcomes wherever directly measurable. Preserve the raw source, units,
sampling interval, collection overhead and checksums. Do not substitute CPU
utilization for CPU time per transaction or infer queue length from latency.

Data belongs in `D:\BankingResearch\Telemetry\{normal,heavy_transactions,
reduced_cpu,db_contention,recovery}`. Keep experiment commands, intervention
times and injected-driver labels separate from diagnostic inputs. A configuration
limit is evidence of assigned capacity, not a direct measurement of useful
throughput. An unavailable field stays unavailable.

## Controlled runs

1. Normal: warm up, then measure multiple independent normal runs with fixed
   traffic. Verify ledger totals and unique request identities.
2. Heavy transactions: increase arrivals while preserving resource allocation.
   Record offered and completed rates, queues, per-request CPU and throttling.
3. Reduced CPU: reduce one service's CPU allocation while keeping comparable
   offered traffic and database state. Record actual throttling and throughput.
4. Database contention: create a bounded, reversible lock only in the local demo
   database; record the owning and waiting sessions and SQL wait durations.
5. Recovery: restore each intervention, measure at least three later performance
   observations, and verify no duplicate processing, pending-payment consistency
   and ledger reconciliation. Do not report recovery from lower latency alone.

At least two different measured drivers plus recovery are required for final
acceptance. If Anthos cannot run reliably, document the blocker and use the
authorized lightweight banking fallback with an explicit source label.

## Research protocol, to implement after the first execution gate

Expand RE2 using the pinned official RCAEval revision, including Online Boutique
and Train Ticket. Choose cases before examining outcomes. Preserve original
downloads and prior results. Keep every recording and all windows from it in
one split. Also report a stricter grouping by system/service/fault family when
there are enough independent groups; report group counts and exclusions.
Previously inspected 15 recordings are development evidence, not untouched
final tests. Freeze a new held-out set before fitting or tuning.

Fit preprocessing, detector thresholds, persistence rules and calibration using
training data; choose settings on validation data only. Freeze them before final
testing. The earlier 11 alerts at 15 normal checkpoints are a known limitation,
not a resolved result. Report normal-run false alerts per time, event detection
rate, detection delay, localization Top-1/Top-3, and uncertainty. Account for
dependence between windows; do not treat overlapping windows as independent
experiments. A checkpoint alert count is not pointwise precision or recall.

Compare statistical detection/localization, GNN only, GNN with conventional
fixed follow-ups, and GNN with PROBE-XAI. Include the same architecture with
identity adjacency, equal information budgets, missing-field ablations and
fixed seeds. Separate real external reads/bytes/time from in-memory field
inspection. Preserve negative results. Do not assert GNN superiority or novelty
from the current illustrative study. Evaluate driver accuracy only where
independent injected-driver truth exists; otherwise report abstention and
evidence coverage rather than fabricated accuracy.

## Preservation and cleanup

Maintain `D:\BankingResearch\component-inventory.json` and an evidence index
with component origins, versions, paths, checksums and runtime status. Final
deliverables must identify which results are recorded benchmark replay, actual
local banking execution, and existing AWS storage verification.

Before deletion, present exact owned paths, their measured sizes, retained
datasets/models/reports, and the recovery procedure for approval. Retain existing
project results, source history and raw measurements. Do not prune all Docker
volumes, remove unrelated images, or unregister any WSL distribution without
ownership verification and explicit cleanup approval.
