# Demo

## Complete local demo

From the project root:

```powershell
python scripts/generate_dataset.py --samples 600 --seed 42
python scripts/run_smoke.py
python scripts/research_demo.py --scenario DATABASE_LATENCY --seed 42
```

Start backend:

```powershell
uvicorn backend.main:app --reload
```

Start frontend in a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Review scenario

Use `DATABASE_LATENCY` with `UPI_PAYMENT`.

Demonstration story:

1. UPI transaction enters the graph.
2. Database latency becomes abnormal.
3. GNN detects a graph anomaly.
4. Affected nodes are ranked.
5. RCA combines telemetry, graph propagation, and transaction relevance.
6. XAI identifies important telemetry features.
7. A causal frontier is created.
8. Frontier nodes receive a 5-second adaptive policy; unrelated nodes remain at 60 seconds.
9. A focused second observation window is analyzed.
10. A simulated counterfactual intervention provides additional RCA evidence.
