# RegRadar architecture

## 1. Problem

Regulated companies (here: a fictional Indian payment aggregator, *Acme Pay*) receive a steady stream of circulars from regulators such as RBI, SEBI and MeitY. Compliance teams must work out which new obligations apply, whether existing controls already cover them, where the gaps are, and what to fix first. RegRadar automates that pipeline with six cooperating agents. An independent validator challenges every gap before it reaches the report.

## 2. System overview

```
React + TypeScript + Vite dashboard (frontend/)
        |  REST (JSON), CORS
FastAPI (backend/main.py, backend/api/routes.py)
        |
Runner (backend/orchestration/runner.py) --> SQLite (runs + messages)
        |
LangGraph StateGraph (backend/orchestration/graph.py)
   Regulatory Scout -> Obligation Extractor -> Control Mapper -> Gap Synthesiser <-> Novelty Validator -> [Escalation] -> Output Agent
        |                         |                    |                     |
  sources.py (dataset,     text.py (modal      knowledge.py         llm/ (demo responder |
  pasted docs, RSS)        verbs, params)      (controls, KIs)      Anthropic | OpenAI-compatible)
```

## 3. The six agents

| # | Agent | Reads from state | Writes to state | Reasoning |
|---|---|---|---|---|
| 1 | **Regulatory Scout** (`agents/regulatory_scout.py`) | `request` | `documents`, `source_errors` | Synthetic dataset (demo); pasted circulars + RBI/SEBI RSS (live); keyword relevance ranking |
| 2 | **Obligation Extractor** (`agents/obligation_extractor.py`) | `documents` | `obligations` | Modal-verb parser (shall/must = mandatory, should = recommended, may = permissive) plus parameter extraction (deadline hours, retention days, frequency). Live: LLM extraction, keeping only verbatim sentences (anti-hallucination) |
| 3 | **Control Mapper** (`agents/control_mapper.py`) | `obligations`, control library | `coverage` | Score = 0.65 x TF-IDF cosine + 0.35 x keyword overlap; covered >= 0.42 with no shortfall, partial >= 0.20; quantitative shortfall checks (e.g. 24h vs 6h, 90 vs 180 days, annual vs quarterly) |
| 4 | **Gap Synthesiser** (`agents/gap_synthesiser.py`) | `coverage`, `obligations`, `pending_feedback` | `gaps`, `revision_count`, clears `pending_feedback` | Draft mode (round 0) or revise mode (when feedback is pending). LLM in live mode, deterministic demo responder in demo mode, template fallback if the LLM fails |
| 5 | **Novelty Validator** (`agents/novelty_validator.py`) | `gaps`, `obligations`, `coverage`, known-issues register | gap statuses, `validation_decisions`, `pending_feedback`, `validation_round` | Nine independent rule checks (authoritative), plus an optional advisory LLM critique in live mode |
| 6 | **Output Agent** (`agents/output_agent.py`) | everything | `remediation_plan`, `report`, `status` | Risk score = severity weight x urgency x exposure x classification factor; P1/P2/P3 with target dates and owners; Markdown report; LLM executive summary in live mode |

### Novelty Validator checks

| Check | Issue code | Rejects when |
|---|---|---|
| obligation_exists | `unknown_obligation` | the gap points at an obligation not in this run |
| required_detail | `insufficient_detail` | title/description/action are too thin |
| citation_consistency | `citation_mismatch` | citation differs from the obligation's source |
| evidence_grounding | `evidence_not_grounded` | evidence quote is not verbatim from the obligation (paraphrase or hallucination) |
| not_already_covered | `already_covered` | the coverage matrix says a control already covers it |
| novel_vs_known_issues | `already_tracked` | the known-issues register already tracks it (not novel) |
| not_duplicate | `duplicate_proposal` | another accepted or earlier gap covers the same obligation |
| mandatory_classification | `non_mandatory_obligation` | a "should"/"may" obligation is raised as a mandatory gap |
| severity_calibration | `severity_understated` | severity is below the defensible minimum (e.g. 6-hour regulator reporting -> critical) |

Each issue carries `code`, `message`, `field` and `expected`, so the synthesiser can act on it programmatically.

## 4. Shared state and agent communication

