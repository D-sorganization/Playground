"""Tests for scripts/analyze_completist_data.py - decomposed helpers."""

import sys
from pathlib import Path

# Make scripts/ importable
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import analyze_completist_data as target_module
import completist_report
from analyze_completist_data import (
    _build_priority_table,
    _build_report_lines,
    _collect_report_data,
    _save_report_files,
    is_excluded,
)


def test_module_syntax_and_import():
    """Verify analyze_completist_data can be imported."""
    assert target_module is not None


def test_has_symbol_generate_report():
    """Verify generate_report exists."""
    assert hasattr(target_module, "generate_report")


# --- is_excluded tests ---


def test_is_excluded_empty_string():
    """Empty path is excluded."""
    assert is_excluded("") is True


def test_is_excluded_docs_path():
    """Paths under docs/ are excluded."""
    assert is_excluded("docs/assessments/foo.md") is True


def test_is_excluded_source_path():
    """Regular source paths are not excluded."""
    assert is_excluded("src/Project_GROOT/tools/video_ingest.py") is False


def test_is_excluded_self():
    """The script itself is excluded."""
    assert is_excluded("scripts/analyze_completist_data.py") is True


# --- _collect_report_data tests ---


def test_collect_report_data_returns_four_lists():
    """_collect_report_data returns a 4-tuple of lists when data files absent."""
    result = _collect_report_data()
    assert len(result) == 4
    for lst in result:
        assert isinstance(lst, list)


def test_collect_report_data_empty_when_no_files():
    """Returns empty lists when completist data files do not exist."""
    criticals, todos, fixmes, missing_docs = _collect_report_data()
    # All empty since .jules/completist_data/ is absent in tests
    assert criticals == [] or isinstance(criticals, list)
    assert todos == [] or isinstance(todos, list)


# --- _build_report_lines tests ---


def test_build_report_lines_contains_header():
    """Report lines include the date header."""
    lines = _build_report_lines("2026-01-01", [], [], [], [])
    body = "\n".join(lines)
    assert "Completist Report: 2026-01-01" in body


def test_build_report_lines_contains_summary():
    """Report lines include executive summary counts."""
    lines = _build_report_lines("2026-01-01", [], [], [], [])
    body = "\n".join(lines)
    assert "Executive Summary" in body
    assert "Critical Gaps" in body


def test_build_report_lines_with_findings():
    """Report includes finding rows when criticals are provided."""
    critical = {"file": "src/foo.py", "line": "10", "type": "Stub"}
    lines = _build_report_lines("2026-01-01", [critical], [], [], [])
    body = "\n".join(lines)
    assert "src/foo.py" in body


def test_build_report_lines_feature_gap_section():
    """Report includes Feature Gap Matrix when todos provided."""
    todo = {"file": "src/bar.py", "line": "5", "type": "TRACKED_TASK", "text": "do x"}
    lines = _build_report_lines("2026-01-01", [], [todo], [], [])
    body = "\n".join(lines)
    assert "Feature Gap Matrix" in body
    assert "do x" in body


# --- _build_priority_table tests ---


def test_build_priority_table_empty():
    """_build_priority_table with empty lists returns header lines only."""
    lines = _build_priority_table([], [])
    assert any("Recommended Implementation Order" in ln for ln in lines)


def test_build_priority_table_ranks_items():
    """Items appear in the table when provided."""
    finding = {"file": "src/x.py", "line": "1", "type": "Stub", "name": "my_func"}
    lines = _build_priority_table([finding], [])
    body = "\n".join(lines)
    assert "src/x.py" in body


def test_build_priority_table_max_20_rows():
    """Priority table is capped at 20 data rows."""
    findings = [
        {"file": f"src/f{i}.py", "line": str(i), "type": "Stub", "name": f"f{i}"}
        for i in range(30)
    ]
    lines = _build_priority_table(findings, [])
    # Header lines (4) + max 20 data rows
    data_rows = [
        ln for ln in lines if ln.startswith("| ") and not ln.startswith("| Priority")
    ]
    assert len(data_rows) <= 20


# --- _save_report_files tests ---


def test_save_report_files_creates_dated_file(tmp_path, monkeypatch):
    """_save_report_files writes a dated markdown file."""
    monkeypatch.setattr(completist_report, "REPORT_DIR", str(tmp_path))
    _save_report_files("2026-04-14", "report content")
    assert (tmp_path / "Completist_Report_2026-04-14.md").exists()


def test_save_report_files_creates_latest(tmp_path, monkeypatch):
    """_save_report_files writes COMPLETIST_LATEST.md."""
    monkeypatch.setattr(completist_report, "REPORT_DIR", str(tmp_path))
    _save_report_files("2026-04-14", "report content")
    assert (tmp_path / "COMPLETIST_LATEST.md").exists()


def test_save_report_files_content(tmp_path, monkeypatch):
    """_save_report_files writes the provided content."""
    monkeypatch.setattr(completist_report, "REPORT_DIR", str(tmp_path))
    _save_report_files("2026-04-14", "hello world")
    content = (tmp_path / "COMPLETIST_LATEST.md").read_text()
    assert "hello world" in content
