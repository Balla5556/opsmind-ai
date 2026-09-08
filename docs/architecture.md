# OpsMind AI Architecture

## Phase 2 flow

```text
Synthetic telemetry -> Isolation Forest -> Phase 1 incident
                                         |
                                         v
                               Context builder (typed signals)
                                         |
                                         v
                    Hybrid runbook retrieval (semantic + exact signal match)
                                         |
                                         v
             OpenAI structured hypotheses OR deterministic safe fallback
                                         |
                                         v
                 Evidence validation -> recommendation-only report -> dashboard
```

## Safety and resilience

- Phase 1 detection has no dependency on the RAG index or LLM provider.
- Phase 2 never invokes shell commands, cloud APIs, restarts, or database mutations.
- Recommendations carry `requires_human_approval: true`.
- Failed LLM calls and invalid structured output route to deterministic RCA.
- Investigation reports and their trace are written atomically to local runtime storage.
- Runbooks are public-safe synthetic operational documentation only.

## Replaceable boundaries

| Boundary | Current implementation | Future replacement |
| --- | --- | --- |
| Embeddings | SentenceTransformers / offline deterministic | Managed embedding API |
| Vector search | FAISS | OpenSearch, pgvector, or hosted vector DB |
| Hypothesis generation | OpenAI Responses structured outputs | Another typed LLM provider |
| Persistence | Atomic JSON runtime store | PostgreSQL or managed incident store |
| Telemetry | Synthetic generator | Prometheus or OpenTelemetry ingestion |
