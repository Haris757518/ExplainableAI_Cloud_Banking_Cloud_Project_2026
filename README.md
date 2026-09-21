# Explainable AI-Based Cloud Performance Analytics for Digital Banking using Graph Neural Networks

## Team Members
- Haris K
- Keshav Gokaram
- Harish Kumar

## What this project does

This project detects cloud-performance anomalies affecting digital banking workflows and provides a ranked root-cause explanation using graph-based machine learning.

The working pipeline is:

AWS EC2/RDS + CloudWatch (or local simulation)
→ telemetry normalization
→ banking/infrastructure graph
→ Graph Convolutional Network (GCN)
→ anomaly score and affected nodes
→ root-cause ranking
→ feature/node explanation
→ Transaction-Conditioned Causal-Frontier Adaptive Observability (TC-CFAO) policy
→ FastAPI
→ React dashboard

## Important distinction

This is a **cloud performance analytics** project, not a fraud-detection project. Banking transactions are used as context for understanding which services/resources participate in a workflow.

## Modes

### Local/simulation mode
Works without AWS credentials. Synthetic telemetry covers:
- NORMAL
- CPU_SPIKE
- DATABASE_LATENCY
- SERVICE_OVERLOAD
- NETWORK_DEGRADATION
- CASCADING_FAILURE

### AWS mode
Uses boto3/CloudWatch when `AWS_MODE=true` and AWS credentials are available through the normal AWS SDK credential chain. The adapter supports EC2 and RDS resource metrics and normalizes them to the same internal schema used by the simulator.

## Quick start

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows
# .venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env
python scripts/generate_dataset.py --samples 600 --seed 42
python training/train.py --epochs 35 --seed 42
python scripts/demo.py --scenario DATABASE_LATENCY
uvicorn backend.main:app --reload
```

API: http://127.0.0.1:8000/docs
Frontend: see `frontend/README.md`.

## Expected demo

A `DATABASE_LATENCY` event raises RDS database latency, which can propagate to EC2 and the payment service. The model should report an anomaly and rank the RDS node highly as a root-cause candidate. The explanation layer highlights the telemetry dimensions contributing most to the anomaly score. TC-CFAO then proposes a higher-resolution telemetry policy for the causal frontier.

## Architecture

```text
Digital Banking Transaction
        |
        v
AWS / Synthetic Telemetry
        |
        v
Telemetry Normalization
        |
        v
Business + Infrastructure Graph
        |
        v
Baseline GCN
        |
        +--> anomaly score
        +--> affected nodes
        |
        v
Root Cause Ranking
        |
        v
Explainability
        |
        v
TC-CFAO Policy
        |
        v
FastAPI
        |
        v
Dashboard
```

## Research extension path

The baseline is intentionally upgradeable to:
- temporal GNNs
- stronger transaction-conditioned graph propagation
- causal verification/counterfactual testing
- richer XAI
- real adaptive telemetry orchestration
- OpenTelemetry / X-Ray integration

Synthetic results are not presented as real-world banking measurements.

## Quick Start (Windows)

### 1. Backend

```powershell
.\.venv\Scripts\activate
uvicorn backend.main:app --reload
```

Check `http://127.0.0.1:8000/api/health`.

### 2. Frontend

Open a second PowerShell terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open the URL shown by Vite, normally `http://127.0.0.1:5173`.

The frontend uses the Vite `/api` proxy, so browser requests are forwarded to FastAPI without requiring a hard-coded API host. Once the backend is reachable, the dashboard automatically runs the `DATABASE_LATENCY` demo once.

### 3. Manual demo

```powershell
.\.venv\Scripts\activate
python scripts/demo.py --scenario DATABASE_LATENCY --seed 42
```

AWS mode remains disabled by default. Configure real CloudWatch access only after the local end-to-end demo is working.
