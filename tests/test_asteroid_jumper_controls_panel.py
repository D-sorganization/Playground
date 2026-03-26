"""Auto-generated syntax verification test suite for asteroid_jumper.controls_panel."""
import pytest
import src.asteroid_jumper.controls_panel as target_module

def test_module_syntax_and_import():
    """Verify asteroid_jumper.controls_panel can be successfully imported and parsed."""
    assert target_module is not None

def test_has_symbol_ControlsPanel():
    """Verify ControlsPanel exists in module."""
    assert hasattr(target_module, "ControlsPanel")

def test_has_symbol__make_dspin():
    """Verify _make_dspin exists in module."""
    assert hasattr(target_module, "_make_dspin")

