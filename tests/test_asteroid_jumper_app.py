"""Auto-generated syntax verification test suite for asteroid_jumper.app."""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
pytest.importorskip("PyQt6")

import src.asteroid_jumper.app as target_module


def test_module_syntax_and_import():
    """Verify asteroid_jumper.app can be successfully imported and parsed."""
    assert target_module is not None


def test_has_symbol_main():
    """Verify main exists in module."""
    assert hasattr(target_module, "main")
