from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from .engine import IncidentEngine
from .telemetry import TelemetryGenerator, SCENARIOS

app = FastAPI(title="OpsMind AI API", version="0.1.0", description="Synthetic AIOps incident intelligence MVP")
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:3000"], allow_credentials=True, allow_methods=["GET"], allow_headers=["*"])

def dataset(scenario: str = "mixed"):
    points = TelemetryGenerator().generate(scenario=scenario)
    incidents = IncidentEngine().analyze(points)
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
    _, found = dataset(scenario)
    item = next((i for i in found if i.incident_id == incident_id), None)
    if not item: raise HTTPException(404, "Incident not found")
    return item
