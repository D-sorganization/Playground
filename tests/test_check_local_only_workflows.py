"""Tests for scripts/check_local_only_workflows.py."""

from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
import yaml

SCRIPT_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "check_local_only_workflows.py"
)
CI_STANDARD_PATH = (
    Path(__file__).resolve().parents[1] / ".github" / "workflows" / "ci-standard.yml"
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


def _write_workflow(tmp_path: Path, body: str) -> None:
    workflow_dir = tmp_path / ".github" / "workflows"
    workflow_dir.mkdir(parents=True, exist_ok=True)
    (workflow_dir / "ci.yml").write_text(body, encoding="utf-8")


FLEET_WORKFLOW = "jobs:\n  test:\n    runs-on: d-sorg-fleet\n"
HOSTED_WORKFLOW = "jobs:\n  test:\n    runs-on: ubuntu-latest\n"


def test_main_no_violations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exit 0 when no banned tokens are found."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("REPO_VISIBILITY", "private")
    _write_workflow(tmp_path, FLEET_WORKFLOW)

    exit_code = main()

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "Workflow runner routing is local-only." in captured.out


def test_main_with_violations(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Exit 1 when banned tokens are found on a non-public repository."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("REPO_VISIBILITY", "private")
    _write_workflow(tmp_path, HOSTED_WORKFLOW)

    exit_code = main()

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "GitHub-hosted runner routing is forbidden." in captured.out
    assert "workflows" in captured.out
    assert "ci.yml:3" in captured.out
    assert "ubuntu-latest" in captured.out


def test_unknown_visibility_still_enforces(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Fail closed: an unreadable visibility must not permit hosted routing.

    A false failure costs a re-run; a false pass costs a billed month.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("REPO_VISIBILITY", raising=False)
    _write_workflow(tmp_path, HOSTED_WORKFLOW)

    assert main() == 1


def test_public_repo_permits_hosted_runners(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Hosted runners are free and unmetered on a public repo, so allow them."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("REPO_VISIBILITY", "public")
    _write_workflow(tmp_path, HOSTED_WORKFLOW)

    exit_code = main()

    assert exit_code == 0
    assert "hosted runners permitted" in capsys.readouterr().out


def test_public_repo_warns_on_fleet_pin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """A fleet pin on a public repo is a fork-PR exposure, but not a hard failure.

    Warning rather than failing is what lets a repo migrate incrementally.
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("REPO_VISIBILITY", "public")
    _write_workflow(tmp_path, FLEET_WORKFLOW)

    exit_code = main()

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "::warning::" in captured.out
    assert "d-sorg-fleet" in captured.out


def test_ci_standard_local_runner_guard_and_optional_job_inputs() -> None:
    """CI workflow keeps the runner guard local and skips absent optional projects."""
    workflow = yaml.safe_load(CI_STANDARD_PATH.read_text(encoding="utf-8"))
    jobs = workflow["jobs"]

    assert jobs["local-only-workflows"]["needs"] == "pick-runner"
    assert (
        jobs["local-only-workflows"]["runs-on"]
        == "${{ needs.pick-runner.outputs.runner }}"
    )
    javascript_steps = jobs["javascript-tests"]["steps"]
    assert (
        javascript_steps[1]["if"]
        == "${{ hashFiles('javascript/package-lock.json') != '' }}"
    )
    assert (
        javascript_steps[3]["if"]
        == "${{ hashFiles('javascript/package-lock.json') == '' }}"
    )

    arduino_steps = jobs["arduino-build"]["steps"]
    assert arduino_steps[1]["if"] == "${{ hashFiles('arduino/platformio.ini') != '' }}"
    assert arduino_steps[4]["if"] == "${{ hashFiles('arduino/platformio.ini') == '' }}"
