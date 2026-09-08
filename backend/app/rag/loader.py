"""Load public-safe Markdown runbooks with deterministic JSON front matter."""

from __future__ import annotations

import json
from pathlib import Path

from ..schemas import Runbook, RunbookMetadata


class RunbookLoadError(ValueError):
    """Raised when a runbook cannot meet the knowledge-base contract."""


def load_runbooks(runbook_directory: Path) -> list[Runbook]:
    """Load every Markdown runbook, rejecting malformed metadata early."""
    if not runbook_directory.is_dir():
        raise RunbookLoadError(f"Runbook directory does not exist: {runbook_directory}")

    runbooks = [_load_runbook(path) for path in sorted(runbook_directory.rglob("*.md"))]
    ids = [runbook.metadata.runbook_id for runbook in runbooks]
    if len(ids) != len(set(ids)):
        raise RunbookLoadError("Runbook IDs must be unique")
    return runbooks


def _load_runbook(path: Path) -> Runbook:
    raw = path.read_text(encoding="utf-8").strip()
    if not raw.startswith("---\n"):
        raise RunbookLoadError(f"Missing metadata delimiter in {path}")
    try:
        _, front_matter, content = raw.split("---\n", 2)
        metadata = RunbookMetadata.model_validate(json.loads(front_matter))
    except (ValueError, json.JSONDecodeError) as exc:
        raise RunbookLoadError(f"Invalid metadata in {path}") from exc
    if not content.strip():
        raise RunbookLoadError(f"Runbook body cannot be empty: {path}")
    return Runbook(metadata=metadata, content=content.strip(), source_path=str(path))
