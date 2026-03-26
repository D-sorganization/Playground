"""Auto-generated syntax verification test suite for Project_GROOT.tools.smoke_test."""

import src.Project_GROOT.tools.smoke_test as target_module


def test_module_syntax_and_import():
    """Verify Project_GROOT.tools.smoke_test can be successfully imported and parsed."""
    assert target_module is not None


def test_has_symbol_test_gpu():
    """Verify test_gpu exists in module."""
    assert hasattr(target_module, "test_gpu")


def test_has_symbol_test_isaac_sim():
    """Verify test_isaac_sim exists in module."""
    assert hasattr(target_module, "test_isaac_sim")


def test_has_symbol_test_isaac_lab():
    """Verify test_isaac_lab exists in module."""
    assert hasattr(target_module, "test_isaac_lab")


def test_has_symbol_test_pose_backend():
    """Verify test_pose_backend exists in module."""
    assert hasattr(target_module, "test_pose_backend")


def test_has_symbol_test_dependencies():
    """Verify test_dependencies exists in module."""
    assert hasattr(target_module, "test_dependencies")


def test_has_symbol_test_project_structure():
    """Verify test_project_structure exists in module."""
    assert hasattr(target_module, "test_project_structure")


def test_has_symbol_test_all():
    """Verify test_all exists in module."""
    assert hasattr(target_module, "test_all")


def test_has_symbol_main():
    """Verify main exists in module."""
    assert hasattr(target_module, "main")
