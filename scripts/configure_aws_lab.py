"""Install the isolated measured probe service on an explicitly selected EC2 host."""
from pathlib import Path
import argparse
import base64
import json
import sys
import time
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import boto3
from botocore.config import Config
from common.config import Settings


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--instance-id',required=True)
    p.add_argument('--env-file',default='.env')
    p.add_argument('--out',default='results/observed/aws_lab_setup.json')
    args=p.parse_args();s=Settings(_env_file=args.env_file)
    session=boto3.Session(region_name=s.aws_region,profile_name=s.profile)
    ec2=session.client('ec2',config=Config(connect_timeout=4,read_timeout=10,retries={'max_attempts':1}))
    instances=ec2.describe_instances(InstanceIds=[args.instance_id])['Reservations']
    instance=instances[0]['Instances'][0]
    if instance['State']['Name']!='running' or not instance.get('IamInstanceProfile'):
        raise RuntimeError('Selected instance must be running and have an instance profile for CloudWatch publishing.')
    source=base64.b64encode((Path(__file__).resolve().parents[1]/'aws/lab_probe_service.py').read_bytes()).decode()
    # Dedicated directories, OS account, and database. No application data, firewall
    # rules, existing DB authentication, or IAM policies are replaced.
    shell=f'''set -eu
if [ -d /opt/explainableai-observer ] && [ ! -f /opt/explainableai-observer/.managed-by-explainableai ]; then echo 'Unowned installation path; stopping'; exit 1; fi
if ss -ltn | grep -q ':8080 ' && ! systemctl is-active --quiet explainableai-observer; then echo 'Port 8080 is already in use'; exit 1; fi
systemctl is-active --quiet postgresql || {{ echo 'Existing PostgreSQL service must be active'; exit 1; }}
id xaiobserver >/dev/null 2>&1 || useradd --system --home-dir /var/lib/explainableai-observer --shell /sbin/nologin xaiobserver
install -d -m 755 /opt/explainableai-observer
touch /opt/explainableai-observer/.managed-by-explainableai
install -d -m 750 -o xaiobserver -g xaiobserver /var/lib/explainableai-observer
dnf install -y python3-pip >/dev/null
python3 -m venv /opt/explainableai-observer/venv
/opt/explainableai-observer/venv/bin/pip install --disable-pip-version-check 'boto3>=1.34,<2' 'psycopg[binary]>=3.2,<4' >/dev/null
sudo -u postgres psql -X -At -v ON_ERROR_STOP=1 -c "SELECT 'CREATE ROLE xaiobserver LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION' WHERE NOT EXISTS (SELECT FROM pg_roles WHERE rolname='xaiobserver')" | sudo -u postgres psql -X -v ON_ERROR_STOP=1
sudo -u postgres psql -X -At -v ON_ERROR_STOP=1 -c "SELECT 'CREATE DATABASE xai_observability OWNER xaiobserver' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname='xai_observability')" | sudo -u postgres psql -X -v ON_ERROR_STOP=1
printf '%s' '{source}' | base64 -d > /opt/explainableai-observer/service.py
chmod 644 /opt/explainableai-observer/service.py
cat > /etc/systemd/system/explainableai-observer.service <<'SERVICE'
[Unit]
Description=ExplainableAI measured AWS lab probes
After=network-online.target postgresql.service
Wants=network-online.target
[Service]
Type=simple
User=xaiobserver
Group=xaiobserver
Environment=AWS_REGION={s.aws_region}
Environment=OBSERVER_INSTANCE_ID={args.instance_id}
ExecStart=/opt/explainableai-observer/venv/bin/python /opt/explainableai-observer/service.py
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/var/lib/explainableai-observer
[Install]
WantedBy=multi-user.target
SERVICE
systemctl daemon-reload
systemctl enable explainableai-observer
systemctl restart explainableai-observer
sleep 3
systemctl is-active explainableai-observer
curl --fail --silent --max-time 20 http://127.0.0.1:8080/health
'''
    client=session.client('ssm',config=Config(connect_timeout=4,read_timeout=10,retries={'max_attempts':1}))
    response=client.send_command(InstanceIds=[args.instance_id],DocumentName='AWS-RunShellScript',TimeoutSeconds=300,
        Parameters={'commands':[shell],'executionTimeout':['240']},Comment='Configure isolated measured lab probe service and database; no synthetic telemetry')
    command=response['Command']['CommandId']
    print(json.dumps({'command_id':command,'instance_id':args.instance_id,'status':'dispatched'}),flush=True)
    for _ in range(120):
        try:
            result=client.get_command_invocation(CommandId=command,InstanceId=args.instance_id)
        except client.exceptions.InvocationDoesNotExist:
            time.sleep(2);continue
        if result['Status'] in ('Success','Failed','Cancelled','TimedOut'):
            report={k:result.get(k) for k in ('InstanceId','Status','ExecutionStartDateTime','ExecutionEndDateTime','StandardOutputContent','StandardErrorContent')}
            report['source']='aws_lab_configuration'
            out=Path(args.out);out.parent.mkdir(parents=True,exist_ok=True);out.write_text(json.dumps(report,indent=2),encoding='utf-8')
            print(json.dumps(report,indent=2));return 0 if result['Status']=='Success' else 1
        time.sleep(2)
    print('Setup still running; inspect the dispatched SSM command ID.');return 2


if __name__=='__main__':
    raise SystemExit(main())
