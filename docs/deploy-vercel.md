# Deploying RegRadar on Vercel

RegRadar deploys as **one Vercel project** on one domain:

```
https://<your-project>.vercel.app/            -> React dashboard (built by Vite, served from Vercel's CDN)
https://<your-project>.vercel.app/api/...     -> FastAPI + LangGraph backend (one Vercel Python Function)
https://<your-project>.vercel.app/docs        -> Swagger API docs
```

Because the dashboard and API share one origin, there is **no CORS setup** and **no `VITE_API_BASE_URL`** to configure.

## How it works (files already in the repo)

| File | What it does |
|---|---|
| `pyproject.toml` -> `[tool.vercel] entrypoint = "backend.main:app"` | Tells Vercel where the FastAPI `app` is |
| `pyproject.toml` -> `[tool.vercel.fastapi.static] cdn = true` | Serves the built dashboard from the CDN |
| `requirements.txt` / `[project].dependencies` | Runtime packages only (FastAPI, LangGraph, psycopg). Test tools live in `requirements-dev.txt` |
| `.python-version` | Python 3.12 |
| `vercel.json` -> `buildCommand` | `cd frontend && npm install && npm run build` -> creates `frontend/dist` |
| `vercel.json` -> `functions["backend/main.py"]` | 300 s max duration (the Hobby-plan maximum) and excludes tests/docs/node_modules from the function bundle |
| `.vercelignore` | Keeps `.venv`, `node_modules`, local `.db` files and `.env` out of the upload |
| `backend/main.py` | Calls `app.frontend("/", directory="frontend/dist")` when the build exists, so React Router deep links like `/runs/<id>/trace` work on refresh |
| `backend/config.py` | Detects Vercel (`VERCEL=1`) and picks storage (see below) |

## Storage: connect a free Postgres database (recommended)

Vercel functions cannot keep files: only `/tmp` is writable, and it is wiped whenever an instance stops.

* **Without a database**, RegRadar still works. Runs are stored in `/tmp/regradar.db`, and the dashboard shows a yellow "Temporary run storage" banner. Run history and traces can disappear between visits, or when Vercel routes a request to a different instance.
* **With Postgres**, runs and traces persist. RegRadar reads `DATABASE_URL` (or `POSTGRES_URL`) and creates its tables automatically on first start.

Neon has a free plan and integrates with Vercel (step 4 below).

---

## Step-by-step: deploy from GitHub (recommended)

### 1. Check that it builds locally (optional but saves time)

```powershell
cd C:\Projects\regradar\frontend
npm install
npm run build
cd ..
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements-dev.txt
python -m pytest
```

Single-server preview of exactly what Vercel will serve (dashboard + API on one port):

```powershell
python -m uvicorn backend.main:app --host 127.0.0.1 --port 8000
```

Open <http://127.0.0.1:8000> and you should see the dashboard, not JSON. Stop it with `Ctrl+C`.

### 2. Push the project to GitHub

Create an **empty** repository on <https://github.com/new> (for example `regradar`, no README). Then:

```powershell
cd C:\Projects\regradar
git init
git add .
git commit -m "RegRadar CA3 project"
git branch -M main
git remote add origin https://github.com/<your-username>/regradar.git
git push -u origin main
```

Check on GitHub that `.env`, `.venv` and `frontend/node_modules` were **not** uploaded (`.gitignore` excludes them). Do commit `frontend/package-lock.json`.

### 3. Import the repository into Vercel

1. Sign in at <https://vercel.com> with your GitHub account (the Hobby plan is free).
2. Click **Add New... > Project**, find `regradar` and click **Import**.
3. On the configuration screen:
   * **Root Directory:** leave as `./` (the project root, not `frontend`).
   * **Framework Preset:** it should detect **FastAPI**. If it shows something else, choose FastAPI.
   * **Build Command / Output Directory / Install Command:** leave the defaults. `vercel.json` provides the build command.
   * **Environment Variables:** none are required for the demo. Add LLM keys now or later (step 5).
4. Click **Deploy** and wait for the build. In the build log you should see Python packages installing, then `vite build` creating `frontend/dist`.

### 4. Add the free Neon Postgres database

1. In your Vercel project, open the **Storage** tab, click **Create Database** (or **Browse Marketplace**), and choose **Neon** (Serverless Postgres).
2. Accept the free plan, choose a region close to India (e.g. Singapore, `ap-southeast-1`), and **connect it to this project** for Production, Preview and Development.
3. Go to **Settings > Environment Variables** and confirm a `DATABASE_URL` (or `POSTGRES_URL`) variable now exists. It starts with `postgresql://` or `postgres://`.
4. Redeploy so the function picks it up: **Deployments** tab, the three-dot menu on the latest deployment, **Redeploy**.

### 5. (Optional) Enable live LLM mode

