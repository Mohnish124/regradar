# RegRadar - Run Guide (Windows 11, VS Code, PowerShell)

Every command below matches the actual code: backend entry point `backend.main:app`, frontend in `frontend/`, Vite on port 5173, API on port 8000.

You need two PowerShell terminals: **Terminal 1** for the backend, **Terminal 2** for the frontend.

---

## A. Initial setup (once)

### A1. Open the project

1. Unzip `regradar.zip` to a folder, for example `C:\Projects\regradar`. Avoid folders synced by OneDrive, which can lock SQLite files.
2. In VS Code choose **File > Open Folder...** and select `C:\Projects\regradar`.
3. Open a terminal with **Terminal > New Terminal**. Make sure it says `PowerShell` (not `cmd`) in the terminal dropdown.

```powershell
cd C:\Projects\regradar
```

### A2. Check the tools

```powershell
py --version        # need Python 3.11, 3.12 or 3.13
node --version      # need Node.js 20.19+ or 22.x
npm --version
git --version       # optional
```

Missing something?
* Python: <https://www.python.org/downloads/windows/> (tick "Add python.exe to PATH" and keep the "py launcher" option).
* Node.js LTS: <https://nodejs.org/>.

### A3. Create or reuse the virtual environment

```powershell
if (!(Test-Path .venv)) {
    py -m venv .venv
}
.\.venv\Scripts\Activate.ps1
```

