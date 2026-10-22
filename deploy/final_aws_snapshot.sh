#!/bin/bash
set -euo pipefail
mkdir -p /opt/banking-research/telemetry/database-backup
kubectl -n banking-probe-research exec statefulset/ledger-db -- pg_dump -U admin -d postgresdb --no-owner --no-acl | gzip > /opt/banking-research/telemetry/database-backup/ledger-final.sql.gz
gzip -t /opt/banking-research/telemetry/database-backup/ledger-final.sql.gz
kubectl -n banking-probe-research get pods -o json > /opt/banking-research/telemetry/database-backup/final-pods.json
kubectl -n banking-probe-research get pod -l app=ledgerwriter -o json > /opt/banking-research/telemetry/database-backup/restored-ledgerwriter-pod.json
sha256sum /opt/banking-research/telemetry/database-backup/ledger-final.sql.gz
