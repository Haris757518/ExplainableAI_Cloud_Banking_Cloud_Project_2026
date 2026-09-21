# Run the project on Windows

Open two PowerShell terminals in the project root.

## Terminal 1 — backend

```powershell
.\.venv\Scripts\activate
uvicorn backend.main:app --reload
```

Check:

- http://127.0.0.1:8000/api/health
- http://127.0.0.1:8000/docs

## Terminal 2 — frontend

```powershell
cd frontend
npm run dev
```

Open the URL printed by Vite (normally `http://127.0.0.1:5173`).

The frontend now uses Vite's `/api` proxy, so it does not depend on a hard-coded browser API host and avoids localhost/127.0.0.1 CORS mismatches during development.

## Quick API test

```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health"
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/simulate?scenario=DATABASE_LATENCY&seed=42" -Method Post | ConvertTo-Json -Depth 8
```

If the browser says **Backend Offline**, start Terminal 1 first, then refresh the frontend.
