"""Freeze a prospective repeat protocol before any new workload outcomes."""
import base64,hashlib,json,zlib
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
source=(ROOT/'scripts/collect_aws_banking_experiments.py').read_text()
source=source.replace("RUN='controlled-'","RUN='final-controlled-'")
source=source.replace("'1000000.00'","'10000000.00'")
source=source.replace("'i-0aefecc39f02f2727'","'i-05d147001c0289108'")
source=source.replace("--since=20m","--since=40m")
left=source.index("        for service in ('ledgerwriter','balancereader'):")
right=source.index('        try:\n            query=',left)
source=source[:left]+source[right:]
left=source.index("try:\n    phase('normal',75,5)")
right=source.index('finally:\n    if resized:resize(original)',left)
source=source[:left]+'''try:
    phase('normal',360,5)
    reduced=json.loads(json.dumps(original));reduced['limits']['cpu']='20m';reduced['requests']['cpu']='20m'
    for trial in range(1,4):
        try:
            resize(reduced);resized=True;phase('reduced_cpu_'+str(trial),75,5)
        finally:
            if resized:resize(original);resized=False
        phase('cpu_recovery_'+str(trial),90,5)
        lock_command=['kubectl','-n',NS,'exec','statefulset/ledger-db','--','psql','-U','admin','-d','postgresdb','-v','ON_ERROR_STOP=1','-c',"SET application_name='research-bounded-lock'; BEGIN; LOCK TABLE transactions IN ACCESS EXCLUSIVE MODE; SELECT pg_sleep(30); COMMIT;"]
        lock_log=(OUT/('bounded-lock-'+str(trial)+'.stdout')).open('w')
        blocker=subprocess.Popen(lock_command,stdout=lock_log,stderr=subprocess.STDOUT)
        write(LABELS,{'timestamp':time.time(),'event':'bounded_database_lock_started','duration_seconds':30,'trial':trial})
        phase('db_contention_'+str(trial),60,5);blocker.wait(timeout=10);lock_log.close()
        assert blocker.returncode==0
        write(LABELS,{'timestamp':time.time(),'event':'bounded_database_lock_process_exit','return_code':blocker.returncode,'trial':trial})
        phase('db_recovery_'+str(trial),60,5)
        if trial<=2:
            phase('heavy_transactions_'+str(trial),60,15)
            phase('traffic_recovery_'+str(trial),60,5)
'''+source[right:]
source=source.replace("(OUT/'deployment-before.json').write_text(json.dumps(pods))","(OUT/'deployment-before.json').write_text(json.dumps(pods))\n(OUT/'executed-collector.py').write_bytes(Path(__file__).read_bytes())")
target=ROOT/'deploy/collect_final_validation.py';target.write_text(source)
compile(source,str(target),'exec')
payload=base64.b64encode(zlib.compress(source.encode())).decode()
script="#!/bin/bash\nset -euo pipefail\npython3 - <<'PY'\nimport pathlib,zlib,base64\npathlib.Path('/opt/banking-research/collect_final_validation.py').write_bytes(zlib.decompress(base64.b64decode("+repr(payload)+")))\nPY\npython3 /opt/banking-research/collect_final_validation.py\n"
(ROOT/'deploy/run_final_validation.sh').write_text(script)
protocol={'frozen_at':datetime.now(timezone.utc).isoformat(),'development_recording':'controlled-20261022T174849Z',
    'normal_reference_seconds':360,'model_train_seconds':216,'model_validation_end_seconds':288,'normal_holdout_end_seconds':360,
    'test_repetitions':{'reduced_cpu':3,'db_contention':3,'heavy_transactions':2},'fixed_checkpoint_seconds_after_phase_start':30,
    'localization_budget':8,'source':'Prospective new AWS execution; same demo application and host class. Not cross-application generalization.',
    'labels_policy':'Intervention log separate. All window predictions are written before evaluation-only labels are read.',
    'measurement_policy':'Cgroup and PostgreSQL snapshots every 2 seconds; expensive serial Java probes omitted. Missing queue and backend spans remain missing.',
    'source_sha256':{name:hashlib.sha256((ROOT/name).read_bytes()).hexdigest() for name in ['deploy/collect_final_validation.py','analysis/banking_localization.py','ai_models/banking_study.py']}}
output=ROOT/'results/final_validation';output.mkdir(exist_ok=True)
frozen=output/'prospective-protocol.json'
if frozen.exists():raise SystemExit('Protocol already frozen; preserve it rather than changing the test.')
frozen.write_text(json.dumps(protocol,indent=2))
print('Frozen final protocol:',protocol['test_repetitions'])
