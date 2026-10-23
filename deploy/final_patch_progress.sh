#!/bin/bash
set -eu
python3 - <<'PY'
import json,pathlib
r=pathlib.Path('/opt/banking-research/telemetry');p=r/'final-integrity/patched/trials.json';print('Patched trials:',[x['both_accounts_and_history_correct'] for x in json.loads(p.read_text())] if p.exists() else []);print('Restart check:',(r/'final-integrity/patched/after-restart.json').exists());print('Class hashes:',(r/'correctness-fix/deployed-class-checksums.json').exists())
PY
kubectl -n banking-probe-research get pods --no-headers
