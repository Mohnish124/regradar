# Demo script (about 8 minutes)

Before the viva: start the backend and frontend (run guide B and C) and delete old runs if you want a clean history.

## 1. Problem and architecture (1.5 min) - Architecture page

* "Indian fintechs receive frequent RBI/SEBI/MeitY circulars. RegRadar finds new obligations, checks them against our controls, and produces validated, prioritised gaps."
* Point to the graph: six agents, a conditional edge after the Novelty Validator, the **revise** loop back to the Gap Synthesiser, and **escalate** to human review.
* "Agents communicate only through a typed LangGraph shared state. The validator's feedback is a structured object in that state."

## 2. Run the demo (1 min) - Dashboard

* Click **Run deterministic demo**. Say clearly: "This is demo mode. The documents are synthetic, and the LLM is replaced by a deterministic responder, so the run is repeatable without an API key. The LangGraph execution, routing and validator checks are real."

## 3. Feedback loop (2.5 min) - Feedback Loop page

Walk through the rounds strip: Round 1 (7 accepted / 5 rejected), Round 2 (2 / 1), Round 3 (0 / 1), then Escalation.

| Gap | Clause | First-draft mistake | Validator code | Outcome |
|---|---|---|---|---|
| GAP-001 | RBI §3.1 (report incidents within 6 hours) | severity `low` (scripted) | `severity_understated` (expected critical) | revised -> accepted in round 2 |
| GAP-002 | RBI §3.2 (MFA) | proposed although CTRL-IAM-02 covers it (scripted) | `already_covered` | withdrawn |
| GAP-003 | RBI §3.3 (quarterly VAPT) | ignored the known-issues register (naive drafter) | `already_tracked` (KI-2026-011) | withdrawn, linked to KI |
| GAP-004 | RBI §3.4 (180-day logs) | paraphrased evidence (scripted) | `evidence_not_grounded` | verbatim quote -> accepted |
| GAP-006 | RBI §3.7 (should run cyber drills) | marked mandatory (naive drafter) | `non_mandatory_obligation` x3 | synthesiser defends it -> escalated |

Show the diff table on GAP-001 (`severity: low -> critical`) and the validator's message ("regulatory reporting deadline of 6 hours").

## 4. Trace (1 min) - Agent Trace page

* Filter type = `feedback`: seven rejection messages from the Novelty Validator to the Gap Synthesiser.
* Expand a payload to show the structured `issues` (code, field, expected).
* Point out the "Deterministic demo responder" labels and the timestamps and durations from the actual run.

## 5. Coverage and remediation (1 min)

* **Coverage Matrix**: 5 covered / 9 partial / 2 gap; show the shortfall text "control acts within 24h but regulation requires 6h".
* **Remediation Plan**: P1 items first; the score breakdown is transparent (severity x urgency x exposure).

## 6. Report and tests (1 min)

* **Final Report**: download the Markdown; point out the DEMO banner and disclaimers.
* Terminal: `python -m pytest tests/test_feedback_loop.py -v`. Mention that the main test asserts the order propose -> reject -> feedback received -> revise -> re-validate -> accept -> report from the persisted trace, and another test uses a non-demo scripted LLM to prove that feedback reaches the LLM through state.

## Optional: live mode

With `LLM_PROVIDER` configured: New Analysis -> Live -> "Insert sample text" -> Start. The trace then shows `Live LLM <provider>/<model>` labels.
