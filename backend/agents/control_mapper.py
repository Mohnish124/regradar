"""Agent 3 - Control Mapper: maps obligations to internal controls (coverage matrix)."""

from __future__ import annotations

from typing import Any

from backend.agents.base import Agent, MessageBuffer
from backend.retrieval.knowledge import load_control_library
from backend.retrieval.text import TfidfIndex, keyword_overlap
from backend.schemas import ControlCandidate, CoverageItem, Obligation

COVERED_THRESHOLD = 0.42
PARTIAL_THRESHOLD = 0.20
COSINE_WEIGHT = 0.65
KEYWORD_WEIGHT = 0.35


def control_text(control: dict[str, Any]) -> str:
    return " ".join([control["title"], control["description"], " ".join(control.get("keywords", []))])


def find_shortfalls(obligation: Obligation, control: dict[str, Any]) -> list[str]:
    """Compare quantitative requirements with the control's documented parameters."""
    req = obligation.parameters
    have = control.get("parameters") or {}
    out: list[str] = []
    if req.deadline_hours is not None and have.get("deadline_hours") is not None:
        if have["deadline_hours"] > req.deadline_hours:
            out.append(f"control acts within {have['deadline_hours']:g}h but regulation requires {req.deadline_hours:g}h")
    if req.retention_days is not None and have.get("retention_days") is not None:
        if have["retention_days"] < req.retention_days:
            out.append(f"control retains {have['retention_days']:g} days but regulation requires {req.retention_days:g} days")
    if req.frequency_per_year is not None and have.get("frequency_per_year") is not None:
        if have["frequency_per_year"] < req.frequency_per_year:
            out.append(
                f"control runs {have.get('frequency', str(have['frequency_per_year']) + 'x/yr')} "
                f"but regulation requires {req.frequency}"
            )
    return out


class ControlMapper(Agent):
    name = "control_mapper"
    display_name = "Control Mapper"
    role = "Scores every obligation against the control library (TF-IDF + keyword overlap) and checks quantitative shortfalls."

    def run(self, state, buf: MessageBuffer) -> dict[str, Any]:
        controls = load_control_library()["controls"]
        obligations = [Obligation.model_validate(o) for o in state.get("obligations", [])]
        index = TfidfIndex([control_text(c) for c in controls] + [o.text for o in obligations])
        control_vecs = [(c, index.vector(control_text(c))) for c in controls]

        coverage: list[CoverageItem] = []
        for ob in obligations:
            ov = index.vector(ob.text)
            scored = []
            for control, cv in control_vecs:
                score = COSINE_WEIGHT * index.cosine(ov, cv) + KEYWORD_WEIGHT * keyword_overlap(ob.text, control.get("keywords", []))
                scored.append((round(score, 3), control))
            scored.sort(key=lambda s: s[0], reverse=True)
            best_score, best = scored[0] if scored else (0.0, None)
            shortfalls = find_shortfalls(ob, best) if best and best_score >= PARTIAL_THRESHOLD else []
            if best_score >= COVERED_THRESHOLD and not shortfalls:
                status = "covered"
                rationale = f"{best['id']} addresses the obligation (score {best_score:.2f} >= {COVERED_THRESHOLD})."
            elif best_score >= PARTIAL_THRESHOLD:
                status = "partial"
                rationale = (
                    f"{best['id']} is related (score {best_score:.2f})"
                    + (f" but has shortfalls: {'; '.join(shortfalls)}." if shortfalls else
                       f" but below the coverage threshold {COVERED_THRESHOLD}.")
                )
            else:
                status = "gap"
                rationale = f"No control scores above {PARTIAL_THRESHOLD} (best {best_score:.2f})."
            linked = best if status != "gap" else None
            coverage.append(
                CoverageItem(
                    obligation_id=ob.id,
                    citation=ob.citation,
                    regulator=ob.regulator,
                    obligation_text=ob.text,
                    strength=ob.strength,
                    status=status,  # type: ignore[arg-type]
                    best_control_id=linked["id"] if linked else None,
                    best_control_title=linked["title"] if linked else None,
                    similarity=best_score,
                    candidates=[ControlCandidate(control_id=c["id"], title=c["title"], score=s) for s, c in scored[:3]],
                    shortfalls=shortfalls,
                    rationale=rationale,
                )
            )

        counts = {k: sum(1 for c in coverage if c.status == k) for k in ("covered", "partial", "gap")}
        buf.emit(
            "gap_synthesiser",
            "result",
            f"Coverage matrix built: {counts['covered']} covered, {counts['partial']} partial, {counts['gap']} gap "
            f"across {len(controls)} controls",
            {
                "counts": counts,
                "thresholds": {"covered": COVERED_THRESHOLD, "partial": PARTIAL_THRESHOLD},
                "method": f"{COSINE_WEIGHT} x TF-IDF cosine + {KEYWORD_WEIGHT} x keyword overlap, plus parameter shortfall checks",
                "matrix": [
                    {"obligation_id": c.obligation_id, "status": c.status, "control": c.best_control_id,
                     "score": c.similarity, "shortfalls": c.shortfalls}
                    for c in coverage
                ],
            },
        )
        return {"coverage": [c.model_dump(mode="json") for c in coverage]}
