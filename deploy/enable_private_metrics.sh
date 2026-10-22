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
