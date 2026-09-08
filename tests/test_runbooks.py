from pathlib import Path

from backend.app.rag.loader import load_runbooks


RUNBOOKS = Path(__file__).parents[1] / "data" / "runbooks"


def test_runbooks_are_loadable_and_have_unique_stable_metadata():
    runbooks = load_runbooks(RUNBOOKS)

    assert len(runbooks) >= 5
    assert {"db_pool_exhaustion", "cpu_saturation", "traffic_spike", "memory_leak", "latency_degradation"}.issubset(
        {scenario for runbook in runbooks for scenario in runbook.metadata.scenarios}
    )
    assert len({runbook.metadata.runbook_id for runbook in runbooks}) == len(runbooks)


def test_runbooks_have_required_operational_sections():
    required = ("Symptoms", "Thresholds", "Possible causes", "Investigation steps", "Safe immediate remediation", "Long-term prevention")
    for runbook in load_runbooks(RUNBOOKS):
        assert all(section in runbook.content for section in required)
