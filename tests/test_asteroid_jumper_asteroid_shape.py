"""Auto-generated syntax verification test suite for asteroid_jumper.asteroid_shape."""
import pytest
import src.asteroid_jumper.asteroid_shape as target_module

def test_module_syntax_and_import():
    """Verify asteroid_jumper.asteroid_shape can be successfully imported and parsed."""
    assert target_module is not None

def test_has_symbol_ShapeKind():
    """Verify ShapeKind exists in module."""
    assert hasattr(target_module, "ShapeKind")

def test_has_symbol_AsteroidShape():
    """Verify AsteroidShape exists in module."""
    assert hasattr(target_module, "AsteroidShape")

def test_has_symbol__polar_to_xy():
    """Verify _polar_to_xy exists in module."""
    assert hasattr(target_module, "_polar_to_xy")

def test_has_symbol_make_circle():
    """Verify make_circle exists in module."""
    assert hasattr(target_module, "make_circle")

def test_has_symbol_make_ellipse():
    """Verify make_ellipse exists in module."""
    assert hasattr(target_module, "make_ellipse")

def test_has_symbol_make_random():
    """Verify make_random exists in module."""
    assert hasattr(target_module, "make_random")

def test_has_symbol_surface_normal_at_angle():
    """Verify surface_normal_at_angle exists in module."""
    assert hasattr(target_module, "surface_normal_at_angle")

def test_has_symbol_surface_point_at_angle():
    """Verify surface_point_at_angle exists in module."""
    assert hasattr(target_module, "surface_point_at_angle")

def test_has_symbol__angle_diff():
    """Verify _angle_diff exists in module."""
    assert hasattr(target_module, "_angle_diff")

