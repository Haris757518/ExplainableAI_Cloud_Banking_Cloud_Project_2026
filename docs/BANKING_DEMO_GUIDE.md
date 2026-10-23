# Banking investigation demo

Run `START_REDESIGN.ps1 -Port 8012` and open http://127.0.0.1:8012/. The launcher uses the project environment, the prepared V1 environment on this computer, or the installed Python. For a new checkout, install `requirements-benchmarks.txt`, then run `npm --prefix frontend ci` and `npm --prefix frontend run build` first.

## Show the problem and its correction

Choose **Run banking investigation**. The application verifies the original recorded evidence and the separate later correction proof. It presents six readable questions: what failed, where it started, why it happened, the deeper cause, the action and whether recovery worked. The default balance finding shows the controlled missed-transfer defect and implemented correction. Choose the other findings for processor restriction, database blocking or increased traffic. Download the readable investigation report from the same screen.

The original workload contains 3,025 submissions and matching ledger records. Its acknowledgement parser was faulty, so those response-success flags are excluded. Later repeat results have their own source label and counts. A ledger record does not establish that its caller received a success response.

## What the explanations establish

Processor allowance fell while payments slowed. Database measurements showed lock waits. Incoming requests rose during the load condition. These observations support the stated contributors but do not identify who changed a configuration, why a transaction was held, or an exclusive internal bottleneck without the missing instruments.

The investigator-assisted commit-order test has stronger mechanism evidence. An earlier-numbered transfer committed after a later-numbered one, and the readers skipped it. The implemented correction reads committed ledger records directly, with deterministic history ordering. Three original-code trials failed; three corrected-code trials passed, including both balances and histories. The checks passed after restarting the readers. The deployed build hashes match the validated Java build. This is verified behavior in these tests, with additional database-read work and no universal production certification.

## Research results

Open **Research & Validation → Model results** for the original banking GNN failure, the development revision, any checksum-verified later repeat results and the retrospective RE2 calibration audit. Original and revised results remain separate. See [current validation](CURRENT_VALIDATION_STATUS.md) and [research contribution](RESEARCH_CONTRIBUTION.md) for scope. No new root-cause accuracy is inferred from a command summary whose raw measurements are unavailable.

## Reproduce locally

- `python scripts/replay_banking_investigation.py` verifies the original banking recording and later correction proof, then writes readable and structured reports without AWS.
- `python scripts/recompute_final_checks.py` recomputes final workload accounting and direct-evidence localization from the portable final inputs after that evaluation is complete. It verifies retained GNN prediction and checkpoint hashes without retraining.
- `python scripts/retrain_banking_models.py --out results/reproduction/banking-fresh` trains new graph and identity models from the bundled final recording. The output directory must be new.
- `python scripts/restore_re2_inputs.py` restores the exact 15 public recordings from the pinned official dataset revision and verifies every checksum. Use `--verify-only` to check existing inputs without downloading.

The normal dashboard starts no cloud resources. The SQL backup remains local on D:. Never upload AWS credentials or private keys. Full cloud reproduction requires separately authorized compute and the bounded export-and-cleanup pipeline; the offline demonstration needs no AWS access.
