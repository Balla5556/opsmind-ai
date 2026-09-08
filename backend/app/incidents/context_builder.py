"""Build compact, deterministic investigation context from a Phase 1 incident."""

from __future__ import annotations

from ..schemas import Incident, IncidentContext


NORMAL_THRESHOLDS = {
    "cpu_percent": 85,
    "memory_percent": 85,
    "api_latency_ms": 800,
    "request_volume": 1300,
    "http_error_rate": 7,
    "db_connection_utilization": 85,
    "network_traffic_mbps": 200,
    "disk_utilization": 85,
}


def build_incident_context(incident: Incident) -> IncidentContext:
    abnormal = {
        name: value for name, value in incident.supporting_metrics.items()
        if value >= NORMAL_THRESHOLDS[name]
    }
    normal = {
        name: value for name, value in incident.supporting_metrics.items()
        if name not in abnormal
    }
    return IncidentContext(
        incident_id=incident.incident_id,
        service=incident.service,
        severity=incident.severity,
        scenario=incident.scenario,
        summary=incident.summary,
        abnormal_signals=abnormal,
        normal_signals=normal,
        observed_at=incident.detected_at,
    )
