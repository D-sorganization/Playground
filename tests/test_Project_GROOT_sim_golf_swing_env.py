"""Auto-generated syntax verification tests for golf_swing_env."""

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
