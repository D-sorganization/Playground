"""Regression tests: the static assessment must not scan its own pattern source.

The regex patterns (``except Exception as e:``, ``time.sleep(``, ``while True``)
live in ``scripts/assessment_collectors.py``; scanning that file inflates the
counts it reports. See Playground PR #470.
"""

import sys
from pathlib import Path

import pytest

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(SCRIPTS_DIR))

from assessment_collectors import (  # noqa: E402
    _assess_error_handling,
    _assess_performance,
)
from assessment_utils import find_python_files  # noqa: E402


@pytest.fixture()
def repo_with_scanner(tmp_path, monkeypatch):
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    for name in ("assessment_collectors.py", "run_assessment.py"):
        (scripts / name).write_text(
            (SCRIPTS_DIR / name).read_text(encoding="utf-8"), encoding="utf-8"
        )
    (tmp_path / "app.py").write_text("x = 1\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    return tmp_path


def test_find_python_files_excludes_assessment_pattern_modules(
    repo_with_scanner,
):
    names = {p.name for p in find_python_files()}

    assert "app.py" in names
    assert "assessment_collectors.py" not in names
    assert "run_assessment.py" not in names


def test_collectors_report_zero_for_clean_repo(repo_with_scanner):
    files = find_python_files()

    error_findings, _ = _assess_error_handling(files)
    perf_findings, perf_score = _assess_performance(files)

    assert "- Bare except blocks: 0" in error_findings
    assert "- time.sleep() calls: 0" in perf_findings
    assert "- 'while True' loops: 0" in perf_findings
    assert perf_score == 10
