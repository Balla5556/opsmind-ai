"""Small LangGraph RCA workflow with deterministic, testable nodes.

The Phase 2 MVP deliberately uses evidence rules for hypothesis generation. An LLM
provider can later replace that node without changing the API/report contract.
"""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from ..incidents.context_builder import build_incident_context
from ..rag.embeddings import EmbeddingProvider, configured_embeddings
from ..rag.loader import load_runbooks
from ..rag.retriever import RunbookRetriever
from ..schemas import Incident, InvestigationReport, InvestigationStep, RemediationAction, RootCauseHypothesis, RunbookMatch
from .hypothesis_provider import HypothesisProvider, configured_hypothesis_provider


class RCAState(TypedDict, total=False):
    incident: Incident
    report: InvestigationReport
    runbooks: list[RunbookMatch]
    hypotheses: list[RootCauseHypothesis]
    trace: list[InvestigationStep]


SIGNATURE_DETAILS = {
    "database_connection_pool_exhaustion": ("RB-DB-001", "DB connection utilization reached {db_connection_utilization}%"),
    "cpu_saturation": ("RB-INF-001", "CPU utilization reached {cpu_percent}%"),
    "traffic_overload": ("RB-SVC-001", "Request volume increased to {request_volume}/min"),
    "memory_leak": ("RB-SVC-002", "Memory utilization reached {memory_percent}%"),
    "api_latency_degradation": ("RB-NET-001", "API latency increased to {api_latency_ms} ms"),
}


def create_rca_graph(runbook_directory: Path, embeddings: EmbeddingProvider | None = None, hypothesis_provider: HypothesisProvider | None = None):
    retriever = RunbookRetriever(load_runbooks(runbook_directory), embeddings or configured_embeddings())
    provider = hypothesis_provider if hypothesis_provider is not None else configured_hypothesis_provider()
    graph = StateGraph(RCAState)

    def gather_context(state: RCAState):
        incident = state["incident"]
        context = build_incident_context(incident)
        trace = [InvestigationStep(name="gather_context", status="complete", detail=f"Captured {len(context.abnormal_signals)} abnormal and {len(context.normal_signals)} normal signals.", recorded_at=datetime.now(timezone.utc))]
        return {"trace": trace, "report": InvestigationReport(
            incident_id=incident.incident_id, service=incident.service, severity=incident.severity,
            status="retrieving_knowledge", supporting_evidence=_metric_evidence(context.abnormal_signals),
            created_at=datetime.now(timezone.utc),
        )}

    def retrieve_knowledge(state: RCAState):
        matches = retriever.retrieve_runbooks(build_incident_context(state["incident"]))
        return {"runbooks": matches, "trace": [*state["trace"], InvestigationStep(name="retrieve_knowledge", status="complete", detail=f"Retrieved {len(matches)} runbooks using {retriever.embeddings.name}.", recorded_at=datetime.now(timezone.utc))]}

    def generate_hypotheses(state: RCAState):
        incident = state["incident"]
        context = build_incident_context(incident)
        if provider:
            try:
                hypotheses = provider.generate(context, state["runbooks"])
                return {"hypotheses": hypotheses, "report": state["report"].model_copy(update={"reasoning_provider": provider.name, "reasoning_model": provider.model}), "trace": [*state["trace"], InvestigationStep(name="generate_hypotheses", status="complete", detail=f"Generated {len(hypotheses)} evidence-validated hypotheses with {provider.name}.", recorded_at=datetime.now(timezone.utc))]}
            except Exception:
                # A provider failure must never prevent an incident from being
                # investigated; use the measured-signature fallback instead.
                report = state["report"].model_copy(update={"reasoning_provider": provider.name, "reasoning_model": provider.model, "used_fallback": True})
            else:
                report = state["report"]
        else:
            report = state["report"]
        metrics = incident.supporting_metrics
        primary = _detect_signature(metrics)
        runbook_id, template = SIGNATURE_DETAILS.get(primary, ("", "No deterministic root-cause signature matched"))
        evidence = [template.format(**metrics)] if runbook_id else []
        if metrics.get("api_latency_ms", 0) >= 800:
            evidence.append(f"API latency increased to {metrics['api_latency_ms']} ms")
        if metrics.get("http_error_rate", 0) >= 7:
            evidence.append(f"HTTP error rate increased to {metrics['http_error_rate']}%")
        top = RootCauseHypothesis(prediction=primary, confidence_signal=0.82 if runbook_id else 0.35,
                                  supporting_evidence=list(dict.fromkeys(evidence)), runbook_ids=[runbook_id] if runbook_id else [])
        alternatives = [
            RootCauseHypothesis(prediction="traffic_overload", confidence_signal=0.35,
                                supporting_evidence=[f"Request volume is {metrics['request_volume']}/min"],
                                contradicting_evidence=[f"CPU is only {metrics['cpu_percent']}%"]),
            RootCauseHypothesis(prediction="cpu_saturation", confidence_signal=0.18,
                                contradicting_evidence=[f"CPU is only {metrics['cpu_percent']}%"]),
        ]
        return {"hypotheses": [top, *[item for item in alternatives if item.prediction != primary]], "report": report, "trace": [*state["trace"], InvestigationStep(name="generate_hypotheses", status="fallback" if provider else "complete", detail="Ranked deterministic hypotheses from observed metric signatures.", recorded_at=datetime.now(timezone.utc))]}

    def generate_report(state: RCAState):
        report = state["report"]
        hypotheses = sorted(state["hypotheses"], key=lambda item: item.confidence_signal, reverse=True)
        root_cause = hypotheses[0]
        report.status = "complete" if root_cause.confidence_signal >= 0.65 else "inconclusive"
        report.root_cause = root_cause
        report.hypotheses = hypotheses
        report.runbooks = state["runbooks"]
        report.recommended_actions = _remediation(root_cause)
        report.completed_at = datetime.now(timezone.utc)
        report.investigation_trace = [*state["trace"], InvestigationStep(name="generate_report", status="complete", detail="Generated recommendation-only incident report.", recorded_at=datetime.now(timezone.utc))]
        return {"report": report}

    graph.add_node("gather_context", gather_context)
    graph.add_node("retrieve_knowledge", retrieve_knowledge)
    graph.add_node("generate_hypotheses", generate_hypotheses)
    graph.add_node("generate_report", generate_report)
    graph.add_edge(START, "gather_context")
    graph.add_edge("gather_context", "retrieve_knowledge")
    graph.add_edge("retrieve_knowledge", "generate_hypotheses")
    graph.add_edge("generate_hypotheses", "generate_report")
    graph.add_edge("generate_report", END)
    return graph.compile()


