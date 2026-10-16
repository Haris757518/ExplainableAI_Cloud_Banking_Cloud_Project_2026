# Thursday / Review Demo

## Demo story

Use the `DATABASE_LATENCY` scenario with a `UPI_PAYMENT` transaction.

```text
UPI_PAYMENT
    ↓
API Gateway
    ↓
Payment Service
    ↓
EC2-01
    ↓
RDS-01
```

The system then shows:

1. anomaly detection by the GCN
2. affected-node scores
3. transaction-conditioned root-cause ranking
4. feature-perturbation explanation
5. simulated counterfactual evidence
6. causal frontier
7. adaptive telemetry policy
8. temporal window with onset/peak/recovery
9. before/after adaptive re-analysis

## Commands

```powershell
.\.venv\Scripts\python.exe scripts/run_smoke.py
.\.venv\Scripts\python.exe scripts/research_demo.py --scenario DATABASE_LATENCY --seed 42
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

## What to say

“This system treats a digital-banking transaction as a path through a business-to-infrastructure dependency graph. The GNN uses telemetry and graph relationships to detect abnormal graph states. A transaction-conditioned RCA layer ranks root-cause candidates, XAI provides supporting feature evidence, and the proposed TC-CFAO loop focuses higher-resolution telemetry on the suspected causal frontier before re-analysis.”

Synthetic experiments must be described as synthetic. AWS results should only be presented after real CloudWatch collection has been configured and tested.
