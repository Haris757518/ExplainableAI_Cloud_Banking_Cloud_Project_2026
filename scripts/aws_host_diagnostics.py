"""Bounded read-only host audit through SSM. No environment or process arguments."""
from pathlib import Path
import argparse
import json
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import boto3
from botocore.config import Config
from common.config import Settings

COMMANDS = [
    "printf '=== RESOURCE PRESSURE ===\\n'; uptime; free -m; df -h /; for p in cpu memory io; do printf '%s\\n' \"$p\"; cat /proc/pressure/$p 2>/dev/null || true; done",
    "printf '=== PROCESS NAMES ONLY ===\\n'; ps -eo comm,pcpu,pmem --sort=-pcpu | head -15",
    "printf '=== SERVICE STATUS ===\\n'; for s in nginx httpd postgresql mariadb mysql docker; do printf '%s: ' \"$s\"; systemctl is-active \"$s\" 2>/dev/null || true; done",
    "printf '=== LISTENING TCP PORTS ===\\n'; ss -ltn",
]


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--instance-id',required=True)
    p.add_argument('--env-file',default='.env')
    p.add_argument('--out',default='results/observed/aws_host_diagnostics.json')
    args=p.parse_args()
    s=Settings(_env_file=args.env_file)
    client=boto3.Session(region_name=s.aws_region,profile_name=s.profile).client('ssm',config=Config(connect_timeout=4,read_timeout=10,retries={'max_attempts':1}))
    response=client.send_command(InstanceIds=[args.instance_id],DocumentName='AWS-RunShellScript',TimeoutSeconds=30,
        Parameters={'commands':COMMANDS,'executionTimeout':['20']},Comment='Read-only cloud performance diagnosis; no secrets or process arguments')
    command=response['Command']['CommandId']
    result=None
    for _ in range(20):
        try:
            result=client.get_command_invocation(CommandId=command,InstanceId=args.instance_id)
        except client.exceptions.InvocationDoesNotExist:
            time.sleep(1)
            continue
        if result['Status'] in ('Success','Failed','Cancelled','TimedOut'):
            break
        time.sleep(1)
    if not result:
        raise RuntimeError('SSM audit did not return an observation.')
    report={k:result.get(k) for k in ('InstanceId','Status','ExecutionStartDateTime','ExecutionEndDateTime','StandardOutputContent','StandardErrorContent')}
    report['source']='aws_ssm_read_only_host_observation'
    out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2))


if __name__=='__main__':
    main()