Your prompt should now start with `(.venv)`. If activation is blocked, see [F1](#f1-powershell-blocks-venv-activation).

### A4. Install backend dependencies (into `.venv` only)

```powershell
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt   # runtime + test tools
python -m pip check
python -c "import sys; print(sys.executable)"
```

The last line must print a path ending in `regradar\.venv\Scripts\python.exe`. If it prints something else, activation did not work: use the direct-interpreter commands in F1.

Optional, to record exact versions for your submission:

```powershell
python -m pip freeze > requirements.lock.txt
```

### A5. Install frontend dependencies

```powershell
cd frontend
npm install          # first time: creates package-lock.json
cd ..
```

After `package-lock.json` exists, use `npm ci` for clean, reproducible installs. Commit `package-lock.json`.

### A6. Configure `.env` (optional for the demo)

```powershell
Copy-Item .env.example .env
notepad .env
```

The demo needs **no changes** to `.env`. To enable live LLM reasoning, see `docs/environment-variables.md`. The frontend has its own optional file:

```powershell
Copy-Item frontend\.env.example frontend\.env   # only if the API is not at http://127.0.0.1:8000
```

---

## B. Start the backend (Terminal 1)

```powershell
cd C:\Projects\regradar
.\.venv\Scripts\Activate.ps1
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

Wait for `Uvicorn running on http://127.0.0.1:8000`. Then check:

* Health: <http://127.0.0.1:8000/api/health> - expect `{"status":"ok", ...}`
* Interactive API docs (Swagger): <http://127.0.0.1:8000/docs>

Or from another terminal:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/api/health
```

The SQLite database is created automatically at `data\regradar.db`.

---

## C. Start the frontend (Terminal 2)

Open a second terminal (**Terminal > New Terminal**, or the `+` button):

```powershell
cd C:\Projects\regradar\frontend
if (!(Test-Path node_modules)) { npm install }
npm run dev
```

Open <http://localhost:5173> in your browser. The sidebar shows "API online - demo LLM" when the frontend can reach the backend.

---

## D. Run the demo and inspect the results

### D1. From the dashboard

Click **Run deterministic demo** on the Dashboard. You land on the **Feedback Loop** page of the new run. Then use the run's tabs: Overview, Trace, Feedback loop, Coverage, Gaps, Remediation, Report.

### D2. From PowerShell (API)

```powershell
$run = Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/demo/run
$run.id
$run.stats

# Execution trace (every agent message)
(Invoke-RestMethod "http://127.0.0.1:8000/api/runs/$($run.id)/trace").messages |
    Select-Object seq, sender, recipient, message_type, summary | Format-Table -Wrap

# Only the validator's rejections (structured feedback)
(Invoke-RestMethod "http://127.0.0.1:8000/api/runs/$($run.id)/trace?message_type=feedback").messages |
    Select-Object seq, summary

# Coverage matrix, gaps + validator decisions, remediation plan
Invoke-RestMethod "http://127.0.0.1:8000/api/runs/$($run.id)/coverage"
Invoke-RestMethod "http://127.0.0.1:8000/api/runs/$($run.id)/gaps"
Invoke-RestMethod "http://127.0.0.1:8000/api/runs/$($run.id)/remediation"

# Final report as Markdown file
Invoke-WebRequest "http://127.0.0.1:8000/api/runs/$($run.id)/report?format=md" -OutFile report.md
```

### D3. From PowerShell (CLI, no server needed)

```powershell
python -m backend.cli demo            # runs the real graph, prints route, stats and the full trace
python -m backend.cli demo --report   # also prints the Markdown report
python -m backend.cli runs            # lists stored runs
```

Expected demo outcome (deterministic): 3 documents, 16 obligations, coverage 5 covered / 9 partial / 2 gap, 12 gap proposals, 3 validation rounds, 2 revision cycles, 9 accepted, 2 withdrawn, 1 escalated.

---

## E. Run tests and checks

Run from the project root with `.venv` activated.

| Check | Command |
|---|---|
| All backend tests | `python -m pytest` |
| Deployment tests (Vercel mode, frontend serving) | `python -m pytest tests/test_deployment.py` |
| Backend unit tests | `python -m pytest tests/test_text_and_parsing.py tests/test_agents.py tests/test_sources.py` |
| Feedback-loop orchestration tests | `python -m pytest tests/test_feedback_loop.py -v` |
| API tests | `python -m pytest tests/test_api.py` |
| Python lint | `python -m ruff check backend tests` |
| Dependency verification | `python -m pip check` |
| Frontend lint | `cd frontend; npm run lint` |
| Frontend type checking | `cd frontend; npm run typecheck` |
| Frontend production build | `cd frontend; npm run build` |

Everything at once:

```powershell
powershell -ExecutionPolicy Bypass -File scripts\verify.ps1
```

---

## F. Troubleshooting

### F1. PowerShell blocks venv activation

Error: `Activate.ps1 cannot be loaded because running scripts is disabled on this system`.

Option 1 (recommended, current user only):

```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
```

Option 2: skip activation and call the venv interpreter directly:

```powershell
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
.\.venv\Scripts\python.exe -m pip check
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

### F2. A port is already in use

Error: `[WinError 10048] Only one usage of each socket address` (backend) or `Port 5173 is already in use` (frontend).

```powershell
Get-NetTCPConnection -LocalPort 8000 -State Listen | Select-Object OwningProcess
Stop-Process -Id <PID>
```

Or use another port, e.g. backend on 8001: start uvicorn with `--port 8001`, put `VITE_API_BASE_URL=http://127.0.0.1:8001` in `frontend\.env`, and restart `npm run dev`. For another frontend port, also add its origin to `CORS_ORIGINS` in `.env`.

### F3. API key missing or invalid

* Demo mode never needs a key.
* Live mode without a key returns HTTP 400: "Live LLM is not configured: ANTHROPIC_API_KEY is not set..." Fill in `.env` and restart the backend.
* An invalid key appears in the trace as an `error` message ("rejected the API key (HTTP 401)"), and the agents fall back to rule-based logic labelled `rule-based-fallback`.
* Check the setup on **Settings & Health** ("Live LLM ready: yes").

### F4. Backend not reachable

* Is Terminal 1 still running uvicorn without errors?
* Open <http://127.0.0.1:8000/api/health> directly in the browser.
* `ModuleNotFoundError: No module named 'backend'` means you started uvicorn from the wrong folder: `cd` to the project root first.
* `No module named 'fastapi'` or `'langgraph'` means the wrong Python: activate `.venv` or use `.\.venv\Scripts\python.exe`.

### F5. Frontend shows "Cannot reach the RegRadar API" (network error)

* Start the backend first (section B).
* Check `VITE_API_BASE_URL` in `frontend\.env` (default `http://127.0.0.1:8000`). Restart `npm run dev` after changing it; Vite reads env files at startup.

### F6. CORS errors in the browser console

The backend only accepts origins in `CORS_ORIGINS`. The default allows `http://localhost:5173` and `http://127.0.0.1:5173`. If you open the dashboard on another host or port, add it (comma-separated, no trailing slash) and restart the backend.

### F7. `npm install` fails

```powershell
cd frontend
npm cache verify
Remove-Item -Recurse -Force node_modules -ErrorAction SilentlyContinue
npm install
```

On a college network that blocks the npm registry, try a mobile hotspot. On `EBADENGINE`, upgrade Node.js to the current LTS.

### F8. Package version conflicts

```powershell
python -m pip check                     # shows the conflicting packages
Remove-Item -Recurse -Force .venv       # start clean
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
```

For npm peer-dependency errors: `npm install --legacy-peer-deps`.

### F9. The database cannot be opened

* Error `Cannot open database ...` or `database is locked`: close other programs using `data\regradar.db` (e.g. DB Browser for SQLite) and avoid OneDrive folders.
* To start fresh, stop the backend and delete the file: `Remove-Item data\regradar.db`. It is recreated on startup.
* `DATABASE_URL` must start with `sqlite:///`.

### F10. An external regulatory website is unavailable

Live mode fetches `rbi.org.in` and `sebi.gov.in` RSS feeds. If a site is down or blocked:
* the run still completes;
* each failure is listed in **Run Overview > Source errors**, in the trace as an `error` message and in the report's "Source errors" section;
* nothing is faked: if no source works, the graph routes straight from the Regulatory Scout to the Output Agent.

Workaround: paste the circular's text on **New Analysis**, or set `LIVE_SOURCES_ENABLED=false`.

---

## Single-server mode (what Vercel serves)

After `cd frontend; npm run build`, the backend also serves the built dashboard, so one command runs everything on port 8000:

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
# open http://127.0.0.1:8000  (dashboard + /api + /docs on one origin)
```

To go back to API-only mode, delete `frontend\dist` or set `SERVE_FRONTEND=false` in `.env`.

## Deploy to Vercel

See **[deploy-vercel.md](deploy-vercel.md)**.

## Docker (optional)

```powershell
docker compose up --build                            # API :8000, dashboard :5173
docker compose --profile integrations up --build     # also n8n :5678
```
