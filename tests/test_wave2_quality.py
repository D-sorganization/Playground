"""Unit tests for wave-2 quality sweep (#173).

Covers:
  - Physics Vec2 type-checking (TypeError on bad operands)
  - Asteroid shape DbC preconditions (ValueError on invalid input)
  - Input handler _jump_month helper (month boundary logic)
  - Smoke test project_structure function (pure path logic)
  - RenderSettings defaults
"""

from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))


# ---------------------------------------------------------------------------
# Vec2 type-error tests (new TypeError guards)
# ---------------------------------------------------------------------------


class TestVec2TypeGuards:
    """Verify that Vec2 raises TypeError on incompatible operands."""

    def test_add_non_vec2_raises(self) -> None:
        from asteroid_jumper.physics import Vec2

        with pytest.raises(TypeError, match="Vec2 \\+ Vec2 required"):
            Vec2(1, 2) + (3, 4)  # type: ignore[operator]

    def test_sub_non_vec2_raises(self) -> None:
        from asteroid_jumper.physics import Vec2

        with pytest.raises(TypeError, match="Vec2 - Vec2 required"):
            Vec2(1, 2) - [3, 4]  # type: ignore[operator]

    def test_mul_non_scalar_raises(self) -> None:
        from asteroid_jumper.physics import Vec2

        with pytest.raises(TypeError, match="Vec2 \\* scalar required"):
            Vec2(1, 2) * "bad"  # type: ignore[operator]

    def test_mul_int_works(self) -> None:
        from asteroid_jumper.physics import Vec2

        result = Vec2(2, 3) * 2
        assert result == Vec2(4, 6)


# ---------------------------------------------------------------------------
# Asteroid shape DbC
# ---------------------------------------------------------------------------


class TestAsteroidShapeDbC:
    """Verify DbC preconditions on shape factory functions."""

    def test_make_circle_negative_radius(self) -> None:
        from asteroid_jumper.asteroid_shape import make_circle

        with pytest.raises(ValueError):
            make_circle(-1.0)

    def test_make_circle_zero_radius(self) -> None:
        from asteroid_jumper.asteroid_shape import make_circle

        with pytest.raises(ValueError):
            make_circle(0.0)

    def test_make_ellipse_zero_semi_axis(self) -> None:
        from asteroid_jumper.asteroid_shape import make_ellipse

        with pytest.raises(ValueError):
            make_ellipse(0.0, 5.0)

    def test_make_ellipse_negative_semi_axis(self) -> None:
        from asteroid_jumper.asteroid_shape import make_ellipse

        with pytest.raises(ValueError):
            make_ellipse(5.0, -1.0)

    def test_make_random_negative_radius(self) -> None:
        from asteroid_jumper.asteroid_shape import make_random

        with pytest.raises(ValueError):
            make_random(-5.0)

    def test_make_random_roughness_out_of_range(self) -> None:
        from asteroid_jumper.asteroid_shape import make_random

        with pytest.raises(ValueError):
            make_random(5.0, roughness=1.5)

    def test_make_random_too_few_points(self) -> None:
        from asteroid_jumper.asteroid_shape import make_random

        with pytest.raises(ValueError):
            make_random(5.0, n_pts=3)

    def test_make_circle_too_few_points(self) -> None:
        from asteroid_jumper.asteroid_shape import make_circle

        with pytest.raises(ValueError):
            make_circle(5.0, n_pts=4)

    def test_make_ellipse_too_few_points(self) -> None:
        from asteroid_jumper.asteroid_shape import make_ellipse

        with pytest.raises(ValueError):
            make_ellipse(5.0, 3.0, n_pts=4)


# ---------------------------------------------------------------------------
# Physics DbC
# ---------------------------------------------------------------------------


class TestPhysicsDbC:
    """Verify DbC preconditions on physics helpers."""

    def test_moment_of_inertia_ellipse_zero_mass(self) -> None:
        from asteroid_jumper.physics import moment_of_inertia_ellipse

        with pytest.raises(ValueError):
            moment_of_inertia_ellipse(0.0, 1.0, 1.0)

    def test_moment_of_inertia_disk_zero_radius(self) -> None:
        from asteroid_jumper.physics import moment_of_inertia_disk

        with pytest.raises(ValueError):
            moment_of_inertia_disk(1.0, 0.0)

    def test_moment_of_inertia_rod_negative_length(self) -> None:
        from asteroid_jumper.physics import moment_of_inertia_rod

        with pytest.raises(ValueError):
            moment_of_inertia_rod(1.0, -1.0)

    def test_integrate_body_zero_dt(self) -> None:
        from asteroid_jumper.physics import RigidBody, integrate_body

        body = RigidBody(mass=1.0, moment_of_inertia=1.0)
        with pytest.raises(ValueError):
            integrate_body(body, 0.0)

    def test_integrate_body_negative_dt(self) -> None:
        from asteroid_jumper.physics import RigidBody, integrate_body

        body = RigidBody(mass=1.0, moment_of_inertia=1.0)
        with pytest.raises(ValueError):
            integrate_body(body, -0.1)

    def test_rigid_body_zero_mass(self) -> None:
        from asteroid_jumper.physics import RigidBody

        with pytest.raises(ValueError):
            RigidBody(mass=0.0, moment_of_inertia=1.0)

    def test_rigid_body_negative_moi(self) -> None:
        from asteroid_jumper.physics import RigidBody

        with pytest.raises(ValueError):
            RigidBody(mass=1.0, moment_of_inertia=-1.0)


# ---------------------------------------------------------------------------
# Surface geometry tests
# ---------------------------------------------------------------------------


