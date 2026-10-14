export const AGENT_LABELS: Record<string, string> = {
  orchestrator: "Orchestrator",
  regulatory_scout: "Regulatory Scout",
  obligation_extractor: "Obligation Extractor",
  control_mapper: "Control Mapper",
  gap_synthesiser: "Gap Synthesiser",
  novelty_validator: "Novelty Validator",
  output_agent: "Output Agent",
  human_reviewer: "Human Reviewer",
  escalation: "Escalation",
};

export const AGENT_ORDER = [
  "orchestrator", "regulatory_scout", "obligation_extractor", "control_mapper",
  "gap_synthesiser", "novelty_validator", "output_agent", "human_reviewer",
];

export function agentLabel(name: string): string {
  return AGENT_LABELS[name] ?? name;
}

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "-";
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

export function shortId(id: string): string {
  return id.replace(/^run-/, "");
}

export function pct(n: number | undefined): string {
  return n === undefined ? "-" : `${n.toFixed(0)}%`;
}

export function reasoningLabel(source: string | undefined | null): string {
  if (!source) return "";
  if (source === "deterministic-demo") return "Deterministic demo responder";
  if (source === "rule-based-fallback") return "Rule-based fallback (LLM failed)";
  if (source.startsWith("llm:")) return `Live LLM ${source.slice(4)}`;
  return source;
}
