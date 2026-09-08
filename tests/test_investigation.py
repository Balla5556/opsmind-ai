from pathlib import Path

from backend.app.agents.graph import create_rca_graph
from backend.app.engine import IncidentEngine
from backend.app.investigations import InvestigationService
from backend.app.rag.embeddings import TokenHashEmbeddings
from backend.app.schemas import RootCauseHypothesis
from backend.app.telemetry import TelemetryGenerator


def test_db_pool_investigation_is_grounded_in_its_runbook():
    points = TelemetryGenerator().generate(90, "db_pool_exhaustion")
    incident = IncidentEngine().analyze(points)[-1]
    report = create_rca_graph(Path(__file__).parents[1] / "data" / "runbooks", TokenHashEmbeddings()).invoke({"incident": incident})["report"]

    assert report.status == "complete"
    assert report.root_cause is not None
    assert report.root_cause.prediction == "database_connection_pool_exhaustion"
    assert report.root_cause.runbook_ids == ["RB-DB-001"]
    assert report.recommended_actions[0].requires_human_approval


def test_completed_report_survives_service_recreation(tmp_path):
    incident = IncidentEngine().analyze(TelemetryGenerator().generate(90, "db_pool_exhaustion"))[-1]
    runbooks = Path(__file__).parents[1] / "data" / "runbooks"
    first = InvestigationService(runbooks, tmp_path / "reports.json", TokenHashEmbeddings()).investigate(incident)
    recovered = InvestigationService(runbooks, tmp_path / "reports.json", TokenHashEmbeddings()).get(incident.incident_id)

    assert recovered is not None
    assert recovered.created_at == first.created_at


class _GroundedProvider:
    name = "test-llm"
    model = "test-model"

    def generate(self, context, runbooks):
        return [RootCauseHypothesis(
            prediction="database_connection_pool_exhaustion", confidence_signal=.88,
            supporting_evidence=["db connection utilization measured 97.0"],
            contradicting_evidence=[], runbook_ids=["RB-DB-001"],
        )]


class _FailingProvider:
    name = "test-llm"
    model = "test-model"

    def generate(self, context, runbooks):
        raise RuntimeError("simulated provider outage")


def test_llm_hypotheses_are_reported_when_the_provider_succeeds():
    incident = IncidentEngine().analyze(TelemetryGenerator().generate(90, "db_pool_exhaustion"))[-1]
    report = create_rca_graph(Path(__file__).parents[1] / "data" / "runbooks", TokenHashEmbeddings(), _GroundedProvider()).invoke({"incident": incident})["report"]

    assert report.reasoning_provider == "test-llm"
    assert report.reasoning_model == "test-model"
    assert not report.used_fallback
    assert report.root_cause.prediction == "database_connection_pool_exhaustion"


def test_provider_failure_uses_deterministic_fallback():
    incident = IncidentEngine().analyze(TelemetryGenerator().generate(90, "db_pool_exhaustion"))[-1]
    report = create_rca_graph(Path(__file__).parents[1] / "data" / "runbooks", TokenHashEmbeddings(), _FailingProvider()).invoke({"incident": incident})["report"]

    assert report.used_fallback
    assert report.root_cause.prediction == "database_connection_pool_exhaustion"
