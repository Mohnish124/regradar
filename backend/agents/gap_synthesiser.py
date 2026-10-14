"""Agent 4 - Gap Synthesiser: proposes compliance gaps and revises them from validator feedback.

Round 0 (no pending feedback): draft gap proposals from the coverage matrix.
Round N (pending feedback in shared state): revise, withdraw or defend each
rejected proposal, addressing every issue the Novelty Validator raised.
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import ValidationError

from backend.agents.base import Agent, MessageBuffer
from backend.agents.policy import draft_gap_fields
from backend.retrieval.knowledge import load_control_library
from backend.schemas import GapProposal, GapRevisionRecord, LLMUsage

SYSTEM_DRAFT = (
    "You are a senior compliance analyst at a digital payments company. Given obligations and a "
    "coverage matrix (obligation -> best matching internal control), propose specific, actionable "
    "compliance gaps. Quote the regulation verbatim as evidence, cite it exactly, calibrate severity "
    "(low/medium/high/critical), and classify each gap as mandatory or advisory based on the modal verb."
)
SYSTEM_REVISE = (
    "You are a senior compliance analyst. An independent validator rejected some of your gap "
    "proposals with structured feedback. For each rejected gap decide: 'revise' (fix every issue), "
    "'withdraw' (if the validator is right that the gap is not real or not novel) or 'maintain' (only "
    "if you can justify it). Respond to the feedback explicitly."
)
REVISABLE_FIELDS = (
    "title", "description", "gap_type", "severity", "classification", "evidence_quote",
    "citation", "related_control_ids", "recommended_action",
)


class GapSynthesiser(Agent):
    name = "gap_synthesiser"
    display_name = "Gap Synthesiser"
    role = "Drafts gap proposals from the coverage matrix and revises them using the validator's structured feedback."

    # ---------------------------------------------------------------- drafting
    def _draft_payload(self, state) -> dict[str, Any]:
        lib = load_control_library()
        return {
            "coverage": state.get("coverage", []),
            "obligations": state.get("obligations", []),
            "controls": lib["controls"],
            "known_issues": lib.get("known_issues", []),
        }

    def _draft_prompt(self, payload: dict[str, Any]) -> str:
        items = [
            {k: c[k] for k in ("obligation_id", "citation", "obligation_text", "strength", "status",
                               "best_control_id", "best_control_title", "similarity", "shortfalls")}
            for c in payload["coverage"]
        ]
        controls = [{k: c[k] for k in ("id", "title", "description", "owner")} for c in payload["controls"]]
        return (
            f"Coverage matrix:\n{json.dumps(items, ensure_ascii=False)}\n\n"
            f"Control library:\n{json.dumps(controls, ensure_ascii=False)}\n\n"
            f"Known issues already tracked:\n{json.dumps(payload['known_issues'], ensure_ascii=False)}\n\n"
            'Propose gaps for obligations that are not fully covered. Return {"gaps": [{"obligation_id": str, '
            '"citation": str, "title": str, "description": str, "gap_type": "missing_control"|"parameter_shortfall"|'
            '"scope_gap"|"governance_gap", "severity": "low"|"medium"|"high"|"critical", "classification": '
            '"mandatory"|"advisory", "evidence_quote": str (verbatim from the obligation), "related_control_ids": '
            '[str], "recommended_action": str}]}'
        )

    def _template_gaps(self, payload: dict[str, Any]) -> list[dict[str, Any]]:
        controls = {c["id"]: c for c in payload["controls"]}
        obligations = {o["id"]: o for o in payload["obligations"]}
        return [
            draft_gap_fields(item, obligations[item["obligation_id"]], controls)
            for item in payload["coverage"]
            if item["status"] != "covered"
        ]

    def draft(self, state, buf: MessageBuffer) -> dict[str, Any]:
        payload = self._draft_payload(state)
        known_obligations = {o["id"] for o in payload["obligations"]}
        result, usage = self.call_llm("synthesise_gaps", SYSTEM_DRAFT, self._draft_prompt(payload), payload)
        if result is None:
            buf.emit("orchestrator", "error", "Gap drafting LLM call failed; using deterministic templates",
                     {"error": usage.error}, llm=usage)
            raw_gaps = self._template_gaps(payload)
        else:
            raw_gaps = result.data.get("gaps", [])

        gaps: list[GapProposal] = []
        dropped: list[str] = []
        for i, raw in enumerate(raw_gaps, start=1):
            if not isinstance(raw, dict) or raw.get("obligation_id") not in known_obligations:
                dropped.append(str(raw.get("obligation_id") if isinstance(raw, dict) else raw)[:80])
                continue
            try:
                gap = GapProposal(
                    id=f"GAP-{i:03d}",
                    status="proposed",
                    revision=0,
                    reasoning_source=usage.reasoning_source,
                    **{k: raw[k] for k in ("obligation_id", "citation", "title", "description", "gap_type",
                                           "severity", "classification", "evidence_quote",
                                           "related_control_ids", "recommended_action") if k in raw},
                )
            except (ValidationError, TypeError) as exc:
                dropped.append(f"{raw.get('obligation_id')}: {str(exc).splitlines()[0]}")
                continue
            gap.history.append(GapRevisionRecord(revision=0, action="proposed", reasoning_source=usage.reasoning_source))
            gaps.append(gap)

        for gap in gaps:
            buf.emit(
                "novelty_validator", "proposal",
                f"{gap.id} proposed: {gap.title} [{gap.severity}, {gap.classification}]",
                {"gap": gap.model_dump(mode="json")}, revision_round=0, llm=usage,
            )
        buf.emit(
            "novelty_validator", "result",
            f"Drafted {len(gaps)} gap proposal(s) for validation" + (f"; dropped {len(dropped)} malformed" if dropped else ""),
            {"gap_ids": [g.id for g in gaps], "dropped": dropped}, llm=usage,
        )
        return {"gaps": [g.model_dump(mode="json") for g in gaps], "revision_count": 0}

    # ---------------------------------------------------------------- revising
    def revise(self, state, buf: MessageBuffer) -> dict[str, Any]:
        feedback = state.get("pending_feedback", [])
        round_no = state.get("revision_count", 0) + 1
        gaps = {g["id"]: GapProposal.model_validate(g) for g in state.get("gaps", [])}
        obligations = {o["id"]: o for o in state.get("obligations", [])}
        coverage = {c["obligation_id"]: c for c in state.get("coverage", [])}

        rejected_entries = []
        for fb in feedback:
            gap = gaps[fb["gap_id"]]
            rejected_entries.append({
                "gap": gap.model_dump(mode="json"),
                "issues": fb["issues"],
                "obligation_text": obligations.get(gap.obligation_id, {}).get("text", ""),
                "obligation_strength": obligations.get(gap.obligation_id, {}).get("strength"),
                "coverage": coverage.get(gap.obligation_id),
            })
        buf.emit(
            "orchestrator", "info",
            f"Received {len(feedback)} rejection(s) with structured feedback via shared state (validation round {feedback[0]['round'] if feedback else '?'})",
            {"feedback": feedback}, revision_round=round_no,
        )

        prompt = (
            f"Rejected proposals with validator feedback:\n{json.dumps(rejected_entries, ensure_ascii=False)}\n\n"
            'Return {"revisions": [{"gap_id": str, "action": "revise"|"withdraw"|"maintain", '
            '"changes": {<field>: <new value>}, "response_to_feedback": str, "known_issue_id": str|null}]}. '
            f"Revisable fields: {', '.join(REVISABLE_FIELDS)}."
        )
        result, usage = self.call_llm("revise_gaps", SYSTEM_REVISE, prompt, {"rejected": rejected_entries})
        if result is None:
            buf.emit("orchestrator", "error", "Revision LLM call failed; applying deterministic feedback rules",
                     {"error": usage.error}, llm=usage, revision_round=round_no)
            from backend.llm.demo import revise_from_feedback  # deterministic rules, also used by demo
            revisions = [revise_from_feedback(e) for e in rejected_entries]
        else:
            revisions = result.data.get("revisions", [])

        by_gap = {str(r.get("gap_id")): r for r in revisions if isinstance(r, dict)}
        for fb in feedback:
            gap = gaps[fb["gap_id"]]
            rev = by_gap.get(gap.id) or {"action": "maintain", "response_to_feedback": "No response produced for this gap."}
            self._apply(gap, rev, round_no, usage, buf)

        return {
            "gaps": [g.model_dump(mode="json") for g in gaps.values()],
            "pending_feedback": [],
            "revision_count": round_no,
        }

    def _apply(self, gap: GapProposal, rev: dict[str, Any], round_no: int, usage: LLMUsage, buf: MessageBuffer) -> None:
        action = str(rev.get("action", "maintain")).lower()
        response = str(rev.get("response_to_feedback", ""))[:1000]
        before = gap.model_dump(mode="json")
        applied: dict[str, Any] = {}
        if action == "withdraw":
            gap.status = "withdrawn"
            if rev.get("known_issue_id"):
                gap.known_issue_id = str(rev["known_issue_id"])
            record_action = "withdrawn"
        else:
            if action == "revise":
                for key, value in (rev.get("changes") or {}).items():
                    if key in REVISABLE_FIELDS:
                        applied[key] = value
                try:  # re-validate literals/types before applying LLM-proposed changes
                    GapProposal.model_validate({**gap.model_dump(), **applied})
                except ValidationError as exc:
                    buf.emit("orchestrator", "error", f"{gap.id}: proposed changes failed schema validation; ignored",
                             {"error": str(exc).splitlines()[0], "changes": applied}, revision_round=round_no)
                    applied = {}
            for key, value in applied.items():
                setattr(gap, key, value)
            gap.status = "revised"
            gap.revision = round_no
            record_action = "revised" if action == "revise" and applied else "maintained"
        gap.response_to_feedback = response
        gap.reasoning_source = usage.reasoning_source
        gap.history.append(GapRevisionRecord(
            revision=round_no, action=record_action,  # type: ignore[arg-type]
            changes={k: {"from": before.get(k), "to": v} for k, v in applied.items()},
            response_to_feedback=response, reasoning_source=usage.reasoning_source,
        ))
        recipient = "output_agent" if record_action == "withdrawn" else "novelty_validator"
        buf.emit(
            recipient, "revision",
            f"{gap.id} {record_action} (revision {round_no}): {response}",
            {"gap_id": gap.id, "action": record_action, "changes": gap.history[-1].changes,
             "gap": gap.model_dump(mode="json")},
            revision_round=round_no, llm=usage,
        )

    def run(self, state, buf: MessageBuffer) -> dict[str, Any]:
        if state.get("pending_feedback"):
            return self.revise(state, buf)
        return self.draft(state, buf)
