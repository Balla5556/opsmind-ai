"""Generate repeatable retrieval and RCA metrics over held-out incident variations."""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from time import perf_counter

from ..agents.graph import create_rca_graph
from ..engine import IncidentEngine
from ..incidents.context_builder import build_incident_context
from ..rag.embeddings import TokenHashEmbeddings
from ..rag.loader import load_runbooks
from ..rag.retriever import RunbookRetriever
from ..telemetry import TelemetryGenerator


GROUND_TRUTH = {
    "db_pool_exhaustion": ("RB-DB-001", "database_connection_pool_exhaustion"),
    "cpu_saturation": ("RB-INF-001", "cpu_saturation"),
    "traffic_spike": ("RB-SVC-001", "traffic_overload"),
    "memory_leak": ("RB-SVC-002", "memory_leak"),
    "latency_degradation": ("RB-NET-001", "api_latency_degradation"),
}
EVALUATION_SEEDS = (20260908, 20260909, 20260910, 20260911, 20260912)


def run_evaluation(runbook_directory: Path) -> dict:
    """Use labels only for scoring; retrieval and RCA see measurements only."""
    embeddings = TokenHashEmbeddings()
    retriever = RunbookRetriever(load_runbooks(runbook_directory), embeddings)
    graph = create_rca_graph(runbook_directory, embeddings)
    retrieval_ranks: list[int | None] = []
    correct_top_1: list[bool] = []
    correct_top_3: list[bool] = []
    confidence_errors: list[float] = []
    latencies_ms: list[float] = []
    confusion = Counter()
    per_scenario: dict[str, dict] = {}

    for scenario, (expected_runbook, expected_root_cause) in GROUND_TRUTH.items():
        scenario_ranks: list[int | None] = []
        scenario_correct: list[bool] = []
        for seed in EVALUATION_SEEDS:
            points = TelemetryGenerator(seed=seed).generate(90, scenario)
            incident = IncidentEngine().analyze(points)[-1]
            matches = retriever.retrieve_runbooks(build_incident_context(incident))
            rank = next((position + 1 for position, match in enumerate(matches) if match.runbook_id == expected_runbook), None)
            started = perf_counter()
            report = graph.invoke({"incident": incident})["report"]
            latencies_ms.append((perf_counter() - started) * 1000)
            predictions = [item.prediction for item in report.hypotheses]
            prediction = report.root_cause.prediction if report.root_cause else "inconclusive"
            is_correct = prediction == expected_root_cause
            retrieval_ranks.append(rank)
            scenario_ranks.append(rank)
            correct_top_1.append(is_correct)
            scenario_correct.append(is_correct)
            correct_top_3.append(expected_root_cause in predictions[:3])
            confidence_errors.append(abs((report.root_cause.confidence_signal if report.root_cause else 0) - float(is_correct)))
            confusion[(expected_root_cause, prediction)] += 1
        per_scenario[scenario] = {
            "expected_runbook": expected_runbook,
            "expected_root_cause": expected_root_cause,
            "sample_size": len(EVALUATION_SEEDS),
            "retrieval_recall_at_3": round(sum(rank is not None and rank <= 3 for rank in scenario_ranks) / len(scenario_ranks), 4),
            "rca_top_1_accuracy": round(sum(scenario_correct) / len(scenario_correct), 4),
        }

    total = len(retrieval_ranks)
    found_ranks = [rank for rank in retrieval_ranks if rank is not None]
    return {
        "evaluation_mode": "offline_deterministic",
        "sample_size": total,
        "seed_count_per_scenario": len(EVALUATION_SEEDS),
        "retrieval": {
            "recall_at_1": round(sum(rank == 1 for rank in retrieval_ranks) / total, 4),
            "recall_at_3": round(sum(rank is not None and rank <= 3 for rank in retrieval_ranks) / total, 4),
            "mrr": round(sum(1 / rank for rank in found_ranks) / total, 4),
        },
        "rca": {
            "top_1_accuracy": round(sum(correct_top_1) / total, 4),
            "top_3_accuracy": round(sum(correct_top_3) / total, 4),
            "mean_absolute_confidence_error": round(sum(confidence_errors) / total, 4),
            "confusion_matrix": {f"{expected} -> {predicted}": count for (expected, predicted), count in sorted(confusion.items())},
        },
        "system": {"investigation_latency_ms_p50": round(_percentile(latencies_ms, .5), 2), "investigation_latency_ms_p95": round(_percentile(latencies_ms, .95), 2)},
        "per_scenario": per_scenario,
    }


def _percentile(values: list[float], percentile: float) -> float:
    ordered = sorted(values)
    index = round((len(ordered) - 1) * percentile)
    return ordered[index]
