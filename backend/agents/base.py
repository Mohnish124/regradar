"""Common agent machinery: message emission, timing, LLM call wrapper."""

from __future__ import annotations

import logging
import time
import uuid
from typing import Any

from backend.llm.base import LLMError, LLMResult
from backend.orchestration.state import RegRadarState, RunContext
from backend.schemas import AgentMessage, LLMUsage, utcnow

log = logging.getLogger("regradar.agents")


class MessageBuffer:
    """Collects messages emitted during one node execution, numbering them globally."""

    def __init__(self, state: RegRadarState, ctx: RunContext, sender: str):
        self._offset = len(state.get("trace") or [])
        self.ctx = ctx
        self.sender = sender
        self.messages: list[dict[str, Any]] = []

    def emit(
        self,
        recipient: str,
        message_type: str,
        summary: str,
        payload: dict[str, Any] | None = None,
        revision_round: int = 0,
        duration_ms: float | None = None,
        llm: LLMUsage | None = None,
        sender: str | None = None,
    ) -> dict[str, Any]:
        msg = AgentMessage(
            id=uuid.uuid4().hex[:12],
            run_id=self.ctx.run_id,
            seq=self._offset + len(self.messages) + 1,
            timestamp=utcnow(),
            sender=sender or self.sender,
            recipient=recipient,
            message_type=message_type,  # type: ignore[arg-type]
            summary=summary,
            payload=payload or {},
            revision_round=revision_round,
            duration_ms=round(duration_ms, 2) if duration_ms is not None else None,
            llm=llm,
        )
        data = msg.model_dump(mode="json")
        self.messages.append(data)
        return data


class Agent:
    """Base class. Subclasses implement ``run(state, buf) -> dict``."""

    name: str = "agent"
    display_name: str = "Agent"
    role: str = ""

    def __init__(self, ctx: RunContext):
        self.ctx = ctx

    def __call__(self, state: RegRadarState) -> dict[str, Any]:
        buf = MessageBuffer(state, self.ctx, self.name)
        started = time.perf_counter()
        try:
            update = self.run(state, buf)
        except Exception as exc:  # an agent must never crash the run silently
            log.exception("Agent %s failed", self.name)
            buf.emit("orchestrator", "error", f"{self.display_name} failed: {exc}", {"error": repr(exc)})
            raise AgentFailure(self.name, str(exc), buf.messages) from exc
        elapsed = (time.perf_counter() - started) * 1000
        if buf.messages:
            # attribute node duration to the final summary message of the node
            buf.messages[-1]["duration_ms"] = round(elapsed, 2)
        update["trace"] = buf.messages
        update["route_history"] = [self.name]
        return update

    def run(self, state: RegRadarState, buf: MessageBuffer) -> dict[str, Any]:  # pragma: no cover
        raise NotImplementedError

    # ------------------------------------------------------------- LLM helper
    def call_llm(
        self, task: str, system: str, prompt: str, payload: dict[str, Any]
    ) -> tuple[LLMResult | None, LLMUsage]:
        """Call the run's LLM. Returns (result, usage); result is None on failure."""
        llm = self.ctx.llm
        try:
            result = llm.complete_json(task, system, prompt, payload)
        except (LLMError, ValueError) as exc:
            log.warning("LLM task %s failed for %s: %s", task, self.name, exc)
            return None, LLMUsage(
                provider=llm.provider,
                model=llm.model,
                reasoning_source="rule-based-fallback",
                fallback=True,
                error=str(exc)[:500],
            )
        return result, LLMUsage(provider=result.provider, model=result.model, reasoning_source=result.reasoning_source)


class AgentFailure(RuntimeError):
    def __init__(self, agent: str, message: str, messages: list[dict[str, Any]]):
        super().__init__(f"{agent}: {message}")
        self.agent = agent
        self.messages = messages
