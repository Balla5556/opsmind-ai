"""FAISS-backed retrieval over the public-safe runbook corpus."""

from __future__ import annotations

from collections.abc import Iterable
import re

import faiss
import numpy as np

from ..schemas import IncidentContext, Runbook, RunbookMatch
from .embeddings import EmbeddingProvider


class RunbookRetriever:
    def __init__(self, runbooks: Iterable[Runbook], embeddings: EmbeddingProvider):
        self.runbooks = list(runbooks)
        if not self.runbooks:
            raise ValueError("At least one runbook is required")
        self.embeddings = embeddings
        vectors = embeddings.embed([self._document_text(runbook) for runbook in self.runbooks])
        self.index = faiss.IndexFlatIP(vectors.shape[1])
        self.index.add(np.ascontiguousarray(vectors, dtype=np.float32))

    def retrieve_runbooks(self, incident_context: IncidentContext, top_k: int = 5) -> list[RunbookMatch]:
        if top_k < 1:
            raise ValueError("top_k must be positive")
        query = self._query_text(incident_context)
        scores, indices = self.index.search(self.embeddings.embed([query]), min(top_k, len(self.runbooks)))
        results = []
        candidates = []
        for score, index in zip(scores[0], indices[0]):
            runbook = self.runbooks[int(index)]
            # A small lexical component keeps exact operational identifiers (such
            # as a DB pool signal) prominent alongside semantic similarity.
            adjusted_score = 0.5 * float(score) + 0.5 * self._metadata_score(query, runbook)
            candidates.append(RunbookMatch(
                runbook_id=runbook.metadata.runbook_id,
                title=runbook.metadata.title,
                score=round(max(0.0, min(1.0, adjusted_score)), 4),
                relevant_text=runbook.content[:600],
                metadata=runbook.metadata,
            ))
        return sorted(candidates, key=lambda match: match.score, reverse=True)

    @staticmethod
    def _document_text(runbook: Runbook) -> str:
        metadata = runbook.metadata
        return " ".join((metadata.title, metadata.domain, " ".join(metadata.scenarios), " ".join(metadata.tags), runbook.content))

    @staticmethod
    def _query_text(context: IncidentContext) -> str:
        signals = " ".join(f"{name.replace('_', ' ')} {value}" for name, value in context.abnormal_signals.items())
        return f"service {context.service} observed operational signals {signals}"

    @staticmethod
    def _metadata_score(query: str, runbook: Runbook) -> float:
        def tokens(text: str) -> set[str]:
            return set(re.findall(r"[a-z]+", text.lower().replace("db", "database")))

        query_tokens = tokens(query)
        runbook_tokens = tokens(" ".join((runbook.metadata.title, runbook.metadata.domain, " ".join(runbook.metadata.tags))))
        return len(query_tokens & runbook_tokens) / max(1, len(query_tokens))
