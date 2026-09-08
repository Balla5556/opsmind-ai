from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

Severity = Literal["critical", "high", "medium", "low"]
InvestigationStatus = Literal["pending", "gathering_context", "retrieving_knowledge", "evaluating_hypotheses", "complete", "inconclusive", "failed"]


class TelemetryPoint(BaseModel):
    timestamp: datetime
    service: str
    cpu_percent: float = Field(ge=0, le=100)
    memory_percent: float = Field(ge=0, le=100)
    api_latency_ms: float = Field(ge=0)
    request_volume: float = Field(ge=0)
    http_error_rate: float = Field(ge=0, le=100)
    db_connection_utilization: float = Field(ge=0, le=100)
    network_traffic_mbps: float = Field(ge=0)
    disk_utilization: float = Field(ge=0, le=100)
    service_status: Literal["healthy", "degraded", "down"]
    scenario: str = "baseline"


class Incident(BaseModel):
    incident_id: str
    service: str
    detected_at: datetime
    started_at: datetime
    primary_signal: str
    anomaly_score: float
    severity: Severity
    supporting_metrics: dict[str, float]
    scenario: str
    summary: str


class RunbookMetadata(BaseModel):
    runbook_id: str = Field(pattern=r"^RB-[A-Z]+-\d{3}$")
    title: str
    service: str
    domain: str
    scenarios: list[str]
    tags: list[str] = Field(default_factory=list)


class Runbook(BaseModel):
    metadata: RunbookMetadata
    content: str
    source_path: str


class RunbookMatch(BaseModel):
    runbook_id: str
    title: str
    score: float = Field(ge=0, le=1)
    relevant_text: str
    metadata: RunbookMetadata


class IncidentContext(BaseModel):
    incident_id: str
    service: str
    severity: Severity
    scenario: str
    summary: str
    abnormal_signals: dict[str, float]
    normal_signals: dict[str, float]
    observed_at: datetime


class RootCauseHypothesis(BaseModel):
    prediction: str
    confidence_signal: float = Field(ge=0, le=1)
    supporting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    runbook_ids: list[str] = Field(default_factory=list)


class HypothesisResponse(BaseModel):
    hypotheses: list[RootCauseHypothesis] = Field(min_length=1, max_length=5)


class RemediationAction(BaseModel):
    urgency: Literal["immediate", "short_term", "preventative"]
    action: str
    requires_human_approval: bool = True
    source_runbook_id: str | None = None


class InvestigationStep(BaseModel):
    name: str
    status: Literal["complete", "fallback"]
    detail: str
    recorded_at: datetime


class InvestigationReport(BaseModel):
    incident_id: str
    service: str
    severity: Severity
    status: InvestigationStatus
    root_cause: RootCauseHypothesis | None = None
    hypotheses: list[RootCauseHypothesis] = Field(default_factory=list)
    supporting_evidence: list[str] = Field(default_factory=list)
    contradicting_evidence: list[str] = Field(default_factory=list)
    runbooks: list[RunbookMatch] = Field(default_factory=list)
    recommended_actions: list[RemediationAction] = Field(default_factory=list)
    created_at: datetime
    completed_at: datetime | None = None
    error: str | None = None
    reasoning_provider: str = "deterministic"
    reasoning_model: str | None = None
    used_fallback: bool = False
    investigation_trace: list[InvestigationStep] = Field(default_factory=list)
