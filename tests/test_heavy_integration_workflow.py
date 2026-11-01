"""The weekly heavy suite must not fail when no live tests are selected (#504)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.unit

WORKFLOW = (
    Path(__file__).resolve().parents[1]
    / ".github"
    / "workflows"
    / "heavy-integration-tests.yml"
)
STEP_NAME = "Run heavy live simulations"


def _heavy_run_script() -> str:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["heavy-tests"]["steps"]
    return next(s["run"] for s in steps if s.get("name") == STEP_NAME)


def test_marker_subset_does_not_apply_the_global_coverage_gate() -> None:
    # The repo-wide fail_under=60 applied to an empty live_simulation run read 27 %.
    assert "--cov" not in _heavy_run_script()


def test_no_tests_selected_exit_code_is_not_a_failure() -> None:
    script = _heavy_run_script()
    assert 'pytest -v -m "live_simulation"' in script
    assert '"$rc" -eq 5' in script
    assert "exit $rc" in script
