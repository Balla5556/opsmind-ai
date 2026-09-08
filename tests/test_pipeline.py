from fastapi.testclient import TestClient
from backend.app.anomaly import AnomalyDetector
from backend.app.main import app
from backend.app.telemetry import TelemetryGenerator

def test_generator_covers_requested_metric_surface():
    point = TelemetryGenerator().generate(1)[0]
    assert point.cpu_percent >= 0 and point.api_latency_ms >= 0
    assert point.service_status in {"healthy", "degraded", "down"}

def test_anomaly_scores_and_severity_are_bounded():
    points = TelemetryGenerator().generate(90, "mixed")
    model = AnomalyDetector(); model.fit([p for p in points if p.scenario == "baseline"])
    scores = model.score(points)
    assert all(0 <= score <= 1 for score in scores)
    assert model.severity(max(scores)) in {"critical", "high", "medium", "low"}

def test_api_end_to_end():
    client = TestClient(app)
    assert client.get("/health").json()["status"] == "healthy"
    telemetry = client.get("/telemetry?limit=5").json()
    assert len(telemetry["data"]) == 5
    incidents = client.get("/incidents").json()["data"]
    assert incidents and client.get(f"/incidents/{incidents[0]['incident_id']}").status_code == 200


def test_investigation_api_is_idempotent_and_recommendation_only():
    client = TestClient(app)
    incident = client.get("/incidents?scenario=db_pool_exhaustion").json()["data"][-1]
    first = client.post(f"/api/v1/incidents/{incident['incident_id']}/investigate")
    second = client.post(f"/api/v1/incidents/{incident['incident_id']}/investigate")

    assert first.status_code == 200
    assert first.json()["root_cause"]["prediction"] == "database_connection_pool_exhaustion"
    assert second.json()["created_at"] == first.json()["created_at"]
    assert all(action["requires_human_approval"] for action in first.json()["recommended_actions"])
