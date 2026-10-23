# Explainable cloud banking investigation

This research prototype explains an executed banking incident from the visible problem through the deepest supported mechanism, a corrective action and checked recovery. It combines GNN symptom ranking, progressive direct-evidence investigation and a transaction-integrity recovery gate. The default dashboard uses readable explanations and keeps detailed measurements optional.

Start with the [banking demo guide](docs/BANKING_DEMO_GUIDE.md), [current validation](docs/CURRENT_VALIDATION_STATUS.md), and [research contribution and related work](docs/RESEARCH_CONTRIBUTION.md). Earlier milestone reports remain preserved; these current documents supersede their statements about pending banking execution or reader implementation.

## Run the local demonstration

From this directory, using Python 3.12 and Node.js:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-benchmarks.txt
npm --prefix frontend ci
npm --prefix frontend run build
.\START_REDESIGN.ps1 -Port 8012
```

Open http://127.0.0.1:8012/ and choose **Run banking investigation**. The prepared checkout can reuse the existing V1 Python environment through the launcher. The dashboard reads retained measurements and starts no AWS resources. **Research & Validation → Model results** contains the separate model studies and limitations.

## Implemented components

- `analysis/banking_replay.py`: checksum-verified replay of the original 3,025-request AWS recording, with explicit missing-evidence and recovery checks.
- `ai_models/banking_study.py`: chronological banking next-step graph and identity models, masked missing data, normal-prefix calibration and three random seeds.
- `analysis/banking_localization.py`: measured processor, demand and PostgreSQL blocking evidence to refine symptom rankings, with abstention when evidence is insufficient.
- `analysis/probe_xai.py`: progressive inspection of recorded benchmark columns within an explicit effort budget.
- `analysis/banking_followup.py`: verifies the corrective-code proof and final result manifests before making dashboard claims.
- `deploy/correctness-fix/`: authoritative committed-ledger reader correction and regression-test patch for the pinned Bank of Anthos source.
- `scripts/run_final_validation_pipeline.py`: authorized, bounded cloud execution with automatic export, verified backup and exact-instance cleanup. It is an operational tool, not run by the dashboard.

## Reader correction

The original transaction-number cursor could skip a lower-numbered transfer that committed later. Corrected balance and history endpoints read committed ledger records directly, with deterministic history ordering and explicit database errors. The retained AWS before-and-after tests show three original-code failures, three corrected-code passes and successful restart checks. Deployed class hashes match the validated build; 19 Java tests passed. These tests address the reproduced defect. Authoritative reads increase database work and do not certify production capacity.

## Evidence and reproduction

```powershell
python scripts/replay_banking_investigation.py
python scripts/recompute_final_checks.py
python scripts/retrain_banking_models.py --out results/reproduction/banking-fresh
python scripts/restore_re2_inputs.py --verify-only
```

The first command needs no AWS and writes the readable banking report. The second recomputes final accounting and direct-evidence localization after the final portable inputs are present. The third trains fresh graph and identity models in a new directory. The last verifies the exact 15 public RE2 recordings; omit `--verify-only` to restore missing public files from their pinned revision.

Banking evidence, RE2 controlled experiments, and published Monzo/Starling aggregates retain separate provenance. No public-bank statistic is used as an internal fault label. The original request-acknowledgement parser defect is documented and excluded from success claims. A matching ledger record is distinct from a caller receiving success. The prior repeat whose raw export was missed remains documented and excluded from localization scoring.

The final SQL backup stays on D:. Portable research inputs are allowlisted. AWS credentials, private keys, local environments and generated deployment bundles remain excluded from Git.

## Results and claim boundaries

The initial banking GNN ranked both evaluated fault services incorrectly. Direct evidence corrected those two development cases. In the later frozen-rule workload, direct-evidence localization identified all six fault services; graph GNN ranking identified three. All three seeds had those counts. The graph detector detected all six checkpoints and raised zero alerts in 36 normal holdout bins per seed. These are controlled within-workload results, not production accuracy. The RE2 calibration audit found 13 of 15 fault checkpoints, missed two and produced zero alerts at the 15 normal checkpoints. This is a retrospective audit, not a production false-alarm guarantee.

The proposed contribution is the integrated investigation and integrity-checking workflow. In the original workload, fast balance reads passed a speed-only recovery policy while the balance remained wrong; the integrity gate rejected that state. This demonstrates value on one workload. Worldwide novelty, GNN superiority and broad production root-cause accuracy are not established.

## Verification and submission

Current software checks: **195 Python tests**, **19 Java tests**, frontend production build and four browser acceptance checks. Generated final submission files are placed under `submission/`. The current evidence status and any remaining evaluation boundary are explicit in `docs/CURRENT_VALIDATION_STATUS.md`.
