from datetime import datetime
from typing import Literal
from pydantic import BaseModel, Field

Severity = Literal["critical", "high", "medium", "low"]


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
