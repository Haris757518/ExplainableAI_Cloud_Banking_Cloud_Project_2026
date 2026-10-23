# Optional RCAEval RE2 application-log investigation

## Purpose and boundaries

RCAEval RE2 includes recorded `logs.parquet` files with `timestamp`, `container_name`, and `message`. The project's previously retained 15-case imports contain metrics and traces, not those application logs. This optional extension imports **one** pinned case by default (or an explicitly selected set), then adds **read-only, past-only log excerpts** to the existing guided **Research & Validation → Experiments** investigation.

- The GNN, PROBE-XAI metric rules, fault-label separation, training and final scored experiments are unchanged.
- Log excerpts are **supporting context**, not a newly trained model, verified underlying cause, audit identity, or automatic fix.
- Benchmarks are external microservice recordings, **not** real bank internal logs or the separate AWS Bank of Anthos recording.
- No CloudWatch, S3, EC2, EKS or other cloud requests are made by the reader. The import script makes only an HTTPS request to the pinned public Hugging Face dataset revision.
- Unavailable, incomplete, or checksum-mismatched logs are reported as unavailable instead of being invented.
- The `logs.parquet` filename itself, its enclosing benchmark case name, and injected fault labels are not supplied as diagnostic model inputs.

## Apply to latest banking development branch

From your `codex/banking-investigation-20261023` Git checkout, run the patch tool from this bundle:

```powershell
python path\to\re2_log_extension\apply_re2_log_extension.py --root . --check-only
python path\to\re2_log_extension\apply_re2_log_extension.py --root .
```

The installer verifies existing source anchors and refuses to overwrite pre-existing new files. Review `git diff` before committing.

## Import an optional recorded log file

From the repository root after the original pinned RE2 input restore:

```powershell
python scripts/restore_re2_inputs.py --verify-only
python scripts/restore_re2_logs.py --limit 1
python -m pytest tests/test_re2_log_evidence.py -q
.\START_REDESIGN.ps1 -Port 8012
```

Then open `http://127.0.0.1:8012/` → **Research & Validation** → **Experiments** → **Run guided investigation**. A new **Application log evidence** section shows timestamp-nearby messages from the recorded benchmark and whether the source hash was verified.

`--limit 1` imports at most one of the existing 15 pinned cases. `--case-id <opaque-id>` chooses one matching API case. `--all` processes all 15 (not recommended for a quick review). The initial importer requires the exact pinned manifests to already be present. If the selected official case has no logs, it says so.

## Scientific limits

The underlying supervised RCAEval task has labelled injected faults, but the diagnostic reader deliberately sees only recorded metrics, traces and log text available by the investigation time. Fault labels are used separately for evaluation. The log additions **do not** improve the existing measured 3/6 or 6/6 results until a new independent evaluation is executed, and they **cannot** answer who changed a CPU allowance. That requires operational audit/change records not present in these application logs.

## Validation status

Integrated and validated on 23 October 2026:

- 201 Python tests passed, including six log-reader tests for time boundaries, service prioritization, checksum failures, missing files, bounded scans and corrupt Parquet.
- Frontend build passed; all four browser acceptance checks passed, including the application-log evidence display and its limits.
- Downloaded one official pinned recording (opaque ID `364d289fa7b7106f7a71`). SHA256: `e1a25e50c8b0beae4b2886df54d86d2f28877d0b611fed98411e9c0b0c77dad3`.
- The real reader scanned 171,322 rows completely. At the recording end, 21,112 messages were within its 180-second past-only window; the reader returns at most eight excerpts. The integrated investigation returned available, checksum-verified log evidence.
- Fixed a Windows installer file-handle issue by closing the Parquet reader before renaming the download. Partial scans are disclosed in the interface; unavailable Parquet support and corrupt files abstain.
- Downloaded logs stay in the ignored local raw-data directory and are reproducible with the pinned importer. No model retraining, fault-score changes, AWS use or demonstrated accuracy improvement accompanies this extension.

The local checksum detects later file changes; it is not an independently published upstream checksum or proof of causality.

Source schema: https://huggingface.co/datasets/phamquiluan/RCAEval
