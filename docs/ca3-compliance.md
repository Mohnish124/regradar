# CA3 compliance checklist

**Important:** the original `RegRadar_Master_Build_Prompt_Updated.txt` (with the official CA3 rubric) was not available when this was built. The checklist below maps the requirements listed in the build brief to evidence in this repository. Re-map it against your actual rubric before submission. Nothing here guarantees marks.

| Requirement (from build brief) | Implementation | Evidence |
|---|---|---|
| Six specialised agents | Regulatory Scout, Obligation Extractor, Control Mapper, Gap Synthesiser, Novelty Validator, Output Agent | `backend/agents/*.py`, `/api/agents`, Architecture page |
| LangGraph orchestration | Compiled `StateGraph` with conditional edges | `backend/orchestration/graph.py` |
| Genuine communication via structured shared state | `RegRadarState` TypedDict; additive `trace`; `pending_feedback` | `orchestration/state.py`; `test_rejection_feedback_revision_and_revalidation_sequence` |
| Adaptive Synthesiser -> Validator -> Synthesiser loop | `route_after_validation` (finalise / revise / escalate), `max_revisions` | `test_router_decisions`, `test_max_revisions_zero_escalates_immediately` |
| Real execution traces and validator decisions | `AgentMessage`s persisted per run in SQLite | `/api/runs/{id}/trace`, Agent Trace page, `test_trace_is_ordered_and_persisted` |
| Escalation | Escalation node, `human_reviewer` messages | `test_withdrawals_and_escalation` |
| FastAPI backend | 18 endpoints, Swagger at `/docs` | `backend/api/routes.py`, `tests/test_api.py` |
| React + TypeScript + Vite frontend | 14 pages + 404, React Router, real API calls | `frontend/src/App.tsx`, `frontend/src/pages/` |
| Every navigation item has its own page | Dashboard, New Analysis, Run History, Agent Trace, Feedback Loop, Coverage Matrix, Gaps & Validation, Remediation Plan, Final Report, Regulations, Control Library, Architecture, Settings & Health (+ Run Overview) | Browser check of all routes (see final report) |
| Input / output / agent-message schemas | Pydantic models | `backend/schemas.py`, `frontend/src/types.ts` |
| Regulatory retrieval + labelled synthetic dataset | Dataset with `synthetic: true` + disclaimer; RBI/SEBI RSS; pasted docs | `data/demo/`, `backend/retrieval/sources.py`, `tests/test_sources.py` |
| Control knowledge base + coverage matrix | 16 controls, known-issues register; TF-IDF mapping with shortfall checks | `data/controls/`, `agents/control_mapper.py`, Coverage page |
| Gap synthesis, independent validation, prioritisation | Nine validator checks; risk-scored remediation plan | `agents/novelty_validator.py`, `agents/output_agent.py` |
| LLM integration | Anthropic + any OpenAI-compatible API; retries; JSON repair; fallback | `backend/llm/`, `test_feedback_reaches_synthesiser_llm_through_state`, `test_llm_failure_falls_back_and_is_reported` |
| Deterministic demo executing the real graph, clearly labelled | `DemoLLM`, `/api/demo/run`, `python -m backend.cli demo` | `llm/demo.py`, DEMO badges, report banner |
| Error handling | 400/404/409/422, source errors, LLM failures, failed runs | `test_api.py`, `test_sources.py`, `docs/architecture.md` §7 |
| Tests | 64 pytest tests (unit, orchestration, API, sources, deployment incl. PostgreSQL) | `tests/` |
| Cloud deployment | Vercel (FastAPI function + CDN dashboard), Neon Postgres persistence | `vercel.json`, `pyproject.toml [tool.vercel]`, `docs/deploy-vercel.md`, `tests/test_deployment.py` |
| Env vars, dependencies | `.env.example`, `requirements.txt`, `frontend/package.json` | `docs/environment-variables.md` |
| Docker + n8n | Dockerfiles, compose (with n8n profile), workflow JSON | `Dockerfile`, `frontend/Dockerfile`, `docker-compose.yml`, `n8n/` |
| Documentation | README, run guide, architecture, demo script, Q&A, references, this checklist | `README.md`, `docs/` |

## Known gaps to close yourself

* `frontend/package-lock.json` must be generated on your machine (`npm install`) and committed; the build sandbox could not reach the npm registry.
* Run `scripts\verify.ps1` once on your laptop and keep the output as evidence.
* Docker images and the n8n workflow were written but not executed in the build environment.
