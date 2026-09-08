import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from .engine import IncidentEngine
from .evaluation.report import run_evaluation
from .investigations import InvestigationService
from .telemetry import TelemetryGenerator, SCENARIOS

app = FastAPI(title="OpsMind AI API", version="0.1.0", description="Synthetic AIOps incident intelligence MVP")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_credentials=True, allow_methods=["GET", "POST"], allow_headers=["*"])
PROJECT_ROOT = Path(__file__).parents[2]
investigation_service = InvestigationService(PROJECT_ROOT / "data" / "runbooks", PROJECT_ROOT / "data" / "investigations.json")
known_incidents = {}

def dataset(scenario: str = "mixed"):
    points = TelemetryGenerator().generate(scenario=scenario)
    incidents = IncidentEngine().analyze(points)
    known_incidents.update({incident.incident_id: incident for incident in incidents})
    return points, incidents

@app.get("/health")
def health(): return {"status": "healthy", "service": "opsmind-api", "version": app.version}

@app.get("/telemetry")
def telemetry(scenario: str = Query("mixed"), limit: int = Query(60, ge=1, le=180)):
    if scenario != "mixed" and scenario not in SCENARIOS: raise HTTPException(400, "Unknown scenario")
    points, _ = dataset(scenario)
    return {"data": points[-limit:], "source": "synthetic"}

@app.get("/incidents")
def incidents(scenario: str = Query("mixed")):
    _, found = dataset(scenario)
    return {"data": found[-30:], "count": len(found), "source": "synthetic"}

@app.get("/incidents/{incident_id}")
def incident_detail(incident_id: str, scenario: str = Query("mixed")):
    cached = known_incidents.get(incident_id)
    if cached:
        return cached
    _, found = dataset(scenario)
    item = next((i for i in found if i.incident_id == incident_id), None)
    if not item: raise HTTPException(404, "Incident not found")
    return item


def _known_incident(incident_id: str):
    incident = known_incidents.get(incident_id)
    if incident:
        return incident
    # Preserve the Phase 1 API's on-demand data model while allowing direct API use.
    dataset("mixed")
    incident = known_incidents.get(incident_id)
    if not incident:
        raise HTTPException(404, "Incident not found. Fetch /incidents before investigating an incident.")
    return incident


@app.post("/api/v1/incidents/{incident_id}/investigate")
def investigate(incident_id: str):
    """Create or return an idempotent, recommendation-only RCA report."""
    return investigation_service.investigate(_known_incident(incident_id))


@app.get("/api/v1/incidents/{incident_id}/investigation")
def investigation(incident_id: str):
    report = investigation_service.get(incident_id)
    if not report:
        raise HTTPException(404, "No investigation exists for this incident")
    return report


@app.get("/api/v1/incidents/{incident_id}/runbooks")
def investigation_runbooks(incident_id: str):
    report = investigation_service.get(incident_id)
    if not report:
        raise HTTPException(404, "No investigation exists for this incident")
    return {"data": report.runbooks, "embedding_provider": investigation_service.graph.name if hasattr(investigation_service.graph, "name") else "configured"}


@app.get("/api/v1/incidents/{incident_id}/hypotheses")
def investigation_hypotheses(incident_id: str):
    report = investigation_service.get(incident_id)
    if not report:
        raise HTTPException(404, "No investigation exists for this incident")
    return {"data": report.hypotheses}


@app.post("/api/v1/evaluation/run")
def evaluation_run():
    if os.getenv("OPSMIND_ENABLE_EVALUATION", "false").lower() != "true":
        raise HTTPException(403, "Evaluation endpoint is disabled")
    return run_evaluation(PROJECT_ROOT / "data" / "runbooks")
