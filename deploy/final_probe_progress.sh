#!/bin/bash
set -e
python3 - <<'PY'
import json,pathlib
p=pathlib.Path('/opt/banking-research/telemetry/final-integrity/baseline/trials.json')
print(json.dumps([{'trial':r['trial'],'correct':r['both_accounts_and_history_correct'],'gaps':[a['gap_cents'] for a in r['after']['accounts']]} for r in json.loads(p.read_text())]) if p.exists() else 'No completed trial yet')
PY
