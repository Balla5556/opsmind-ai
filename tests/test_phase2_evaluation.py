from pathlib import Path

from backend.app.evaluation.report import run_evaluation


def test_evaluation_reports_computed_metrics_for_every_injected_scenario():
    report = run_evaluation(Path(__file__).parents[1] / "data" / "runbooks")

    assert report["sample_size"] == 25
    assert set(report["per_scenario"]) == {"db_pool_exhaustion", "cpu_saturation", "traffic_spike", "memory_leak", "latency_degradation"}
    assert 0 <= report["retrieval"]["mrr"] <= 1
    assert 0 <= report["rca"]["top_1_accuracy"] <= 1
    assert 0 <= report["rca"]["mean_absolute_confidence_error"] <= 1
    assert report["system"]["investigation_latency_ms_p95"] >= report["system"]["investigation_latency_ms_p50"]
