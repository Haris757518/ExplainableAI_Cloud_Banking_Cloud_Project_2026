#!/bin/bash
set -euo pipefail
kubectl -n banking-probe-research get pods
if ! systemctl is-active --quiet bank-research-frontend.service; then
  systemd-run --unit=bank-research-frontend --property=Restart=on-failure /usr/local/bin/kubectl -n banking-probe-research port-forward --address 127.0.0.1 service/frontend 8080:80
fi
for attempt in $(seq 1 30); do
  if curl -fsS http://127.0.0.1:8080/login -o /dev/null; then break; fi
  sleep 2
done
python3 /opt/banking-research/anthos/verify_anthos_transfer.py --environment aws --source-instance i-0aefecc39f02f2727 --out /opt/banking-research/telemetry/normal
find /opt/banking-research/telemetry/normal -name verification.json -exec cat '{}' ';'
