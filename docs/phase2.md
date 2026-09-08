# OpsMind AI Phase 2

Phase 2 converts a Phase 1 incident into a safe, evidence-grounded investigation.

## Implemented slice

1. Public-safe Markdown runbooks with stable IDs and JSON metadata.
2. FAISS retrieval behind a replaceable embedding-provider interface.
3. Deterministic incident context that separates abnormal from normal signals.
4. A small LangGraph workflow: gather context, retrieve runbooks, rank hypotheses, and produce approval-gated remediation recommendations.
5. In-memory idempotent investigation reports and Phase 2 API endpoints.
6. A dashboard investigation action and evidence report panel.

## Retrieval providers

`SentenceTransformerEmbeddings` is the configured semantic provider and uses `all-MiniLM-L6-v2`. Its cache defaults to `data/model-cache/`, which is intentionally untracked. Set `OPSMIND_EMBEDDING_PROVIDER=offline` only for disconnected local demos and deterministic tests. `TokenHashEmbeddings` is not a semantic model and must not be used to claim semantic-retrieval metrics.

## Persistence

Completed reports are stored atomically in `data/investigations.json` and are available after an API restart. The file is ignored by Git because it is runtime state. The storage interface is deliberately small so a database repository can replace it in a later deployment phase.

## Controlled evaluation

Set `OPSMIND_ENABLE_EVALUATION=true` only in a non-production environment and call `POST /api/v1/evaluation/run`. The evaluation suite uses five deterministically seeded incident variations for each scenario (25 cases total), keeps labels out of retrieval and signature detection input, and reports retrieval, RCA, confidence error, latency, and confusion-matrix metrics. Current offline baseline: Recall@1 `0.88`, Recall@3 `1.00`, MRR `0.94`, RCA Top-1/Top-3 accuracy `1.00`, mean absolute confidence error `0.18`. These are a small synthetic baseline, not a production-performance claim.

## LLM hypothesis provider

Set `OPSMIND_LLM_ENABLED=true` and provide `OPENAI_API_KEY` in a local `.env` file to enable OpenAI-backed hypothesis generation. The provider uses the Responses API with strict JSON-schema output, `store=false`, a bounded timeout, retrieved-runbook citations, and evidence validation. If the key is absent, the API fails, or the response is invalid, OpsMind automatically uses its deterministic measured-signal fallback; Phase 1 detection remains unaffected. `OPSMIND_LLM_MODEL` defaults to `gpt-5.6-terra` and is configurable.

## API

- `POST /api/v1/incidents/{incident_id}/investigate` starts (or returns) an idempotent investigation.
- `GET /api/v1/incidents/{incident_id}/investigation` returns the structured report.
- `GET /api/v1/incidents/{incident_id}/runbooks` returns retrieved runbooks.
- `GET /api/v1/incidents/{incident_id}/hypotheses` returns ranked hypotheses.

All remediation items require human approval. No infrastructure action is executed.

## Phase 2 completion boundary

The implementation is complete for the synthetic/public-safe Phase 2 scope: runbooks, retrieval, context building, LangGraph orchestration, structured reports/traces, LLM integration with fallback, API, dashboard, evaluation, tests, CI, and documentation. A live LLM run requires a user-provided local API key and is intentionally not executed by default.

Later production phases include a database-backed incident store, authentication, real Prometheus/OpenTelemetry ingestion, and human-approved remediation execution.
