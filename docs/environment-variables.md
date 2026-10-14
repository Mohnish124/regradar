# Environment variables

The backend reads these variables (see `backend/config.py`) from the process environment, after loading `.env` from the project root. Variables already set in the environment take precedence over `.env`.

**None are required for the deterministic demo.** Live LLM mode requires `LLM_PROVIDER`, `LLM_MODEL` and a matching key.

Create your local file:

```powershell
Copy-Item .env.example .env
notepad .env
```

After any change, restart the backend. Then check **Settings & Health** in the dashboard, or `Invoke-RestMethod http://127.0.0.1:8000/api/config`. That endpoint reports only whether a key is set, never its value.

## Backend (`.env` in project root)

| Variable | Purpose | Required? | Example / format | Where to get it | Runs without it? | How to test |
|---|---|---|---|---|---|---|
| `APP_ENV` | Label shown in `/api/config` | No (default `development`) | `development` | - | Yes | `/api/config` -> `app_env` |
| `LOG_LEVEL` | Python log level | No (default `INFO`) | `DEBUG`, `INFO`, `WARNING` | - | Yes | Uvicorn console shows more or fewer lines |
| `DATABASE_URL` | Where runs and traces are stored: SQLite file or PostgreSQL | No (default `sqlite:///./data/regradar.db`; on Vercel `sqlite:////tmp/regradar.db`, temporary) | `sqlite:///./data/regradar.db`, `postgresql://user:pass@ep-xxx.neon.tech/neondb?sslmode=require` | Neon via Vercel **Storage** tab (free plan) injects it automatically | Yes | `/api/health` -> `storage`, `storage_persistent` |
| `POSTGRES_URL` | Fallback name read when `DATABASE_URL` is empty (some Vercel integrations use it) | No | same format | Injected by the integration | Yes | same as above |
| `CORS_ORIGINS` | Browser origins allowed to call the API | No (default `http://localhost:5173,http://127.0.0.1:5173`) | comma-separated, no trailing `/` | - | Yes | Dashboard loads with no CORS error in the browser console (F12) |
| `LLM_PROVIDER` | `demo`, `anthropic`, or `openai` (any OpenAI-compatible API) | Only for live mode (default `demo`) | `anthropic` | - | Yes (demo) | Settings page -> LLM_PROVIDER |
| `LLM_MODEL` | Model name for live mode | Yes if provider is not `demo` | Check your provider's current model list | Provider docs | Yes (demo) | Settings -> "Live LLM ready: yes" |
| `LLM_TEMPERATURE` | Sampling temperature | No (default `0.1`) | `0.1` | - | Yes | - |
| `LLM_TIMEOUT_SECONDS` | Per-request timeout | No (default `60`, range 5-600) | `60` | - | Yes | Slow providers stop failing with "timed out" |
| `LLM_MAX_RETRIES` | Retries on 429/5xx/timeouts | No (default `2`, range 0-5) | `2` | - | Yes | - |
| `ANTHROPIC_API_KEY` | Anthropic API key | Only if `LLM_PROVIDER=anthropic` | `sk-ant-...` | <https://console.anthropic.com/> -> API Keys (paid usage) | Yes | Live run trace shows `Live LLM anthropic/<model>` and no 401 errors |
| `ANTHROPIC_BASE_URL` | Anthropic endpoint | No | `https://api.anthropic.com` | - | Yes | - |
| `OPENAI_API_KEY` | Key for the OpenAI-compatible provider | Only if `LLM_PROVIDER=openai` with a cloud provider | `sk-...`, `gsk_...` | OpenAI: <https://platform.openai.com/api-keys>; Groq (free tier): <https://console.groq.com/keys>; Google Gemini (free tier): <https://aistudio.google.com/apikey> | Yes | Live run completes without `rule-based-fallback` labels |
| `OPENAI_BASE_URL` | Endpoint for the OpenAI-compatible API | No (default `https://api.openai.com/v1`) | Groq `https://api.groq.com/openai/v1`; Gemini `https://generativelanguage.googleapis.com/v1beta/openai`; Ollama `http://localhost:11434/v1` | Provider docs | Yes | Same as above |
| `MAX_REVISIONS` | Default revision cycles in the feedback loop | No (default `2`, range 0-5) | `2` | - | Yes | Run overview shows "Max revisions" |
| `LIVE_SOURCES_ENABLED` | Allow fetching RBI/SEBI RSS | No (default `true`) | `true` / `false` | - | Yes | Live run with feeds -> documents with source `live-rss` |
| `SOURCE_TIMEOUT_SECONDS` | Timeout per feed/page fetch | No (default `15`) | `15` | - | Yes | - |
| `RBI_RSS_URL` | RBI notifications feed | No | `https://www.rbi.org.in/notifications_rss.xml` | Public, no key | Yes | Live run trace "RBI RSS (N items)" |
| `SEBI_RSS_URL` | SEBI feed | No | `https://www.sebi.gov.in/sebirss.xml` | Public, no key | Yes | Live run trace "SEBI RSS (N items)" |
| `SERVE_FRONTEND` | Serve `frontend/dist` from FastAPI when it exists (single-server / Vercel) | No (default `true`) | `true` / `false` | - | Yes | `http://127.0.0.1:8000/` shows the dashboard after `npm run build` |
| `FRONTEND_DIR` | Location of the built dashboard | No (default `frontend/dist`) | `frontend/dist` | - | Yes | - |
| `SLACK_WEBHOOK_URL` | Post run summaries to Slack | No | `https://hooks.slack.com/services/...` | <https://api.slack.com/messaging/webhooks> | Yes | Settings -> "Send test notification" |
| `N8N_WEBHOOK_URL` | Send `run.completed` events to n8n | No | `http://localhost:5678/webhook/regradar` (Docker: `http://n8n:5678/webhook/regradar`) | Your n8n Webhook node (production URL) | Yes | Settings -> "Send test notification"; execution appears in n8n |

