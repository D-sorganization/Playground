"""Tests for asteroid_jumper.draw_helpers - pure-Python helper functions."""

from unittest.mock import MagicMock

import pytest

pytest.importorskip("PyQt6")

from src.asteroid_jumper.draw_helpers import (
    STAR_POSITIONS,
    build_hud_lines,
)


def test_star_positions_count():
    """STAR_POSITIONS should have exactly 200 entries."""
    assert len(STAR_POSITIONS) == 200


def test_star_positions_in_unit_range():
    """All star positions should be in [0, 1) x [0, 1)."""
    for fx, fy in STAR_POSITIONS:
        assert 0.0 <= fx < 1.0, f"fx={fx} out of [0, 1)"
        assert 0.0 <= fy < 1.0, f"fy={fy} out of [0, 1)"


# --- build_hud_lines tests ---


def _make_mock_controller(
    speed: float = 1.0,
    angular_speed: float = 0.5,
    off_centre: float = 0.1,
) -> MagicMock:
    """Return a mock SimController with numeric query methods."""
    ctrl = MagicMock()
    ctrl.jumper_speed.return_value = speed
    ctrl.jumper_angular_speed.return_value = angular_speed
    ctrl.asteroid_speed.return_value = speed * 0.5
    ctrl.asteroid_angular_speed.return_value = angular_speed * 0.5
    ctrl.off_centre_fraction.return_value = off_centre
    return ctrl


def test_build_hud_lines_returns_list():
    """build_hud_lines returns a list of strings."""
    ctrl = _make_mock_controller()
    lines = build_hud_lines("ready", 0.0, ctrl)
    assert isinstance(lines, list)
    assert all(isinstance(ln, str) for ln in lines)


def test_build_hud_lines_contains_phase():
    """HUD lines include the uppercased phase string."""
    ctrl = _make_mock_controller()
    lines = build_hud_lines("flight", 1.23, ctrl)
    assert any("FLIGHT" in ln for ln in lines)


def test_build_hud_lines_contains_time():
    """HUD lines include the formatted simulation time."""
    ctrl = _make_mock_controller()
    lines = build_hud_lines("jumping", 3.75, ctrl)
    assert any("3.75" in ln for ln in lines)


def test_build_hud_lines_contains_speed():
    """HUD lines include the jumper speed value."""
    ctrl = _make_mock_controller(speed=2.345)
    lines = build_hud_lines("flight", 0.0, ctrl)
    assert any("2.345" in ln for ln in lines)


def test_build_hud_lines_ready_phase_has_hint():
    """In 'ready' phase, a drag-hint line is appended."""
    ctrl = _make_mock_controller()
    lines = build_hud_lines("ready", 0.0, ctrl)
    # Should have more lines than non-ready phase
    lines_flight = build_hud_lines("flight", 0.0, ctrl)
    assert len(lines) > len(lines_flight)


def test_build_hud_lines_non_ready_no_hint():
    """Non-ready phase should not have the drag hint."""
    ctrl = _make_mock_controller()
    lines = build_hud_lines("flight", 0.0, ctrl)
    assert not any("Drag" in ln for ln in lines)


def test_build_hud_lines_off_centre_formatted():
    """Off-centre fraction should appear as a percentage string."""
    ctrl = _make_mock_controller(off_centre=0.25)
    lines = build_hud_lines("jumping", 0.0, ctrl)
    assert any("25.00%" in ln for ln in lines)
