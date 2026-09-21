# Thursday Review Demo

## 1. Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
```

## 2. Train the model

```bash
python scripts/generate_dataset.py --samples 600 --seed 42
python training/train.py --epochs 30 --samples 600 --seed 42
```

A trained checkpoint is already included in the ZIP for the immediate demo.

## 3. Run a deterministic demo

```bash
python scripts/demo.py --scenario DATABASE_LATENCY --seed 42
```

Expected story: RDS-01 is abnormal, downstream payment components are affected, RDS-01 is ranked first by the root-cause layer, and TC-CFAO focuses monitoring on the causal frontier.

## 4. Run the backend

```bash
uvicorn backend.main:app --reload
```

Open `http://127.0.0.1:8000/docs`.

Try `POST /api/simulate?scenario=DATABASE_LATENCY&seed=42`.

## 5. Run the frontend

```bash
cd frontend
npm install
npm run dev
```

## 6. AWS mode

Copy `.env.example` to `.env` and set `AWS_MODE=true`, the AWS region, and the EC2/RDS resource IDs. Configure AWS credentials using an approved AWS SDK credential mechanism. Then call `POST /api/aws/collect` or `POST /api/aws/analyze`.

The local simulator remains available even when AWS credentials are absent.

## Review wording

“This implementation monitors AWS/cloud telemetry, constructs a dependency graph for digital banking services, uses a baseline GNN to detect abnormal graph states, ranks probable root causes, produces feature importance explanations, and applies a causal-frontier adaptive telemetry policy. The current baseline is deliberately upgradeable to temporal GNN and stronger causal methods.”
