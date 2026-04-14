"""Real Design-by-Contract tests for architectural invariants.

Replaces trivial ``assert True`` placeholders. Each test exercises a public
API that MUST raise ``ValueError`` when its precondition is violated, and
verifies that the happy path still succeeds.

Covered modules:
  * ``src.contracts`` (``@require`` / ``@ensure`` decorators)
  * ``src.asteroid_jumper.physics`` (``RigidBody``, ``SpringLaunch``,
    ``SimState``, ``moment_of_inertia_*``, ``compute_jump_impulse``,
    ``integrate_body``, ``step_simulation``)
  * ``src.asteroid_jumper.asteroid_shape`` (``AsteroidShape``, ``make_*``)
"""

from __future__ import annotations

import pytest

from src.asteroid_jumper.asteroid_shape import (
    AsteroidShape,
    ShapeKind,
    make_circle,
    make_ellipse,
    make_random,
)
from src.asteroid_jumper.physics import (
    RigidBody,
    SimState,
    SpringLaunch,
    Vec2,
    compute_jump_impulse,
    integrate_body,
    moment_of_inertia_disk,
    moment_of_inertia_ellipse,
    moment_of_inertia_rod,
    step_simulation,
)
from src.contracts import ensure, require

# ---------------------------------------------------------------------------
# contracts.py — require / ensure decorators
# ---------------------------------------------------------------------------


def test_dummy_dbc():
    """@require raises ValueError on precondition violation; passes otherwise."""

    @require(lambda x: x > 0, "x must be positive")
    def sqrt_positive(x: float) -> float:
        return x**0.5

    assert sqrt_positive(4.0) == pytest.approx(2.0)
    with pytest.raises(ValueError, match="x must be positive"):
        sqrt_positive(-1.0)

    @ensure(lambda r: r >= 0, "result must be non-negative")
    def bad_abs(x: float) -> float:
        return x  # intentionally wrong for negative input

    assert bad_abs(3.0) == 3.0
    with pytest.raises(RuntimeError, match="result must be non-negative"):
        bad_abs(-3.0)


def test_orthogonality():
    """Each module enforces its own preconditions independently (orthogonal DbC)."""
    # physics.RigidBody rejects non-positive mass.
    with pytest.raises(ValueError, match="mass must be positive"):
        RigidBody(mass=0.0, moment_of_inertia=1.0)

    # physics.moment_of_inertia_disk rejects non-positive radius.
    with pytest.raises(ValueError, match="radius must be positive"):
        moment_of_inertia_disk(mass=1.0, radius=0.0)

    # asteroid_shape.make_circle rejects non-positive radius.
    with pytest.raises(ValueError, match="radius must be positive"):
        make_circle(radius=-1.0)

    # asteroid_shape.AsteroidShape rejects < 3 vertices.
    with pytest.raises(ValueError, match="at least 3 vertices"):
        AsteroidShape(
            kind=ShapeKind.CIRCLE,
            vertices=((0.0, 0.0), (1.0, 0.0)),
            semi_a=1.0,
            semi_b=1.0,
        )


# ---------------------------------------------------------------------------
# physics preconditions
# ---------------------------------------------------------------------------


def test_rigid_body_rejects_non_positive_moment_of_inertia() -> None:
    with pytest.raises(ValueError, match="moment_of_inertia must be positive"):
        RigidBody(mass=1.0, moment_of_inertia=0.0)
    with pytest.raises(ValueError, match="moment_of_inertia must be positive"):
        RigidBody(mass=1.0, moment_of_inertia=-4.2)


def test_moment_of_inertia_helpers_reject_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="mass must be positive"):
        moment_of_inertia_ellipse(mass=-1.0, a=1.0, b=1.0)
    with pytest.raises(
        ValueError, match="ellipse semi-axes a and b must both be positive"
    ):
        moment_of_inertia_ellipse(mass=1.0, a=0.0, b=1.0)
    with pytest.raises(ValueError, match="length must be positive"):
        moment_of_inertia_rod(mass=1.0, length=0.0)
    with pytest.raises(ValueError, match="radius must be positive"):
        moment_of_inertia_disk(mass=1.0, radius=-3.0)


def test_compute_jump_impulse_rejects_negative_magnitude() -> None:
    with pytest.raises(ValueError, match="force_magnitude must be non-negative"):
        compute_jump_impulse(
            force_magnitude=-1.0,
            force_direction_rad=0.0,
            contact_point=Vec2(1.0, 0.0),
            asteroid_com=Vec2(0.0, 0.0),
            jumper_com=Vec2(2.0, 0.0),
        )


def test_integrate_body_and_step_simulation_reject_non_positive_dt() -> None:
    body = RigidBody(mass=1.0, moment_of_inertia=1.0)
    with pytest.raises(ValueError, match="dt must be positive"):
        integrate_body(body, dt=0.0)
    with pytest.raises(ValueError, match="dt must be positive"):
        integrate_body(body, dt=-0.01)

    asteroid = RigidBody(mass=160.0, moment_of_inertia=1.0)
    jumper = RigidBody(mass=80.0, moment_of_inertia=1.0)
    state = SimState(asteroid=asteroid, jumper=jumper)
    with pytest.raises(ValueError, match="dt must be positive"):
        step_simulation(state, dt=0.0)


def test_spring_launch_rejects_invalid_parameters() -> None:
    with pytest.raises(ValueError, match="total_impulse must be non-negative"):
        SpringLaunch(
            total_impulse=-1.0,
            force_direction_rad=0.0,
            contact_point=Vec2(0.0, 0.0),
            asteroid_com=Vec2(0.0, 0.0),
            jumper_com=Vec2(1.0, 0.0),
            duration=0.1,
        )
    with pytest.raises(ValueError, match="duration must be positive"):
        SpringLaunch(
            total_impulse=1.0,
            force_direction_rad=0.0,
            contact_point=Vec2(0.0, 0.0),
            asteroid_com=Vec2(0.0, 0.0),
            jumper_com=Vec2(1.0, 0.0),
            duration=0.0,
        )


def test_sim_state_rejects_shared_bodies() -> None:
    body = RigidBody(mass=1.0, moment_of_inertia=1.0)
    with pytest.raises(ValueError, match="asteroid and jumper must differ"):
        SimState(asteroid=body, jumper=body)


# ---------------------------------------------------------------------------
# asteroid_shape preconditions
# ---------------------------------------------------------------------------


def test_make_ellipse_rejects_invalid_axes_and_low_npts() -> None:
    with pytest.raises(ValueError, match="DbC Blocked"):
        make_ellipse(semi_a=0.0, semi_b=1.0)
    with pytest.raises(ValueError, match="DbC Blocked"):
        make_ellipse(semi_a=1.0, semi_b=-1.0)
    with pytest.raises(ValueError, match="DbC Blocked"):
        make_ellipse(semi_a=1.0, semi_b=1.0, n_pts=4)


def test_make_random_enforces_roughness_and_radius_bounds() -> None:
    with pytest.raises(ValueError, match="DbC Blocked"):
        make_random(base_radius=0.0)
    with pytest.raises(ValueError, match="DbC Blocked"):
        make_random(base_radius=1.0, roughness=1.5)
    with pytest.raises(ValueError, match="DbC Blocked"):
        make_random(base_radius=1.0, roughness=-0.1)
    with pytest.raises(ValueError, match="DbC Blocked"):
        make_random(base_radius=1.0, n_pts=3)
