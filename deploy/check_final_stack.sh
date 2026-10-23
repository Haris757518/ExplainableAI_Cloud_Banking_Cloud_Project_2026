#!/bin/bash
set -euo pipefail
for service in accounts-db ledger-db; do kubectl -n banking-probe-research rollout status statefulset/$service --timeout=240s; done
for service in userservice contacts frontend ledgerwriter balancereader transactionhistory; do kubectl -n banking-probe-research rollout status deployment/$service --timeout=240s; done
#!/bin/bash
set -euo pipefail
kubectl -n banking-probe-research set env deployment/ledgerwriter deployment/balancereader deployment/transactionhistory MANAGEMENT_ENDPOINTS_WEB_EXPOSURE_INCLUDE=health,metrics
for service in ledgerwriter balancereader transactionhistory; do
 kubectl -n banking-probe-research rollout status deployment/$service --timeout=180s
done
python3 - <<'PY'
import subprocess,json,urllib.request
services=json.loads(subprocess.check_output(['kubectl','-n','banking-probe-research','get','services','-o','json']))['items']
for service in services:
 if service['metadata']['name'] not in ('ledgerwriter','balancereader','transactionhistory'):continue
 ip=service['spec']['clusterIP'];url='http://'+ip+':8080/actuator/metrics'
 try:
  with urllib.request.urlopen(url,timeout=10) as response:print(service['metadata']['name'],response.read().decode())
 except Exception as e:print(service['metadata']['name'],type(e).__name__,str(e))
PY

kubectl -n banking-probe-research exec deployment/balancereader -- ls /app/classes/anthos/samples/bankofanthos/balancereader
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
python3 /opt/banking-research/anthos/verify_anthos_transfer.py --environment aws --source-instance i-05d147001c0289108 --out /opt/banking-research/telemetry/normal
find /opt/banking-research/telemetry/normal -name verification.json -exec cat '{}' ';'
