#!/bin/bash
set -euo pipefail
kubectl -n banking-probe-research exec statefulset/ledger-db -- psql -U admin -d postgresdb -v ON_ERROR_STOP=1 -c "SET application_name='faculty-bounded-lock'; SET statement_timeout='40s'; BEGIN; LOCK TABLE transactions IN ACCESS EXCLUSIVE MODE; SELECT pg_sleep(30); COMMIT;"
