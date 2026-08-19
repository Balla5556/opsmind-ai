from uuid import uuid5, NAMESPACE_URL
from .anomaly import AnomalyDetector, FEATURES
from .schemas import Incident, TelemetryPoint


class IncidentEngine:
    def __init__(self):
        self.detector = AnomalyDetector()

    def analyze(self, points: list[TelemetryPoint]) -> list[Incident]:
        baseline = [p for p in points if p.scenario == "baseline"]
        self.detector.fit(baseline or points[:max(20, len(points)//3)])
        scores = self.detector.score(points)
        incidents = []
        for point, score in zip(points, scores):
            if score < .62: continue
            snapshot = {f: round(float(getattr(point, f)), 2) for f in FEATURES}
            signal = max(snapshot, key=lambda f: self._pressure(f, snapshot[f]))
            incident_id = "INC-" + str(uuid5(NAMESPACE_URL, f"{point.service}:{point.timestamp.isoformat()}"))[:8].upper()
            severity = self.detector.severity(score)
            incidents.append(Incident(incident_id=incident_id, service=point.service, detected_at=point.timestamp,
                started_at=point.timestamp, primary_signal=signal.replace("_", " ").title(), anomaly_score=score,
                severity=severity, supporting_metrics=snapshot, scenario=point.scenario,
                summary=f"{severity.title()} anomaly: {point.scenario.replace('_', ' ')} affecting {point.service}."))
        return incidents

    @staticmethod
    def _pressure(name: str, value: float) -> float:
        targets = {"cpu_percent": 85, "memory_percent": 85, "api_latency_ms": 800, "request_volume": 1300, "http_error_rate": 7, "db_connection_utilization": 85, "network_traffic_mbps": 200, "disk_utilization": 85}
        return value / targets[name]
