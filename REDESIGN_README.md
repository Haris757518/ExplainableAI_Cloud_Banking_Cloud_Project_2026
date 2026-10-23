> **Current validation (23 October):** See [verified results and remaining evaluation](docs/CURRENT_VALIDATION_STATUS.md). The reader correction is implemented and passed repeated AWS tests. Independent repeat-workload localization accuracy remains unreported because its raw export was missed. Earlier milestone statements below are preserved for context.

# Revised project

**Current banking demo:** See [Banking demo guide](docs/BANKING_DEMO_GUIDE.md). The main Banking Investigation screen now replays the executed AWS workload and presents problems, deeper explanations, actions and recovery in plain language. The source evidence and final database backup are retained on D:. Research compute has been terminated. The sections below describe earlier milestones and are superseded by the current guide for banking workload status and test counts.

This is the redesigned application. The sibling V1 checkout and earlier update packages remain unchanged.

## Start

Run `START_REDESIGN.ps1` in this directory. Open http://127.0.0.1:8000 after startup. The launcher prefers a project virtual environment and can reuse the existing V1 Python environment on this computer. To set up independently, create a virtual environment and install the existing requirements files. Rebuild frontend assets with `npm --prefix frontend run build` after changing frontend sources.

The two primary modes are **Banking Cloud** (default) and **Research & Validation**. Banking Cloud shows unavailable monitoring honestly until an executed banking workload is connected. Research & Validation provides guided GNN and PROBE-XAI investigations with readable explanations, recommendations and recovery checks. Published bank history remains under Datasets as an independent reference. Page loads make no cloud writes.

## Evidence

- `docs/DATA_PROVENANCE.md`: official sources, source discrepancies and cloud permissions.
- `docs/FINAL_EXPERIMENT_RESULTS.md`: methods, measured outcomes and limits.
- `results/real_banking`: immutable source snapshots, normalized generations, manifests and banking analyses.
- `results/redesign_20261022/graph`: fresh graph-versus-identity experiment with training and validation histories.
- `submission/Revised_Project_Report.docx`: revised report.
- `submission/Revised_Project_Presentation.pptx`: revised presentation.

Run `python scripts/reproduce_real_banking.py` to reproduce saved banking analysis offline. Existing benchmark results, checkpoints and experimental interfaces are preserved. The RE2 collection now contains 15 recordings with independently prefix-trained identity and graph models. PROBE-XAI results are in results/probe_xai/evaluation_expanded.json. No banking-cloud workload experiment is claimed.

## AWS execution status

The new cloud path is deployed and verified in us-east-1. Both banks have uploaded raw snapshots and normalized CSV files. Downloaded S3 content checksums match, public access is blocked, default AES256 encryption is enabled, and CloudWatch importer-health metrics were read back successfully. Details are in results/real_banking/deployment.json. Configure `BANKING_DATASET_BUCKET`, AWS region and authorized credentials, then use the import controls to execute and inspect the result. This application does not create a bucket or provision Athena. Local imports remain usable without cloud access.

## Verification

The complete final Python suite passed 178 tests. The targeted 21-test investigation and contract suite also passed. Browser acceptance checked both primary modes, Monzo and Starling analysis and research comparisons with no page errors. Frontend production builds passed. Three existing Python dependency deprecation warnings remain. No GNN superiority or confirmed internal banking root-cause accuracy is established.

## Current investigation work

See [PROBE-XAI implementation](docs/PROBE_XAI_IMPLEMENTATION.md), [zero-budget deployment proposal](docs/ZERO_BUDGET_DEPLOYMENT_PLAN.md), and [current measured results](docs/PROBE_XAI_RESULTS.md). The earlier Word report and presentation describe the preceding public-bank integration milestone and remain preserved. The current work does not establish a novelty or accuracy advantage, and new paid AWS compute is not authorized.
