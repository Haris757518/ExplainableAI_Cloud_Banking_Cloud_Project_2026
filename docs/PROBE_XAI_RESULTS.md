# PROBE XAI measured results

Study date: 22 October 2026. Status: implemented and evaluated on recorded benchmarks; banking workload execution remains pending.

## Data and protocol

The study contains 15 RE2-OB recordings. Five prior recordings and results are preserved. Ten additional cases were selected by a declared lexicographic rule before analysis, across CPU, memory, disk, delay and loss. Each retains official pinned source and file checksums. This is a bounded compatibility sample, not a representative independent test set.

Both next-step model variants use identical features, seeds, architecture and per-recording chronological training and validation. Recorded graph edges are restricted to completed training-prefix parent-child spans. All 15 validation cutoffs preceded the independently annotated injection, checked only after predictions. There is no claimed model transfer to banking workloads.

## Four method comparison

| Method | Top 1 | Top 3 | Mechanism agreement | Mean followup columns | Driver abstention |
| --- | --- | --- | --- | --- | --- |
| statistical baseline | 0.733 | 1.000 | 0.000 | 0.0 | 1.000 |
| gnn only | 0.600 | 0.867 | 0.000 | 0.0 | 1.000 |
| gnn conventional diagnosis | 0.600 | 0.867 | 0.133 | 4.8 | 1.000 |
| gnn probe xai | 0.600 | 0.867 | 0.133 | 2.0 | 1.000 |

GNN identity comparison: Top-1 0.6, Top-3 0.9333333333333333. Recorded graph: Top-1 0.6, Top-3 0.8666666666666667. No graph advantage is established.

PROBE-XAI uses 2.0 follow-up columns on average versus 4.8 under conventional diagnosis, with unchanged root-service accuracy and mechanism agreement on this sample. These count recorded in-memory columns, not live diagnostic requests or AWS cost. This supports a bounded implementation-effort observation, not a proven research novelty or generalizable benefit.

## Detection limitations

At fixed checkpoints, 11 of 15 pre-injection windows raised alerts. All 15 selected post-injection checkpoints raised alerts. High pre-injection alerting is a material limitation. These checkpoint counts are not pointwise precision/recall, reliable onset detection or banking fault coverage.

Underlying-driver accuracy and unsupported-diagnosis rate are unavailable because the external benchmark annotations do not independently label demand, retries or code-level explanations. Every method abstained from claiming a deeper driver. That is a scientific boundary, not evidence of perfect diagnosis.

## Software and deployment status

The dashboard now provides the investigation narrative without raw JSON in the main view. It exposes supporting measurements and missing alternatives under All evidence. Recommendations are read-only suggestions. Recovery cannot become Recovered without an approved executed intervention, later performance measurements and later banking-integrity checks.

No new AWS compute or other billable resources were created. Existing S3 and importer-health evidence remains separate. EKS and EC2 discovery were denied. The official Anthos source and prepared manifests are present, but the workload has not been run; provider-neutral instrumentation and runtime verification remain required.

The complete final Python suite passed 178 tests. The targeted 21-test investigation and contract suite also passed. Three browser workflow tests and the production frontend build passed. Original result and checkpoint checksums are verified separately.

## Next experimental milestone

The user has approved local Bank of Anthos on Docker Desktop Kubernetes with large files on D:. Setup is in progress; no banking transfer is verified yet. Complete the [first-execution gate](LOCAL_COMPLETION_PROTOCOL.md), instrument actual arrivals, queues, per-request CPU, worker capacity, traces and transaction outcomes, then record a normal baseline and a bounded high-demand condition. A high-demand injection label must stay outside inference. If measured CPU or queue saturation does not occur, report the result and abstain rather than manufacture a successful chain. Cloud execution requires separately approved resources, permissions, cost cap and cleanup deadline.