`RegRadarState` (`orchestration/state.py`) is a `TypedDict`. Agents never call each other directly; they only read and write this state. `trace`, `errors` and `route_history` use LangGraph's additive reducer (`operator.add`), so every message is kept in order. All other keys are replaced by the latest writer.

Every agent emits `AgentMessage`s (`schemas.py`: sender, recipient, type, summary, payload, revision round, duration, LLM usage). These are appended to `trace` and persisted to SQLite when the run ends, giving a complete, replayable execution trace.

Non-serialisable dependencies (settings, LLM client, analysis date) live in a `RunContext` injected into agents at graph construction, not in state.

## 5. Graph and the adaptive feedback loop

```
START -> regulatory_scout --(documents?)--> obligation_extractor -> control_mapper -> gap_synthesiser -> novelty_validator
regulatory_scout --(no documents)--> output_agent
novelty_validator --route_after_validation-->
     "finalise"  (no rejected gaps)                  -> output_agent
     "revise"    (rejected and revision_count < max) -> gap_synthesiser
     "escalate"  (rejected and revision_count = max) -> escalation -> output_agent
output_agent -> END
```

One loop iteration:
1. The validator rejects a gap and writes a `ValidationDecision` (with structured issues) into `pending_feedback`.
2. `route_after_validation` sees rejected gaps and `revision_count < max_revisions` and returns `revise`.
3. The synthesiser finds `pending_feedback` non-empty, enters revise mode, and passes the rejected gaps plus the exact issues to the LLM (or demo responder).
4. For each gap it applies `revise`, `withdraw` or `maintain`, records the change history (field from/to), increments `revision_count` and clears `pending_feedback`.
5. The validator re-checks only `proposed`/`revised` gaps; accepted gaps stay locked.
6. At the limit, the escalation node marks remaining rejected gaps `escalated` and addresses a message to `human_reviewer`.

The loop is bounded by `max_revisions` (0-5) and LangGraph's recursion limit (60).

## 6. Demo mode vs live mode

| | Demo (`mode="demo"`) | Live (`mode="live"`) |
|---|---|---|
| Documents | Synthetic dataset, clearly labelled | Pasted circulars and/or RBI/SEBI RSS |
| "LLM" steps | `DemoLLM` deterministic responder | Anthropic or any OpenAI-compatible model |
| Graph, routing, validator checks, persistence | **Real** | **Real** |
| Labels | Every LLM-backed message has `reasoning_source="deterministic-demo"`; banner in report and UI | `llm:<provider>/<model>`, or `rule-based-fallback` on failure |

The demo responder's first draft contains three documented mistakes (`llm/demo.py: FIRST_DRAFT_SCRIPT`) plus a naive drafter's systematic weaknesses (everything "mandatory", ignores known issues). The validator does not know about the script. Its rejections come from its normal checks, and revisions are computed from its feedback codes (`revise_from_feedback`). One gap (§3.7) is deliberately defended by the synthesiser, which produces an escalation.

## 7. Error handling

* **LLM failures** (auth, timeout, 5xx, malformed JSON): retries with backoff, one JSON-repair attempt, then deterministic fallback, recorded as an `error` message with `llm.fallback=true`.
* **Live mode without credentials**: HTTP 400 before the run starts, with a clear message.
* **Malformed LLM output**: Pydantic validation; invalid gaps are dropped (and listed), invalid revision changes are ignored (and logged).
* **Unavailable sources**: listed in `source_errors`, the trace and the report; no fake data substitution.
* **Agent exceptions**: run marked `failed`, partial trace persisted, error shown in the dashboard.
* **Invalid input**: FastAPI/Pydantic 422 with field-level messages.

## 8. Persistence

SQLite via the standard library (`db.py`): table `runs` (request, status, stats, full result JSON) and table `messages` (one row per trace message). Runs survive restarts and can be deleted from the Run History page.

## 9. Key design decisions

* **Deterministic agents where determinism matters.** Mapping and validation are rule-based and explainable; LLMs are used for language tasks (extraction, drafting, revision, summaries). LLM output never overrides the validator.
* **Validator independence.** The validator re-derives facts from source data instead of trusting the synthesiser's fields.
* **Stdlib for I/O.** The LLM HTTP clients, RSS fetching, webhooks and SQLite use the standard library, which keeps dependencies small and Windows-friendly.
* **Honest demo.** Demo behaviour is labelled everywhere and the real graph always executes.
