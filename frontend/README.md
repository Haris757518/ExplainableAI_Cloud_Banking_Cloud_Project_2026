# Frontend

React/Vite dashboard for the Digital Banking Cloud Performance Analytics system.

From `frontend/`:

```powershell
npm install
npm run dev
```

The Vite development proxy sends `/api/*` requests to FastAPI at `http://127.0.0.1:8000`.

The dashboard is wired to the real backend analysis results and shows the graph, anomaly scores, RCA, explanation, counterfactual evidence, temporal window, and TC-CFAO adaptive policy.
