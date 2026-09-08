"""Atomic JSON persistence for Phase 2 investigations.

This local store is intentionally simple and replaceable; it keeps reports durable
for the Docker/demo deployment without introducing a database dependency.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from threading import Lock

from .schemas import InvestigationReport


class JsonInvestigationStore:
    def __init__(self, path: Path):
        self.path = path
        self.lock = Lock()

    def get(self, incident_id: str) -> InvestigationReport | None:
        with self.lock:
            payload = self._read()
        item = payload.get(incident_id)
        return InvestigationReport.model_validate(item) if item else None

    def save(self, report: InvestigationReport) -> None:
        with self.lock:
            payload = self._read()
            payload[report.incident_id] = report.model_dump(mode="json")
            self.path.parent.mkdir(parents=True, exist_ok=True)
            temporary = self.path.with_suffix(".tmp")
            temporary.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
            os.replace(temporary, self.path)

    def _read(self) -> dict[str, dict]:
        if not self.path.exists():
            return {}
        try:
            loaded = json.loads(self.path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Investigation store is invalid JSON: {self.path}") from exc
        if not isinstance(loaded, dict):
            raise RuntimeError(f"Investigation store must contain an object: {self.path}")
        return loaded
