#!/bin/bash
set -eu
python3 - <<'PY'
import json,time
from pathlib import Path
runs=sorted(Path('/opt/banking-research/telemetry').glob('final-controlled-*'))
if not runs:
 print('Workload not started')
else:
 root=runs[-1];counts={};last=None
 path=root/'measurements.jsonl'
 if path.exists():
  for line in path.read_text().splitlines():
   try:row=json.loads(line)
   except ValueError:continue
   kind=row.get('instrument','unknown');counts[kind]=counts.get(kind,0)+1
 labels=root/'interventions.jsonl'
 if labels.exists():
  for line in labels.read_text().splitlines():
   try:row=json.loads(line)
   except ValueError:continue
   if row.get('event')=='phase_start':last=row
 print(json.dumps({'execution_id':root.name,'counts':counts,'last_executed_phase':last,'summary_saved':(root/'summary.json').exists(),'checked_at':time.time()}))
PY
