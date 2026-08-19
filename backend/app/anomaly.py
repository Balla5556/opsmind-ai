import numpy as np
from sklearn.ensemble import IsolationForest
from .schemas import TelemetryPoint

FEATURES = ("cpu_percent", "memory_percent", "api_latency_ms", "request_volume", "http_error_rate", "db_connection_utilization", "network_traffic_mbps", "disk_utilization")


class AnomalyDetector:
    def __init__(self):
        self.model = IsolationForest(contamination=0.12, n_estimators=150, random_state=42)
        self.fitted = False

    def feature_matrix(self, points: list[TelemetryPoint]) -> np.ndarray:
        raw = np.array([[getattr(p, name) for name in FEATURES] for p in points], dtype=float)
        # Derived operational features make correlated degradation easier to isolate.
        latency_pressure = raw[:, 2] * (1 + raw[:, 4] / 100)
        capacity_pressure = (raw[:, 0] + raw[:, 1] + raw[:, 5]) / 3
        traffic_intensity = raw[:, 3] / np.maximum(raw[:, 6], 1)
        return np.column_stack([raw, latency_pressure, capacity_pressure, traffic_intensity])

    def fit(self, baseline: list[TelemetryPoint]) -> None:
        self.model.fit(self.feature_matrix(baseline))
        self.fitted = True

    def score(self, points: list[TelemetryPoint]) -> list[float]:
        if not self.fitted: raise RuntimeError("Detector must be fitted before scoring")
        # Convert the Isolation Forest's signed score to intuitive 0..1 risk.
        raw = -self.model.score_samples(self.feature_matrix(points))
        low, high = raw.min(), raw.max()
        return [round(float((value - low) / (high - low + 1e-9)), 3) for value in raw]

    @staticmethod
    def severity(score: float) -> str:
        return "critical" if score >= .82 else "high" if score >= .62 else "medium" if score >= .42 else "low"
