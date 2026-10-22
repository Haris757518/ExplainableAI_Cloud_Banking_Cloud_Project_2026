#!/bin/bash
set -euo pipefail
python3 - <<'PY'
import json,shutil,hashlib
from pathlib import Path
for folder in Path('/opt/banking-research/telemetry').glob('controlled-*'):
 source=Path('/opt/banking-research/collect_experiments.py');shutil.copyfile(source,folder/'executed-collector-source.py')
 audit={'collector_issue':'Payment acknowledgement classifier used unquote instead of form-query parsing; plus-encoded Payment+successful was not recognized.','affected_fields':['payment_request.outcome','summary.acknowledged_success','summary.acknowledged_but_missing_ledger'],'treatment':'Do not use those fields as payment acknowledgement or failure truth. Preserve originals. Ledger counts, unique amounts, timings, HTTP status, traces and instrumentation snapshots are retained independently.','request_to_ledger_link':'Each request uses a unique transfer amount and UUID in this isolated run. Ledger matching uses exact sender, receiver and amount.','executed_collector_sha256':hashlib.sha256(source.read_bytes()).hexdigest(),'future_correction':'Parse query parameters with urllib.parse.parse_qs and retain the decoded result_message; no retrospective invention of missing query strings.','trace_coverage':'Frontend server/client only. Backend and SQL spans not claimed.','missing_instruments':['Direct per-request backend CPU attribution','HTTP admission queue depth']}
 (folder/'collector-audit.json').write_text(json.dumps(audit,indent=2))
root=Path('/opt/banking-research/telemetry/runtime-provenance');root.mkdir(exist_ok=True)
shutil.copyfile('/opt/banking-research/anthos/preparation.json',root/'anthos-source-preparation.json')
PY
