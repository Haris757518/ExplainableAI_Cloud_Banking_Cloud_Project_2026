# Explainable cloud performance investigation

Main version: Research V1 with observed-data implementation, 16 October 2026.

Analyze measured Alibaba microservice call durations or live AWS EC2/RDS CloudWatch series. Missing values remain unknown. The dashboard explains temporal deviations, ranks suspected causes, and requests the evidence needed to distinguish database, compute, and application issues. Synthetic simulation endpoints are disabled by default. Historical checkpoints and results remain available for reproducibility and are excluded from current observed-data conclusions.

## Start on Windows

From this directory:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open http://127.0.0.1:8000 . The local dashboard has been built. After cloning from GitHub, build the frontend using the setup commands below.

## Reproduce the measured-data study

```powershell
.\.venv\Scripts\python.exe scripts/run_observed_research.py
.\.venv\Scripts\python.exe -m pytest -q
```

The real-trace GNN uses chronological partitions and reports measured-target reconstruction error against a training-mean baseline. No accuracy or root-cause success rate is claimed without incident labels. Dashboard diagnosis combines temporal median/MAD evidence with the measured-data GNN reconstruction explanation when the trace slice matches its documented held-out study. It abstains from transferring these weights to AWS.

## AWS access

The existing local configuration uses the default credential profile. Refresh AWS Academy temporary credentials locally. No keys belong in this repository. `AWS_MODE=true` enables read-only collection; it does not create resources. The application database needs a separate read-only monitoring connection in `MONITORED_DATABASE_URL` for wait and lock evidence.

See [the implementation, data decision, limitations, and evaluation plan](docs/REAL_DATA_IMPLEMENTATION.md). Current measured outputs are in `results/observed/`. Legacy synthetic outputs in `results/runtime/` are historical experiments.


## Fresh clone setup

Python 3.12 and Node.js are required. From the project directory:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
npm --prefix frontend ci
npm --prefix frontend run build
.\.venv\Scripts\python.exe scripts/fetch_alibaba_subset.py --out dataset/raw/alibaba
.\.venv\Scripts\python.exe scripts/run_observed_research.py
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Raw traces, credentials, local databases, installers, and raw AWS operational snapshots are kept out of Git. The measured-trace report/checkpoint are included; live verification records are generated locally by `scripts/verify_live.py` after AWS is configured. See `.env.example` and `docs/REAL_DATA_IMPLEMENTATION.md` for configuration.
