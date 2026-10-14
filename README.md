# RegRadar - multi-agent regulatory change radar

RegRadar turns new regulatory circulars into **validated, prioritised compliance gaps**. Six LangGraph agents retrieve regulations, extract obligations, map them to internal controls, propose gaps, independently validate them in a **feedback loop**, and write a remediation report. A FastAPI backend serves a React + TypeScript dashboard.

> The demo uses a **synthetic** dataset (RBI/MeitY-style circulars) and a fictional company, *Acme Pay*. In demo mode the LLM is replaced by a **deterministic demo responder**; the LangGraph graph, routing, validator checks and trace are real. Every demo output is labelled as such.

## Highlights

* **Six agents:** Regulatory Scout -> Obligation Extractor -> Control Mapper -> Gap Synthesiser <-> Novelty Validator -> Output Agent.
* **Adaptive feedback loop:** the validator rejects gaps with structured feedback (issue code, field, expected value). The synthesiser receives it through shared state and revises, withdraws or defends each gap. The graph re-validates, then finalises or escalates to a human at the revision limit.
* **Nine independent validation checks:** evidence grounding, citation consistency, already covered, already tracked (novelty), duplicates, modality, severity calibration, detail, obligation existence.
* **Persistent execution traces** of every agent message, viewable in the dashboard.
* **Live mode:** Anthropic or any OpenAI-compatible model (OpenAI, Groq, Gemini, Ollama), pasted circulars, RBI/SEBI RSS feeds.
* **64 automated tests**, including tests that prove the rejection -> feedback -> revision -> re-validation sequence.
* **Deploys to Vercel** as one project: dashboard on the CDN, FastAPI/LangGraph as a Python function, optional free Neon Postgres for persistent run history. See **[docs/deploy-vercel.md](docs/deploy-vercel.md)**.

## Quick start (Windows PowerShell)

Full guide with troubleshooting: **[docs/run-guide.md](docs/run-guide.md)**.

```powershell
# Terminal 1 - backend (project root)
py -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements-dev.txt
python -m pip check
Copy-Item .env.example .env          # optional for the demo
python -m uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000
```

```powershell
# Terminal 2 - frontend
cd frontend
npm install
npm run dev
```

* Dashboard: <http://localhost:5173> -> click **Run deterministic demo**
* API health: <http://127.0.0.1:8000/api/health>
* API docs: <http://127.0.0.1:8000/docs>

Demo without the UI: `python -m backend.cli demo --report`, or `Invoke-RestMethod -Method Post http://127.0.0.1:8000/api/demo/run`.

If `Activate.ps1` is blocked: `Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`, or call `.\.venv\Scripts\python.exe` directly.

## Tests and checks

```powershell
python -m pytest                                  # all 64 backend tests
python -m pytest tests/test_feedback_loop.py -v   # feedback-loop proof
python -m ruff check backend tests
cd frontend; npm run lint; npm run typecheck; npm run build
```

Or run everything: `powershell -ExecutionPolicy Bypass -File scripts\verify.ps1`.

## Deploy to Vercel

Short version (full step-by-step guide with troubleshooting: **[docs/deploy-vercel.md](docs/deploy-vercel.md)**):

1. Push the repo to GitHub.
2. Vercel: **Add New > Project**, import the repo with root `./`. The FastAPI preset is detected, and `vercel.json` builds the dashboard.
3. Optional but recommended: **Storage > Create Database > Neon** (free) to get `DATABASE_URL`, then redeploy.
4. Optional: add `LLM_PROVIDER`, `LLM_MODEL` and an API key for live mode.
5. Check `https://<your-app>.vercel.app/api/health`, then open the dashboard.

## Environment variables

None are needed for the demo. For live LLM mode set `LLM_PROVIDER`, `LLM_MODEL` and `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` (+ `OPENAI_BASE_URL`). Full table: **[docs/environment-variables.md](docs/environment-variables.md)**.

## Project structure

```
backend/
  main.py              FastAPI app (entry point backend.main:app)
  api/routes.py        REST endpoints
  agents/              the six agents + shared policy rules + registry
  orchestration/       LangGraph state, graph (routing/loop/escalation), runner
  llm/                 demo responder, Anthropic + OpenAI-compatible clients
  retrieval/           sources (dataset, pasted docs, RSS), knowledge base, text utils
  integrations/        Slack / n8n notifications
  db.py, config.py, schemas.py, cli.py
data/demo/             synthetic regulations (labelled)
data/controls/         control library + known-issues register
frontend/              React + TypeScript + Vite dashboard
tests/                 pytest suites (unit, orchestration, API, sources)
docs/                  run guide, Vercel deploy guide, env vars, architecture, demo script, Q&A, references, CA3 checklist
n8n/                   n8n workflow (scheduled scan + Slack alert)
scripts/verify.ps1     one-shot verification for Windows
vercel.json, .vercelignore, .python-version   Vercel deployment config
requirements.txt (runtime), requirements-dev.txt (tests)
Dockerfile, frontend/Dockerfile, docker-compose.yml
```

## API overview

| Method | Path | Purpose |
|---|---|---|
| GET | `/api/health` | Liveness + DB check |
| GET | `/api/config` | Public configuration (no secrets) |
| GET | `/api/agents`, `/api/graph` | Agent registry, graph structure |
| GET | `/api/sources/demo-dataset`, `/api/controls` | Knowledge bases |
| POST | `/api/demo/run` | Deterministic demo through the real graph |
| POST | `/api/runs` | Run an analysis (`AnalysisRequest`) |
| GET | `/api/runs`, `/api/runs/latest`, `/api/runs/{id}` | Run list and detail |
| GET | `/api/runs/{id}/trace` | Execution trace (`?agent=`, `?message_type=`) |
| GET | `/api/runs/{id}/coverage`, `/gaps`, `/remediation` | Agent outputs |
| GET | `/api/runs/{id}/report?format=json\|md` | Final report |
| DELETE | `/api/runs/{id}` | Delete a run |
| POST | `/api/integrations/test` | Test Slack/n8n webhooks |

## Documentation

* [Run guide](docs/run-guide.md) - setup, running, testing, troubleshooting
* [Deploy on Vercel](docs/deploy-vercel.md)
* [Architecture](docs/architecture.md) - agents, state, graph, loop, error handling
* [Demo script](docs/demo-script.md) - what to show and say
* [Evaluator Q&A](docs/evaluator-qa.md)
* [References](docs/references.md)
* [CA3 compliance checklist](docs/ca3-compliance.md)

## Limitations

Lexical control mapping; small fictional control library; RSS feeds often contain summaries only; no authentication (single-user prototype); not legal advice.
