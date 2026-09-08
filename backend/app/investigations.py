"""Durable Phase 2 report service with idempotent investigation starts."""

from __future__ import annotations

from pathlib import Path

from .agents.graph import create_rca_graph
from .investigation_store import JsonInvestigationStore
from .rag.embeddings import EmbeddingProvider
from .schemas import Incident, InvestigationReport


class InvestigationService:
    def __init__(self, runbook_directory: Path, store_path: Path, embeddings: EmbeddingProvider | None = None):
        self.graph = create_rca_graph(runbook_directory, embeddings)
        self.store = JsonInvestigationStore(store_path)

    def investigate(self, incident: Incident) -> InvestigationReport:
        existing = self.store.get(incident.incident_id)
        if existing and existing.status in {"complete", "inconclusive"}:
            return existing
        report = self.graph.invoke({"incident": incident})["report"]
        self.store.save(report)
        return report

    def get(self, incident_id: str) -> InvestigationReport | None:
        return self.store.get(incident_id)
