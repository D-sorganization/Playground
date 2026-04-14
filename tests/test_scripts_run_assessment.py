"""Tests for scripts/run_assessment.py - decomposed helpers."""

import sys
from pathlib import Path

# Make scripts/ importable
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import run_assessment as target_module
from run_assessment import (
    ASSESSMENTS,
    _collect_assessment_metrics,
    _write_assessment_report,
    run_assessment,
)


def test_module_syntax_and_import():
    """Verify run_assessment can be imported."""
    assert target_module is not None


def test_has_symbol_run_assessment():
    """Verify run_assessment function exists."""
    assert hasattr(target_module, "run_assessment")


def test_has_symbol_main():
    """Verify main exists."""
    assert hasattr(target_module, "main")


def test_has_all_assessment_ids():
    """All A-O assessment IDs should be registered."""
    expected = set("ABCDEFGHIJKLMNO")
    assert set(ASSESSMENTS.keys()) == expected


# --- _collect_assessment_metrics tests ---


def test_collect_metrics_returns_tuple_for_all_ids(tmp_path):
    """Each assessment ID should return (findings, score) without raising."""
    for assessment_id in "ABCDEFGHIJKLMNO":
        findings, score = _collect_assessment_metrics(assessment_id, [])
        assert isinstance(findings, list), f"findings not list for {assessment_id}"
        assert isinstance(score, (int, float)), f"score not number for {assessment_id}"


def test_collect_metrics_score_within_bounds(tmp_path):
    """Score should be in [0, 10] for all assessments."""
    for assessment_id in "ABCDEFGHIJKLMNO":
        _, score = _collect_assessment_metrics(assessment_id, [])
        assert 0 <= score <= 10, f"score {score} out of bounds for {assessment_id}"


def test_collect_metrics_fallback_for_unknown_id():
    """Unknown assessment ID returns generic fallback."""
    findings, score = _collect_assessment_metrics("Z", [])
    assert isinstance(findings, list)
    assert score == 7  # fallback baseline


def test_collect_metrics_C_returns_findings():
    """Assessment C returns a findings list with test file count."""
    findings, _ = _collect_assessment_metrics("C", [])
    # At least one finding line mentioning test files
    assert any("Test files" in f for f in findings)


# --- _write_assessment_report tests ---


def test_write_assessment_report_creates_file(tmp_path):
    """_write_assessment_report creates a markdown file at output_path."""
    out = tmp_path / "report.md"
    _write_assessment_report("A", ASSESSMENTS["A"], 8, ["- finding 1"], out)
    assert out.exists()


def test_write_assessment_report_content(tmp_path):
    """Report contains assessment ID, name, and score."""
    out = tmp_path / "report.md"
    _write_assessment_report("B", ASSESSMENTS["B"], 7, ["- README: v"], out)
    content = out.read_text()
    assert "Assessment B" in content
    assert "7/10" in content
    assert "README: v" in content


def test_write_assessment_report_creates_parent_dirs(tmp_path):
    """_write_assessment_report creates missing parent directories."""
    out = tmp_path / "nested" / "deep" / "report.md"
    _write_assessment_report("C", ASSESSMENTS["C"], 5, [], out)
    assert out.exists()


# --- run_assessment integration tests ---


def test_run_assessment_unknown_id_returns_1(tmp_path):
    """run_assessment returns exit code 1 for an unknown assessment ID."""
    result = run_assessment("Z", tmp_path / "report.md")
    assert result == 1


def test_run_assessment_valid_id_returns_0(tmp_path):
    """run_assessment returns exit code 0 for a valid assessment ID."""
    result = run_assessment("A", tmp_path / "report.md")
    assert result == 0


def test_run_assessment_writes_report(tmp_path):
    """run_assessment creates the output file."""
    out = tmp_path / "report.md"
    run_assessment("G", out)
    assert out.exists()
