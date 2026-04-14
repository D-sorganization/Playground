"""Tests for scripts/mypy_autofix_agent.py and scripts/lib/ helpers."""

import sys
from pathlib import Path

# Make scripts/ importable
sys.path.insert(0, str(Path(__file__).parent.parent))

import scripts.mypy_autofix_agent as target_module
from src.mypy_agent.fix_strategies import (
    ALL_FIX_STRATEGIES,
    _ensure_import,
    add_type_ignore,
    fix_generic_suppression,
    fix_name_not_defined,
    has_type_ignore,
)
from src.mypy_agent.io import is_safe_path, parse_mypy_output
from src.mypy_agent.types import MypyError


def test_module_syntax_and_import():
    """Verify mypy_autofix_agent can be imported."""
    assert target_module is not None


def test_has_symbol_run_agent():
    """Verify run_agent exists."""
    assert hasattr(target_module, "run_agent")


def test_has_symbol_main():
    """Verify main exists."""
    assert hasattr(target_module, "main")


# --- parse_mypy_output tests ---


def test_parse_mypy_output_extracts_error():
    """parse_mypy_output returns MypyError for a valid error line."""
    sample = 'src/foo.py:10:5: error: Name "Callable" is not defined  [name-defined]'
    errors = parse_mypy_output(sample)
    assert len(errors) == 1
    assert errors[0].code == "name-defined"
    assert errors[0].line == 10
    assert errors[0].file == "src/foo.py"


def test_parse_mypy_output_ignores_notes():
    """parse_mypy_output skips note-severity lines."""
    sample = "src/foo.py:10:5: note: some note"
    errors = parse_mypy_output(sample)
    assert errors == []


def test_parse_mypy_output_empty_string():
    """parse_mypy_output returns empty list for empty input."""
    assert parse_mypy_output("") == []


# --- is_safe_path tests ---


def test_is_safe_path_src():
    """Files in src/ are safe."""
    assert is_safe_path("src/Project_GROOT/tools/video_ingest.py") is True


def test_is_safe_path_tests():
    """Files in tests/ are safe."""
    assert is_safe_path("tests/test_foo.py") is True


def test_is_safe_path_scripts():
    """Scripts are not in the safe zone."""
    assert is_safe_path("scripts/run_assessment.py") is False


def test_is_safe_path_non_python():
    """Non-.py files are not safe."""
    assert is_safe_path("src/foo.txt") is False


# --- has_type_ignore tests ---


def test_has_type_ignore_with_matching_code():
    """Line with matching ignore code returns True."""
    line = "x = 1  # type: ignore[attr-defined]"
    assert has_type_ignore(line, "attr-defined") is True


def test_has_type_ignore_without_ignore():
    """Plain line returns False."""
    assert has_type_ignore("x = 1", "attr-defined") is False


def test_has_type_ignore_no_code_arg():
    """Any type: ignore matches when code=None."""
    assert has_type_ignore("x = 1  # type: ignore[misc]") is True


# --- add_type_ignore tests ---


def test_add_type_ignore_appends_comment():
    """add_type_ignore appends the suppression comment."""
    result = add_type_ignore("x = foo.bar\n", "attr-defined")
    assert "# type: ignore[attr-defined]" in result


def test_add_type_ignore_extends_existing():
    """add_type_ignore extends existing bracket list."""
    result = add_type_ignore("x = 1  # type: ignore[misc]\n", "attr-defined")
    assert "attr-defined" in result


# --- fix_name_not_defined tests ---


def _make_error(code: str, message: str, line: int = 3) -> MypyError:
    return MypyError(
        file="src/t.py",
        line=line,
        column=1,
        severity="error",
        message=message,
        code=code,
    )


def test_fix_name_not_defined_known_type():
    """fix_name_not_defined adds import for known type."""
    err = _make_error("name-defined", 'Name "Callable" is not defined')
    lines = ["from __future__ import annotations\n", "import os\n", "x: Callable\n"]
    fix = fix_name_not_defined(lines, err)
    assert fix is not None
    assert fix.strategy == "real-fix"
    assert any("Callable" in ln for ln in lines)


def test_fix_name_not_defined_unknown_type():
    """fix_name_not_defined returns None for unknown types."""
    err = _make_error("name-defined", 'Name "SomeRandomClass" is not defined')
    lines = ["x: SomeRandomClass\n"]
    fix = fix_name_not_defined(lines, err)
    assert fix is None


def test_fix_name_not_defined_wrong_code():
    """fix_name_not_defined returns None for non-name-defined errors."""
    err = _make_error("attr-defined", 'Name "Callable" is not defined')
    lines = ["x: Callable\n"]
    fix = fix_name_not_defined(lines, err)
    assert fix is None


# --- fix_generic_suppression tests ---


def test_fix_generic_suppression_suppressible_code():
    """fix_generic_suppression suppresses known error codes."""
    err = _make_error("attr-defined", "some attribute error", line=1)
    lines = ["x = foo.bar\n"]
    fix = fix_generic_suppression(lines, err)
    assert fix is not None
    assert fix.strategy == "suppression"


def test_fix_generic_suppression_unknown_code():
    """fix_generic_suppression returns None for unknown error codes."""
    err = _make_error("some-unknown-code", "mystery error", line=1)
    lines = ["x = 1\n"]
    fix = fix_generic_suppression(lines, err)
    assert fix is None


def test_fix_generic_suppression_already_suppressed():
    """fix_generic_suppression returns None when already suppressed."""
    err = _make_error("attr-defined", "some error", line=1)
    lines = ["x = foo.bar  # type: ignore[attr-defined]\n"]
    fix = fix_generic_suppression(lines, err)
    assert fix is None


# --- ALL_FIX_STRATEGIES tests ---


def test_all_fix_strategies_count():
    """ALL_FIX_STRATEGIES has 5 entries."""
    assert len(ALL_FIX_STRATEGIES) == 5


def test_all_fix_strategies_are_callable():
    """All fix strategies are callable."""
    for strategy in ALL_FIX_STRATEGIES:
        assert callable(strategy)


# --- _ensure_import tests ---


def test_ensure_import_adds_missing():
    """_ensure_import adds an import that is not already present."""
    lines = ["import os\n", "x = 1\n"]
    result = _ensure_import(lines, "from typing import Any")
    assert result is True
    assert any("from typing import Any" in ln for ln in lines)


def test_ensure_import_no_duplicate():
    """_ensure_import does not add a duplicate import."""
    lines = ["from typing import Any\n", "x = 1\n"]
    result = _ensure_import(lines, "from typing import Any")
    assert result is False
    assert sum(1 for ln in lines if "from typing import Any" in ln) == 1
