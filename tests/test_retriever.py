from datetime import datetime, timezone
from pathlib import Path

from backend.app.rag.embeddings import TokenHashEmbeddings
from backend.app.rag.loader import load_runbooks
from backend.app.rag.retriever import RunbookRetriever
from backend.app.schemas import IncidentContext


def test_db_connection_incident_returns_the_db_runbook_first():
    runbooks = load_runbooks(Path(__file__).parents[1] / "data" / "runbooks")
    retriever = RunbookRetriever(runbooks, TokenHashEmbeddings())
    context = IncidentContext(
        incident_id="INC-TEST", service="payment-api", severity="critical", scenario="db_pool_exhaustion",
        summary="Critical database connection pool exhaustion affecting payment-api.",
        abnormal_signals={"db_connection_utilization": 97, "api_latency_ms": 1320, "http_error_rate": 13},
        normal_signals={"cpu_percent": 72}, observed_at=datetime.now(timezone.utc),
    )

    matches = retriever.retrieve_runbooks(context)

    assert matches[0].runbook_id == "RB-DB-001"
    assert all(0 <= match.score <= 1 for match in matches)
