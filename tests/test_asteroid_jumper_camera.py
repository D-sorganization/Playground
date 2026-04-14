"""Tests for asteroid_jumper.camera - Camera viewport helper."""

import pytest

pytest.importorskip("PyQt6")

from src.asteroid_jumper.camera import Camera


def test_camera_default_scale():
    """Camera initialises with default scale > 0."""
    cam = Camera()
    assert cam.scale > 0


def test_camera_custom_scale():
    """Camera accepts a positive custom scale."""
    cam = Camera(scale=50.0)
    assert cam.scale == 50.0


def test_camera_negative_scale_raises():
    """Camera rejects non-positive scale."""
    with pytest.raises(AssertionError, match="positive"):
        Camera(scale=-1.0)


def test_camera_zero_scale_raises():
    """Camera rejects zero scale."""
    with pytest.raises(AssertionError):
        Camera(scale=0.0)


def test_camera_reset_restores_defaults():
    """reset() returns scale to default and pan to origin."""
    from src.asteroid_jumper.camera import VIEWPORT_SCALE_DEFAULT

    cam = Camera(scale=100.0)
    cam.reset()
    assert cam.scale == VIEWPORT_SCALE_DEFAULT
    assert cam.pan.x() == 0.0
    assert cam.pan.y() == 0.0


def test_camera_set_scale():
    """set_scale() updates the zoom level."""
    cam = Camera()
    cam.set_scale(80.0)
    assert cam.scale == 80.0


def test_camera_set_scale_invalid():
    """set_scale() rejects non-positive values."""
    cam = Camera()
    with pytest.raises(AssertionError):
        cam.set_scale(0.0)


def test_camera_zoom_in():
    """zoom(factor > 1) increases scale."""
    cam = Camera(scale=25.0)
    cam.zoom(1.1)
    assert cam.scale > 25.0


def test_camera_zoom_out():
    """zoom(factor < 1) decreases scale."""
    cam = Camera(scale=25.0)
    cam.zoom(0.9)
    assert cam.scale < 25.0


def test_camera_zoom_clamped_min():
    """zoom() respects min_scale lower bound."""
    cam = Camera(scale=6.0)
    cam.zoom(0.01, min_scale=5.0)
    assert cam.scale == 5.0


def test_camera_zoom_clamped_max():
    """zoom() respects max_scale upper bound."""
    cam = Camera(scale=190.0)
    cam.zoom(2.0, max_scale=200.0)
    assert cam.scale == 200.0


def test_camera_zoom_invalid_factor():
    """zoom() rejects zero or negative factor."""
    cam = Camera()
    with pytest.raises(AssertionError):
        cam.zoom(0.0)


def test_world_to_screen_origin_maps_to_centre():
    """World origin should map to viewport centre when pan is zero."""
    cam = Camera(scale=25.0)
    width, height = 800, 600
    sp = cam.world_to_screen(0.0, 0.0, width, height)
    assert abs(sp.x() - width / 2) < 1e-6
    assert abs(sp.y() - height / 2) < 1e-6


def test_world_to_screen_positive_x_goes_right():
    """Positive world X should produce screen X > centre."""
    cam = Camera(scale=10.0)
    width, height = 400, 300
    sp = cam.world_to_screen(5.0, 0.0, width, height)
    assert sp.x() > width / 2


def test_world_to_screen_positive_y_goes_up():
    """Positive world Y should produce screen Y < centre (y-flip)."""
    cam = Camera(scale=10.0)
    width, height = 400, 300
    sp = cam.world_to_screen(0.0, 5.0, width, height)
    assert sp.y() < height / 2


def test_screen_to_world_roundtrip():
    """world_to_screen followed by screen_to_world should return original coords."""
    cam = Camera(scale=20.0)
    width, height = 640, 480
    wx_in, wy_in = 3.5, -2.1
    sp = cam.world_to_screen(wx_in, wy_in, width, height)
    wx_out, wy_out = cam.screen_to_world(sp.x(), sp.y(), width, height)
    assert abs(wx_out - wx_in) < 1e-9
    assert abs(wy_out - wy_in) < 1e-9


def test_screen_to_world_centre_is_origin():
    """Screen centre should map to world origin when pan is zero."""
    cam = Camera()
    width, height = 800, 600
    wx, wy = cam.screen_to_world(width / 2, height / 2, width, height)
    assert abs(wx) < 1e-9
    assert abs(wy) < 1e-9
