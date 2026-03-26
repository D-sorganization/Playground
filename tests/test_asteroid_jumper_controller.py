"""Auto-generated syntax verification test suite for asteroid_jumper.controller."""

import src.asteroid_jumper.controller as target_module


def test_module_syntax_and_import():
    """Verify asteroid_jumper.controller can be successfully imported and parsed."""
    assert target_module is not None


def test_has_symbol_SimController():
    """Verify SimController exists in module."""
    assert hasattr(target_module, "SimController")
