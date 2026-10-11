"""The real workflows keep fork PR code off the self-hosted fleet (RM#1989)."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts import fork_pr_runner_guard as guard

pytestmark = pytest.mark.unit

WORKFLOWS = Path(__file__).resolve().parents[1] / ".github" / "workflows"


def test_workflows_dir_exists() -> None:
    assert WORKFLOWS.is_dir()


def test_no_workflow_runs_fork_pr_code_on_self_hosted() -> None:
    assert guard.find_violations(WORKFLOWS) == []
