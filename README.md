# OpsMind AI

**OpsMind AI** is a production-style, agentic AIOps and incident-intelligence platform. Phase 1 turns operational telemetry into explainable, ranked incidents using feature engineering and Isolation Forest anomaly detection.

> **Data notice:** every record in this MVP is synthetic or public-safe. No proprietary systems, customer data, credentials, or production telemetry are used.

## MVP capabilities

- Synthetic service telemetry: CPU, memory, API latency, request volume, HTTP error rate, DB connection utilization, network traffic, disk utilization, and service status.
- Injected incident patterns: traffic spike, CPU saturation, DB connection pool exhaustion, memory leak, and latency degradation.
- Feature engineering for latency/error pressure, aggregate capacity pressure, and traffic intensity.
- Isolation Forest scoring normalized to a 0–1 anomaly risk, with low/medium/high/critical severity mapping.
- Incident records with stable IDs, service/timestamps, primary signal, score, severity, scenario, and metric evidence.
- FastAPI endpoints and a recruiter-friendly Next.js dashboard.
- Automated tests and a Docker-ready API plus dashboard composition.

## Architecture

```text
Synthetic telemetry generator
      │  (8 metrics + fault scenarios)
      ▼
Feature engineering ──► Isolation Forest ──► Incident engine
                                              │
                                  FastAPI ◄───┘
                                  │               
                         Next.js operations dashboard
```

## Run locally

Requires Python 3.11+ and Node 20+.

```bash
cd opsmind-ai
python -m venv .venv
source .venv/bin/activate
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

In a second terminal:

```bash
cd opsmind-ai/frontend
npm install
npm run dev
```

Open `http://localhost:3000`; API documentation is available at `http://localhost:8000/docs`.

### API surface

| Endpoint | Purpose |
|---|---|
| `GET /health` | API health and version |
| `GET /telemetry?limit=60&scenario=mixed` | simulated telemetry window |
| `GET /incidents?scenario=mixed` | scored incidents |
| `GET /incidents/{incident_id}` | individual incident evidence |

For a focused demo, pass one of `traffic_spike`, `cpu_saturation`, `db_pool_exhaustion`, `memory_leak`, or `latency_degradation` as `scenario`.

### Tests

```bash
cd opsmind-ai
pytest -q
```

### Docker

```bash
docker compose up --build
```

## Design choices

The simulation is deterministic (`seed=42`) so demos and tests are reproducible. Isolation Forest trains on the baseline segment and detects multivariate departures; it is a solid unsupervised Phase 1 baseline rather than a claim of a fully calibrated production model. The incident engine preserves the evidence snapshot that led to each classification.

## Roadmap

**Phase 2 — Knowledge and investigation:** RAG over runbooks, incident postmortems, and service documentation; tool-using investigation agents; evidence-grounded remediation recommendations and evaluations.

**Phase 3 — ML platform:** MLflow experiment/model tracking, time-series forecasting, drift/data-quality checks, calibration, feedback labels, and model monitoring.

**Phase 4 — Production operations:** authenticated data ingestion, Prometheus/OpenTelemetry adapters, durable incident storage, CI/CD, container registry, observability, and AWS deployment (ECS/EKS, API Gateway, RDS/OpenSearch, S3, CloudWatch).

## Suggested Git history

Once this folder is moved into the repository you create, use small, reviewable commits:

1. `chore: initialize OpsMind AI service structure`
2. `feat: add synthetic telemetry scenarios and feature engineering`
3. `feat: add anomaly scoring and incident API`
4. `feat: add operations dashboard`
5. `test: cover telemetry detection and API flows`
6. `docs: add MVP architecture and roadmap`

No GitHub remote is configured or pushed by this project.
