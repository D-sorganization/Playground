"""Auto-generated syntax verification tests for golf_swing_env."""

import pytest

pytest.importorskip("gymnasium")
pytest.importorskip("omni")
pytest.importorskip("torch")

import src.Project_GROOT.sim.golf_swing_env as target_module


def test_module_syntax_and_import():
    """Verify Project_GROOT.sim.golf_swing_env can be imported."""
    assert target_module is not None


def test_has_symbol_GolfSwingEnvCfg():
    """Verify GolfSwingEnvCfg exists in module."""
    assert hasattr(target_module, "GolfSwingEnvCfg")


def test_has_symbol_GolfSwingEnv():
    """Verify GolfSwingEnv exists in module."""
    assert hasattr(target_module, "GolfSwingEnv")
