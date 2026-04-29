"""Tests for scripts/check_local_only_workflows.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "check_local_only_workflows.py"
)
SPEC = importlib.util.spec_from_file_location("check_local_only_workflows", SCRIPT_PATH)
assert SPEC is not None
check_local_only_workflows = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(check_local_only_workflows)
main = check_local_only_workflows.main


def test_main_missing_workflow_dir(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exit 0 when the repository has no workflow directory."""
    monkeypatch.chdir(tmp_path)

    exit_code = main()

    assert exit_code == 0
    assert capsys.readouterr().out == ""


def test_main_no_violations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exit 0 when no banned tokens are found."""
    monkeypatch.chdir(tmp_path)
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "ci.yml").write_text(
        "jobs:\n  test:\n    runs-on: d-sorg-fleet\n",
        encoding="utf-8",
    )

    exit_code = main()

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Workflow runner routing is local-only." in captured.out


def test_main_with_violations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exit 1 when banned tokens are found."""
    monkeypatch.chdir(tmp_path)
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True)
    (workflow_dir / "ci.yml").write_text(
        "jobs:\n  test:\n    runs-on: ubuntu-latest\n",
        encoding="utf-8",
    )

    exit_code = main()

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "GitHub-hosted runner routing is forbidden." in captured.out
    assert "workflows" in captured.out
    assert "ci.yml:3" in captured.out
    assert "ubuntu-latest" in captured.out