**Settings > Environment Variables**, add for *Production* (and *Preview* if you want):

| Name | Example value |
|---|---|
| `LLM_PROVIDER` | `anthropic` or `openai` |
| `LLM_MODEL` | a current model name from your provider's docs |
| `ANTHROPIC_API_KEY` | your key (if provider is `anthropic`) |
| `OPENAI_API_KEY` | your key (if provider is `openai`) |
| `OPENAI_BASE_URL` | e.g. `https://api.groq.com/openai/v1` for Groq (free tier) |
| `MAX_REVISIONS` | `2` (optional) |
| `SLACK_WEBHOOK_URL` | optional |

Do **not** set `VITE_API_BASE_URL`, `CORS_ORIGINS` or `SERVE_FRONTEND` on Vercel; the defaults are correct. Ollama (`localhost`) cannot be reached from Vercel. Redeploy after changing variables.

### 6. Verify the deployment

Replace `<url>` with your deployment URL (shown on the project page, e.g. `https://regradar-yourname.vercel.app`).

```powershell
$u = "https://<url>"
Invoke-RestMethod "$u/api/health"
```

Expected: `status: ok`, `deployment: vercel`, `storage: postgresql (...)`, `storage_persistent: True`. Without Neon you will see `sqlite (regradar.db, temporary /tmp)` and `False`.

```powershell
$run = Invoke-RestMethod -Method Post "$u/api/demo/run"
$run.status            # completed
$run.stats             # 16 obligations, 9 accepted, 2 withdrawn, 1 escalated
(Invoke-RestMethod "$u/api/runs/$($run.id)/trace?message_type=feedback").count   # 7
```

Then in the browser:

* `https://<url>/` shows the Dashboard. Click **Run deterministic demo**.
* Refresh the browser on `https://<url>/feedback-loop` and `https://<url>/runs/<id>/trace`: the pages must load, not 404.
* **Settings & Health** shows Deployment `vercel` and Run storage `postgresql (...)` with a green "yes".
* `https://<url>/docs` opens the Swagger UI.

Every `git push` to `main` now redeploys automatically; pushes to other branches create preview URLs.

---

## Alternative: deploy with the Vercel CLI (no GitHub)

```powershell
npm install -g vercel
cd C:\Projects\regradar
vercel login
vercel            # first run: link/create the project, accept the detected settings -> preview URL
vercel --prod     # production deployment
```

Add environment variables from the CLI if you prefer, e.g. `vercel env add LLM_PROVIDER production`, then run `vercel --prod` again. Install Neon from the CLI with `vercel i neon` (the command shown on Vercel's Neon Marketplace page), or use the dashboard as in step 4.

---

## Troubleshooting

| Symptom | Cause and fix |
|---|---|
| Build fails at `npm install` / `npm run build` | Run `cd frontend; npm install; npm run build` locally and fix any TypeScript error it prints; commit `package-lock.json`. Check the Vercel build log for the first red line. |
| Build fails installing Python packages | Make sure `requirements.txt` was pushed and is unchanged. The project must be imported from the repo **root**, not `frontend/`. |
| `https://<url>/` returns JSON `{"name":"RegRadar API",...}` instead of the dashboard | The frontend build did not run or produced no `frontend/dist`. Check that `vercel.json` is in the repo root and look for `vite build` in the build log. Make sure no Build Command override is set in **Settings > Build and Deployment**. |
| Refreshing `/runs/...` gives 404 | Same cause as above: `frontend/dist/index.html` was not built into the deployment. |
| Dashboard says "Cannot reach the RegRadar API" | Open `https://<url>/api/health`. If that fails, check **Deployments > (latest) > Logs / Functions** for the Python error. You must not have `VITE_API_BASE_URL` set to localhost in Vercel's environment variables. |
| Yellow "Temporary run storage" banner | No database connected. Do step 4 and redeploy. |
| `Cannot connect to PostgreSQL` in health/logs | `DATABASE_URL` is wrong or the Neon database is paused or deleted. Copy the connection string again from the Storage tab (keep `?sslmode=require`) and redeploy. |
| Live run returns HTTP 400 "Live LLM is not configured" | Set `LLM_PROVIDER`, `LLM_MODEL` and the matching API key in Vercel env vars, then redeploy. |
| Live run times out (504) | The LLM is slow. Use a faster model, lower `MAX_REVISIONS`, or set `LLM_TIMEOUT_SECONDS=30`. The Hobby plan allows 300 s per request. |
| Live RSS feeds fail on Vercel | The RBI/SEBI sites sometimes block cloud IPs. Errors are shown in Run Overview > Source errors; paste the circular text instead. |

## Local development is unchanged

`npm run dev` (port 5173) + `uvicorn` (port 8000) work exactly as before; the dev frontend still calls `http://127.0.0.1:8000`. See [run-guide.md](run-guide.md).