Notes:
* The regulatory sources (RBI, SEBI RSS) are public and need **no API keys**.
* Ollama runs locally and free: install from <https://ollama.com/>, `ollama pull <model>`, then set `LLM_PROVIDER=openai`, `OPENAI_BASE_URL=http://localhost:11434/v1`, `LLM_MODEL=<model>`. No key is needed for localhost.
* Model names change often; copy one from your provider's current documentation instead of guessing.

## On Vercel

Set variables in **Project > Settings > Environment Variables**, then redeploy. Vercel sets `VERCEL=1` itself; RegRadar uses it to pick `/tmp` storage when no database is connected.

| Variable | On Vercel |
|---|---|
| `DATABASE_URL` / `POSTGRES_URL` | Added automatically when you connect Neon in the Storage tab (recommended) |
| `LLM_PROVIDER`, `LLM_MODEL`, `ANTHROPIC_API_KEY` / `OPENAI_API_KEY`, `OPENAI_BASE_URL` | Only for live mode |
| `MAX_REVISIONS`, `SLACK_WEBHOOK_URL`, `N8N_WEBHOOK_URL`, `LOG_LEVEL` | Optional |
| `VITE_API_BASE_URL`, `CORS_ORIGINS`, `SERVE_FRONTEND`, `FRONTEND_DIR` | **Do not set.** The dashboard and API share one origin |

Full walkthrough: [deploy-vercel.md](deploy-vercel.md).

## Frontend (`frontend/.env`)

| Variable | Purpose | Required? | Default | How to test |
|---|---|---|---|---|
| `VITE_API_BASE_URL` | Backend URL used by the dashboard | No | `npm run dev`: `http://127.0.0.1:8000`; production build: same origin (relative `/api`) | Sidebar shows "API online". Restart `npm run dev` after changes. Leave unset on Vercel. |

`VITE_` variables are compiled into the browser bundle, so never put secrets in `frontend/.env`. The dashboard never receives API keys: `/api/config` only reports `*_api_key_set: true/false`.

## n8n (only if you import `n8n/regradar_workflow.json`)

The workflow reads `REGRADAR_API_URL` (default `http://backend:8000`) and `SLACK_WEBHOOK_URL` from the **n8n** container's environment. Set them in `docker-compose.yml` under the `n8n` service if you use the scheduled scan.
