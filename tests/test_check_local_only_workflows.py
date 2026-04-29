"""Tests for scripts/check_local_only_workflows.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from scripts.check_local_only_workflows import changed_workflow_lines, main


def test_changed_workflow_lines_git_failure() -> None:
    """Return empty list when git diff fails."""
    with patch(
        "scripts.check_local_only_workflows.subprocess.run",
        return_value=MagicMock(returncode=1),
    ):
        result = changed_workflow_lines()
    assert result == []


def test_changed_workflow_lines_parses_diff() -> None:
    """Parse git diff output into changed lines."""
    diff_output = (
        "--- a/.github/workflows/ci.yml\n"
        "+++ b/.github/workflows/ci.yml\n"
        "@@ -10,5 +10,6 @@\n"
        "     runs-on: ubuntu-latest\n"
        "+    runs-on: self-hosted\n"
        "     steps:\n"
    )
    mock_result = MagicMock(returncode=0, stdout=diff_output)
    with patch(
        "scripts.check_local_only_workflows.subprocess.run",
        return_value=mock_result,
    ):
        result = changed_workflow_lines()
    assert len(result) == 1
    path, line_no, line = result[0]
    assert path == ".github/workflows/ci.yml"
    assert line_no == 11
    assert line == "    runs-on: self-hosted"


def test_main_no_violations(capsys: pytest.CaptureFixture[str]) -> None:
    """Exit 0 when no banned tokens are found."""
    with patch(
        "scripts.check_local_only_workflows.changed_workflow_lines",
        return_value=[],
    ):
        exit_code = main()
    assert exit_code == 0
    captured = capsys.readouterr()
    assert "No new GitHub-hosted runner routing was added." in captured.out


def test_main_with_violations(capsys: pytest.CaptureFixture[str]) -> None:
    """Exit 1 when banned tokens are found."""
    with patch(
        "scripts.check_local_only_workflows.changed_workflow_lines",
        return_value=[
            (".github/workflows/ci.yml", 12, "    runs-on: ubuntu-latest"),
        ],
    ):
        exit_code = main()
    assert exit_code == 1
    captured = capsys.readouterr()
    assert "New GitHub-hosted runner routing is forbidden." in captured.out
    assert "ubuntu-latest" in captured.out
