"""One bounded run: execute, export automatically, verify, and clean up.

Run only with explicit AWS compute authorization. No credentials are logged.
The guest deadline is independent of this process. Failure also attempts an
immediate evidence export before terminating the exact tagged instance.
"""
import base64
import hashlib
import json
import subprocess
import sys
import time
import zlib
from datetime import datetime, timezone
from pathlib import Path

import boto3

from final_aws_session import RECORD, command, ec2, guard, launch, load

ROOT = Path(__file__).resolve().parents[1]
OLD = 'i-05d147001c0289108'


def child(name, *args):
    subprocess.run([sys.executable, str(ROOT / 'scripts' / name), *map(str, args)],
                   cwd=ROOT, check=True)


def main():
    previous = load()
    assert previous['instance_id'] == OLD
    assert boto3.client('sts').get_caller_identity()['Account'] == previous['account']
    remaining = ec2().describe_instances(InstanceIds=[OLD])['Reservations']
    assert not any(i['State']['Name'] not in ('terminated', 'shutting-down')
                   for r in remaining for i in r['Instances'])
    assert not ec2().describe_volumes(Filters=[{'Name': 'tag:ResearchRun', 'Values': [previous['run']]}])['Volumes']
    archived = RECORD.with_name('aws-final-validation-prior-20261022.json')
    assert not archived.exists(), 'Do not overwrite a prior manifest'
    RECORD.rename(archived)
    launch()
    record = load()
    instance = record['instance_id']
    print('Bounded repeat launched:', instance, flush=True)
    # Independent guest deadline remains active even if this process exits.
    failure = None
    exported = None
    try:
        ssm = boto3.client('ssm', region_name='us-east-1')
        for _ in range(90):
            info = ssm.describe_instance_information(Filters=[{'Key': 'InstanceIds', 'Values': [instance]}])['InstanceInformationList']
            if info and info[0]['PingStatus'] == 'Online':
                break
            time.sleep(5)
        else:
            raise RuntimeError('SSM did not become available')
        for file, name, timeout in [
            ('bootstrap_final_aws.sh', 'bootstrap', 900),
            ('apply_anthos_aws.sh', 'deploy', 900),
            ('check_final_stack.sh', 'check-stack', 600),
            ('run_final_baseline_probe.sh', 'baseline-probe', 600),
            ('deploy_and_verify_correctness.sh', 'patched-probe', 900),
        ]:
            text = (ROOT / 'deploy' / file).read_text().replace(OLD, instance)
            command(text, name, timeout)
        # Identity-only collector substitution: no model, localizer, timing,
        # traffic, fault, or scoring rule is changed after the original freeze.
        collector = (ROOT / 'deploy/collect_final_validation.py').read_text().replace(OLD, instance).encode()
        amendment = {
            'created_at': datetime.now(timezone.utc).isoformat(),
            'before_new_workload_execution': True,
            'reason': 'Repeat the unevaluated run after loss of its raw export. Only the source-instance identity changes; rules and workload stay frozen.',
            'source_instance': instance,
            'executed_collector_lf_sha256': hashlib.sha256(collector).hexdigest(),
            'original_collector_lf_sha256': hashlib.sha256((ROOT / 'deploy/collect_final_validation.py').read_text().encode()).hexdigest(),
        }
        path = ROOT / 'results/final_validation/protocol-amendment-004.json'
        assert not path.exists(), 'Never overwrite a prospective amendment'
        path.write_text(json.dumps(amendment, indent=2))
        payload = base64.b64encode(zlib.compress(collector)).decode()
        script = "set -eu\npython3 - <<'PY'\nimport pathlib,zlib,base64\npathlib.Path('/opt/banking-research/collect_final_validation.py').write_bytes(zlib.decompress(base64.b64decode(" + repr(payload) + ")))\nPY\npython3 /opt/banking-research/collect_final_validation.py\n"
        command(script, 'repeated-workload', 2100)
        command((ROOT / 'deploy/verify_final_recovery.sh').read_text().replace(OLD, instance), 'final-recovery', 600)
        child('export_final_aws.py', '--stage', 'final')
        exported = Path(load()['exports'][-1]['folder'])
        # This checks raw hashes, later transfer receipts and SQL backup before
        # termination. Analysis runs only against the verified local archive.
        child('finish_final_aws_session.py', '--export', exported)
    except Exception as error:
        failure = error
        print('Pipeline failed:', type(error).__name__, str(error), flush=True)
        try:
            child('export_final_aws.py', '--stage', 'final')
        except Exception as export_error:
            print('Emergency export failed:', type(export_error).__name__, flush=True)
    finally:
        # Exact tagged instance only; never act on the pre-existing server.
        vm = guard(load())
        if vm['State']['Name'] not in ('terminated', 'shutting-down'):
            ec2().terminate_instances(InstanceIds=[instance])
            print('Exact research instance cleanup requested.', flush=True)
    if failure:
        raise failure
    child('evaluate_final_banking_validation.py', '--export', exported)
    print('EXECUTION, VERIFIED EXPORT, CLEANUP AND LOCAL EVALUATION COMPLETE', flush=True)


if __name__ == '__main__':
    main()
