"""Auto-generated syntax verification test suite for asteroid_jumper.metrics_panel."""
import pytest
import src.asteroid_jumper.metrics_panel as target_module

def test_module_syntax_and_import():
    """Verify asteroid_jumper.metrics_panel can be successfully imported and parsed."""
    assert target_module is not None

def test_has_symbol_MetricsPanel():
    """Verify MetricsPanel exists in module."""
    assert hasattr(target_module, "MetricsPanel")

def test_has_symbol__metric_row():
    """Verify _metric_row exists in module."""
    assert hasattr(target_module, "_metric_row")

