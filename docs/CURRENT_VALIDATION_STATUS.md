# Current validation — 23 October 2026

This status supersedes earlier milestone statements about the reader correction and banking GNN implementation. The bounded research prototype and its controlled validation are complete; the generalization and novelty limits below remain explicit.

## Implemented and verified

The dashboard presents the problem, affected service, immediate mechanism, deeper explanation, action and recovery evidence in ordinary language. It keeps uncertain causes explicit and offers a readable investigation download.

The balance and transaction-history readers now query committed ledger records directly. They no longer serve account results from a cache that can skip a lower-numbered transaction when it commits later. History ordering is deterministic. This correctness-first change performs more database work and has not been certified for production capacity.

The isolated AWS/PostgreSQL test reproduced the issue in all three original-code trials. Corrected code passed all three trials; both account balances and histories agreed with the ledger, including after reader restarts. Deployed class checksums match the locally validated build. Nineteen Java tests passed. The retained proof is in `results/correctness_fix/aws-proof/`, independently checked by `analysis/banking_followup.py` before the dashboard claims verification.

## Model and investigation findings

The initial banking GNN study ranked the wrong service at both evaluated fault checkpoints. Those original results are preserved in `results/banking_study/v1/`. The revised investigator consults measured processor limits and database blocking instead of interpreting the largest model deviation as the cause. It identifies the expected service in both inspected development cases. This is a development regression result, not independent accuracy.

The RE2 detector calibration audit reduced normal-checkpoint alerts from 11 to zero across 15 already inspected recordings. It detected 13 of 15 fault checkpoints and missed two. Precision was 1.0, recall 0.867 and F1 0.929 at these checkpoints. These results are retrospective and do not establish a production false-positive rate.

## Verified new repeat evaluation

The new run submitted **8,475 requests**, with **8,475 unique matching ledger records**. Callers received 6,946 recorded success acknowledgements; 1,505 outcomes were uncertain and 24 other responses were not classified as successful acknowledgements. All planned CPU and database repetitions were scored at the frozen checkpoints.

| Variant | Seed | GNN ranking correct | Evidence localization correct | Detected faults |
| --- | --- | --- | --- | --- |
| Graph | 42 | 3 of 6 | 6 of 6 | 6 of 6 |
| Graph | 43 | 3 of 6 | 6 of 6 | 6 of 6 |
| Graph | 44 | 3 of 6 | 6 of 6 | 6 of 6 |
| Identity | 42 | 0 of 6 | 6 of 6 | 2 of 6 |
| Identity | 43 | 0 of 6 | 6 of 6 | 1 of 6 |
| Identity | 44 | 0 of 6 | 6 of 6 | 6 of 6 |

The graph models raised zero alerts in 36 observed normal-holdout bins for each seed. These are a short normal holdout and six controlled fault repetitions within one workload, not independent applications or production reliability. The direct-evidence localizer is shared by the graph and identity variants; it does not require a GNN alert to inspect measured slowdown.

Three later application transfers were verified. Both account balances matched the ledger, the tested transfers were present in history, returned history IDs were unique, three balance reads succeeded, database blocking was absent and processor allowance was restored. The final archive checksum and SQL backup were verified before terminating the exact research instance. Its root disk deletion is confirmed; the existing payment server was preserved.

The final archive SHA256 is `4032bb593ef3573a044759d83c0a9633191453fcc031237acaf826adb9052aab`. Portable raw inputs, checkpoint hashes, frozen predictions, final scores and cleanup evidence are under `results/final_validation/`. `python scripts/recompute_final_checks.py` independently recomputed the accounting, direct-evidence localization and later recovery checks from this bundle.

## Prior run whose raw export was missed

The subsequent AWS workload completed 8,475 submissions. Its retained command summary reports 8,475 unique ledger matches and 6,896 acknowledged successes. A matching ledger record does not establish that the caller received success.

The complete raw measurements were not exported before automatic instance shutdown. The instance is no longer returned by EC2 and no volumes tagged for this run remain. The earlier correction-proof archive is safely retained. The later command summary cannot substitute for raw measurements, so no repeat-workload localization accuracy is reported. See `results/final_validation/evidence-availability.json` and the retained command output. This prior run remains excluded from localization scoring. The new automatically exported run above completed the repeat evaluation.

The unrelated existing payment server was observed running and was not modified. No new instance was launched during the refreshed-credential check.

## Contribution and limits

The proposed PROBE-XAI contribution combines progressive evidence inspection, separate symptom and cause rankings, explanations limited to measured evidence, and a transaction-integrity recovery gate. In the original controlled workload, fast responses would have declared recovery while a balance remained wrong; the integrity gate rejected that state and accepted the later reconciled state. This demonstrates a useful workflow on one workload. It does not establish worldwide novelty, graph superiority or general production root-cause accuracy.

## Reproduce the retained investigation

Run `python scripts/replay_banking_investigation.py` from the project directory. It verifies the bundled original recording and the later corrective proof, then writes a readable report without AWS access. Start the dashboard with `START_REDESIGN.ps1 -Port 8012`, then choose **Run banking investigation**. Research results remain under **Research & Validation → Model results**.

Current verification: **195 Python tests**, **19 Java tests**, a frontend production build and **four browser acceptance tests passed**. The final portable-data recomputation also passed.