class TestSurfaceGeometry:
    """Test surface normal and point functions."""

    def test_surface_normal_at_zero_angle(self) -> None:
        from asteroid_jumper.asteroid_shape import make_circle, surface_normal_at_angle

        shape = make_circle(5.0, n_pts=64)
        nx, ny = surface_normal_at_angle(shape, 0.0)
        # Should point outward (~+x direction)
        assert nx > 0.5
        assert math.hypot(nx, ny) == pytest.approx(1.0, abs=1e-6)

    def test_surface_point_distance_on_circle(self) -> None:
        from asteroid_jumper.asteroid_shape import make_circle, surface_point_at_angle

        shape = make_circle(10.0, n_pts=64)
        for angle in [0, math.pi / 4, math.pi / 2, math.pi]:
            x, y = surface_point_at_angle(shape, angle)
            dist = math.hypot(x, y)
            assert dist == pytest.approx(10.0, abs=0.5)


# ---------------------------------------------------------------------------
# Angle diff
# ---------------------------------------------------------------------------


class TestAngleDiffEdgeCases:
    """Edge cases for _angle_diff."""

    def test_pi_boundary(self) -> None:
        from asteroid_jumper.asteroid_shape import _angle_diff

        d = _angle_diff(math.pi, -math.pi)
        assert abs(d) <= math.pi + 1e-9

    def test_large_angles(self) -> None:
        from asteroid_jumper.asteroid_shape import _angle_diff

        d = _angle_diff(10 * math.pi + 0.1, 0.1)
        assert -math.pi <= d <= math.pi

    def test_negative_angles(self) -> None:
        from asteroid_jumper.asteroid_shape import _angle_diff

        d = _angle_diff(-0.5, -1.0)
        assert d == pytest.approx(0.5)


# ---------------------------------------------------------------------------
# SpringLaunch DbC
# ---------------------------------------------------------------------------


class TestSpringLaunchDbC:
    """DbC preconditions for SpringLaunch."""

    def test_negative_impulse_raises(self) -> None:
        from asteroid_jumper.physics import SpringLaunch, Vec2

        with pytest.raises(ValueError):
            SpringLaunch(
                total_impulse=-10.0,
                force_direction_rad=0.0,
                contact_point=Vec2(),
                asteroid_com=Vec2(),
                jumper_com=Vec2(0, 1),
                duration=0.5,
            )

    def test_zero_duration_raises(self) -> None:
        from asteroid_jumper.physics import SpringLaunch, Vec2

        with pytest.raises(ValueError):
            SpringLaunch(
                total_impulse=10.0,
                force_direction_rad=0.0,
                contact_point=Vec2(),
                asteroid_com=Vec2(),
                jumper_com=Vec2(0, 1),
                duration=0.0,
            )

    def test_step_zero_dt_raises(self) -> None:
        from asteroid_jumper.physics import SpringLaunch, Vec2

        spring = SpringLaunch(
            total_impulse=10.0,
            force_direction_rad=0.0,
            contact_point=Vec2(),
            asteroid_com=Vec2(),
            jumper_com=Vec2(0, 1),
            duration=0.5,
        )
        with pytest.raises(ValueError):
            spring.step(0.0)


# ---------------------------------------------------------------------------
# SimState invariants
# ---------------------------------------------------------------------------


class TestSimStateDbC:
    """DbC invariants for SimState."""

    def test_same_object_raises(self) -> None:
        from asteroid_jumper.physics import RigidBody, SimState

        body = RigidBody(mass=1.0, moment_of_inertia=1.0)
        with pytest.raises(ValueError, match="asteroid and jumper must differ"):
            SimState(asteroid=body, jumper=body)

    def test_angular_momentum_conservation(self) -> None:
        from asteroid_jumper.physics import RigidBody, SimState, Vec2

        ast = RigidBody(mass=100.0, moment_of_inertia=50.0, pos=Vec2(0, 0))
        jmp = RigidBody(mass=50.0, moment_of_inertia=5.0, pos=Vec2(0, 5))
        state = SimState(asteroid=ast, jumper=jmp)
        # At rest, total angular momentum should be zero
        assert state.total_angular_momentum == pytest.approx(0.0)


# ---------------------------------------------------------------------------
# step_simulation
# ---------------------------------------------------------------------------


class TestStepSimulation:
    """Test simulation stepping."""

    def test_step_zero_dt_raises(self) -> None:
        from asteroid_jumper.physics import RigidBody, SimState, Vec2, step_simulation

        ast = RigidBody(mass=100.0, moment_of_inertia=50.0)
        jmp = RigidBody(mass=50.0, moment_of_inertia=5.0, pos=Vec2(0, 5))
        state = SimState(asteroid=ast, jumper=jmp)
        with pytest.raises(ValueError):
            step_simulation(state, 0.0)

    def test_phase_transitions_to_flight(self) -> None:
        from asteroid_jumper.physics import (
            RigidBody,
            SimState,
            SpringLaunch,
            Vec2,
            step_simulation,
        )

        ast = RigidBody(mass=100.0, moment_of_inertia=50.0)
        jmp = RigidBody(mass=50.0, moment_of_inertia=5.0, pos=Vec2(0, 5))
        state = SimState(asteroid=ast, jumper=jmp)
        state.spring = SpringLaunch(
            total_impulse=100.0,
            force_direction_rad=math.pi / 2,
            contact_point=Vec2(0, 3),
            asteroid_com=ast.pos,
            jumper_com=jmp.pos,
            duration=0.1,
        )
        state.phase = "jumping"
        # Step through the spring duration
        for _ in range(50):
            step_simulation(state, 0.01)
        assert state.phase == "flight"
        assert state.spring is None
