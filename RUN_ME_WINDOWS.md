# Run the project on Windows

## Recommended folder

Use a short path such as:

```text
D:\EAIBank
```

This avoids Windows long-path issues during PyTorch installation.

## Terminal 1 — backend

```powershell
cd D:\EAIBank
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload
```

Check:

- http://127.0.0.1:8000/api/health
- http://127.0.0.1:8000/docs

## Terminal 2 — frontend

```powershell
cd D:\EAIBank\frontend
npm install
npm run dev
```

Open the Vite URL, normally `http://localhost:5173`. The frontend uses the Vite `/api` proxy to reach FastAPI.

## First-time Python setup

If `.venv` does not exist:

```powershell
cd D:\EAIBank
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install torch --index-url https://download.pytorch.org/whl/cpu
.\.venv\Scripts\python.exe -m pip install -r requirements.txt --no-deps
```

If you already have a working project `.venv`, reuse it rather than downloading PyTorch again.

## Demo

```powershell
.\.venv\Scripts\python.exe scripts/generate_dataset.py --samples 600 --seed 42
.\.venv\Scripts\python.exe scripts/run_smoke.py
.\.venv\Scripts\python.exe scripts/research_demo.py --scenario DATABASE_LATENCY --seed 42
```

## AWS

Keep `AWS_MODE=false` until AWS credentials and actual EC2/RDS resource IDs are configured. Never commit credentials.

## AWS live mode (read-only)

1. Start the AWS Academy Learner Lab and open the temporary AWS console.
2. Make the lab's temporary AWS credentials available to your local shell using the method provided by your lab (or configure an AWS CLI profile).
3. Copy `.env.example` to `.env` and set `AWS_MODE=true` plus the correct `AWS_REGION`.
4. Start FastAPI.
5. Open the dashboard and choose `AWS LIVE` → `Connect / Discover AWS`.
6. Confirm EC2/RDS counts and then choose `Analyze AWS`.

The application performs read-only discovery/metric queries. It does not create or delete AWS resources.
