"""Schema-constrained LLM RCA generation with deterministic fallback support."""

from __future__ import annotations

import json
import os
from typing import Protocol

from ..schemas import HypothesisResponse, IncidentContext, RootCauseHypothesis, RunbookMatch


class HypothesisGenerationError(RuntimeError):
    pass


class HypothesisProvider(Protocol):
    name: str
    model: str | None

    def generate(self, context: IncidentContext, runbooks: list[RunbookMatch]) -> list[RootCauseHypothesis]: ...


class OpenAIHypothesisProvider:
    """Generate grounded hypotheses through the Responses API Structured Outputs."""

    name = "openai"

    def __init__(self, api_key: str | None = None, model: str | None = None, timeout_seconds: float | None = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self.model = model or os.getenv("OPSMIND_LLM_MODEL", "gpt-5.6-terra")
        self.timeout_seconds = timeout_seconds or float(os.getenv("OPSMIND_LLM_TIMEOUT_SECONDS", "20"))

    def generate(self, context: IncidentContext, runbooks: list[RunbookMatch]) -> list[RootCauseHypothesis]:
        if not self.api_key:
            raise HypothesisGenerationError("OPENAI_API_KEY is not configured")
        from openai import OpenAI

        client = OpenAI(api_key=self.api_key, timeout=self.timeout_seconds)
        response = client.responses.create(
            model=self.model,
            store=False,
            instructions=(
                "You are an operations RCA analyst. Use only the incident context and retrieved runbooks. "
                "Return 2-5 ranked hypotheses. Every hypothesis needs supporting and contradicting evidence. "
                "Cite only the supplied runbook IDs. Do not propose executable commands or autonomous remediation."
            ),
            input=json.dumps({
                "incident_context": context.model_dump(mode="json"),
                "retrieved_runbooks": [{"runbook_id": item.runbook_id, "title": item.title, "text": item.relevant_text} for item in runbooks],
            }),
            text={"format": {"type": "json_schema", "name": "rca_hypotheses", "strict": True, "schema": HypothesisResponse.model_json_schema()}},
        )
        if not response.output_text:
            raise HypothesisGenerationError("OpenAI returned no structured output")
        hypotheses = HypothesisResponse.model_validate_json(response.output_text).hypotheses
        return self._validate_grounding(hypotheses, context, runbooks)

    @staticmethod
    def _validate_grounding(hypotheses: list[RootCauseHypothesis], context: IncidentContext, runbooks: list[RunbookMatch]) -> list[RootCauseHypothesis]:
        allowed_runbooks = {item.runbook_id for item in runbooks}
        available_evidence = {f"{name.replace('_', ' ')} measured {value}" for name, value in context.abnormal_signals.items()}
        validated = []
        for hypothesis in hypotheses:
            if not hypothesis.supporting_evidence:
                continue
            if not set(hypothesis.runbook_ids).issubset(allowed_runbooks):
                continue
            # Evidence is supplied as a human-readable claim, but must mention an
            # observed metric or a cited runbook to survive validation.
            evidence_text = " ".join(hypothesis.supporting_evidence).lower()
            metric_terms = [name.replace("_", " ") for name in context.abnormal_signals]
            if not any(term in evidence_text for term in metric_terms) and not hypothesis.runbook_ids:
                continue
            validated.append(hypothesis)
        if not validated:
            raise HypothesisGenerationError("LLM hypotheses did not meet evidence-grounding requirements")
        return sorted(validated, key=lambda item: item.confidence_signal, reverse=True)


def configured_hypothesis_provider() -> HypothesisProvider | None:
    if os.getenv("OPSMIND_LLM_ENABLED", "false").lower() != "true":
        return None
    return OpenAIHypothesisProvider()
