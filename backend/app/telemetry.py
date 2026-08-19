from datetime import datetime, timedelta, timezone
import math
import random
from .schemas import TelemetryPoint

SCENARIOS = ("baseline", "traffic_spike", "cpu_saturation", "db_pool_exhaustion", "memory_leak", "latency_degradation")


class TelemetryGenerator:
    """Deterministic, production-shaped telemetry with explainable failure injections."""
    def __init__(self, seed: int = 42, service: str = "payment-api"):
        self.rng = random.Random(seed)
        self.service = service

    def generate(self, points: int = 180, scenario: str = "mixed") -> list[TelemetryPoint]:
        if scenario != "mixed" and scenario not in SCENARIOS:
            raise ValueError(f"Unknown scenario: {scenario}")
        start = datetime.now(timezone.utc).replace(microsecond=0) - timedelta(minutes=points - 1)
        result = []
        for index in range(points):
            active = scenario if scenario != "mixed" else self._scenario_for(index, points)
            result.append(self._point(start + timedelta(minutes=index), index, active))
        return result

    def _scenario_for(self, index: int, points: int) -> str:
        # Five clear incident windows in a normal live-like stream.
        if index < points * .35: return "baseline"
        windows = ["traffic_spike", "cpu_saturation", "db_pool_exhaustion", "memory_leak", "latency_degradation"]
        slot = int((index - points * .35) / max(1, points * .13))
        return windows[min(slot, len(windows) - 1)] if index % 12 < 7 else "baseline"

    def _point(self, timestamp: datetime, index: int, scenario: str) -> TelemetryPoint:
        wave = math.sin(index / 9)
        n = lambda scale: self.rng.uniform(-scale, scale)
        values = dict(cpu_percent=42 + 6 * wave + n(3), memory_percent=56 + 3 * wave + n(2),
                      api_latency_ms=175 + 18 * wave + n(12), request_volume=740 + 60 * wave + n(35),
                      http_error_rate=max(.05, .35 + n(.2)), db_connection_utilization=46 + n(4),
                      network_traffic_mbps=85 + n(10), disk_utilization=38 + n(1.5))
        if scenario == "traffic_spike":
            values.update(request_volume=1850 + n(120), network_traffic_mbps=280 + n(30), cpu_percent=76 + n(5), api_latency_ms=430 + n(45), http_error_rate=3.2 + n(.8))
        elif scenario == "cpu_saturation":
            values.update(cpu_percent=94 + n(2), api_latency_ms=880 + n(90), http_error_rate=8.5 + n(1.5), memory_percent=79 + n(3))
        elif scenario == "db_pool_exhaustion":
            values.update(db_connection_utilization=97 + n(1), api_latency_ms=1320 + n(130), http_error_rate=13 + n(2), cpu_percent=72 + n(4))
        elif scenario == "memory_leak":
            values.update(memory_percent=min(99, 73 + (index % 15) * 1.7 + n(2)), api_latency_ms=680 + n(80), cpu_percent=69 + n(5), http_error_rate=5 + n(1))
        elif scenario == "latency_degradation":
            values.update(api_latency_ms=1680 + n(180), http_error_rate=10 + n(2), cpu_percent=68 + n(5), db_connection_utilization=79 + n(4))
        status = "healthy" if scenario == "baseline" else ("degraded" if scenario == "traffic_spike" else "down" if values["http_error_rate"] > 11 else "degraded")
        return TelemetryPoint(timestamp=timestamp, service=self.service, scenario=scenario, service_status=status, **{k: round(v, 2) for k,v in values.items()})