def _metric_evidence(metrics: dict[str, float]) -> list[str]:
    return [f"{name.replace('_', ' ')} measured {value}" for name, value in metrics.items()]


def _detect_signature(metrics: dict[str, float]) -> str:
    """Classify only from observed measurements, never from the injected label."""
    if metrics.get("db_connection_utilization", 0) >= 95:
        return "database_connection_pool_exhaustion"
    if metrics.get("cpu_percent", 0) >= 90:
        return "cpu_saturation"
    if metrics.get("memory_percent", 0) >= 85:
        return "memory_leak"
    if metrics.get("request_volume", 0) >= 1300:
        return "traffic_overload"
    if metrics.get("api_latency_ms", 0) >= 1000:
        return "api_latency_degradation"
    return "inconclusive"


def _remediation(root_cause: RootCauseHypothesis) -> list[RemediationAction]:
    action = {
        "database_connection_pool_exhaustion": "Inspect active connections and long-running queries.",
        "cpu_saturation": "Inspect the busiest request paths and affected instances.",
        "traffic_overload": "Validate traffic origin and apply approved traffic shaping if necessary.",
        "memory_leak": "Inspect memory growth by instance and deployment version.",
        "api_latency_degradation": "Inspect the affected endpoint and downstream dependency latency.",
    }.get(root_cause.prediction, "Collect additional approved telemetry before acting.")
    return [
        RemediationAction(urgency="immediate", action=action, source_runbook_id=root_cause.runbook_ids[0] if root_cause.runbook_ids else None),
        RemediationAction(urgency="preventative", action="Review the cited runbook and add a targeted alert or regression test.", source_runbook_id=root_cause.runbook_ids[0] if root_cause.runbook_ids else None),
    ]
