"""Real physics tests for ``src.asteroid_jumper.physics``.

Replaces the previous Vec2-only coverage with assertions on:

  * ``RigidBody`` invariants and derived quantities
  * ``moment_of_inertia_*`` analytical formulas
  * ``compute_jump_impulse`` Newton's third law + torque signs
  * ``apply_impulse`` linear and angular response
  * ``integrate_body`` semi-implicit Euler translation
  * ``SpringLaunch`` half-sine impulse sums to ``total_impulse``
  * ``SimState`` conservation of linear + angular momentum
  * ``step_simulation`` equal-and-opposite impulse delivery
  * ``off_centre_ratio`` geometric invariants
"""

from __future__ import annotations

import math

import pytest

from src.asteroid_jumper.physics import (
    RigidBody,
    SimState,
    SpringLaunch,
    Vec2,
    apply_impulse,
    compute_jump_impulse,
    integrate_body,
    moment_of_inertia_disk,
    moment_of_inertia_ellipse,
    moment_of_inertia_rod,
    off_centre_ratio,
    step_simulation,
)

# ---------------------------------------------------------------------------
# Vec2 basics (kept from previous suite — these tests actually exercise the
# operator overloads that RigidBody integration relies on).
# ---------------------------------------------------------------------------


def test_vec2_addition() -> None:
    v1 = Vec2(1.0, 2.0)
    v2 = Vec2(3.0, 4.0)
    v3 = v1 + v2
    assert v3.x == pytest.approx(4.0)
    assert v3.y == pytest.approx(6.0)


def test_vec2_subtraction() -> None:
    v1 = Vec2(5.0, 5.0)
    v2 = Vec2(3.0, 2.0)
    v3 = v1 - v2
    assert v3.x == pytest.approx(2.0)
    assert v3.y == pytest.approx(3.0)


def test_vec2_multiplication() -> None:
    v1 = Vec2(2.0, 3.0)
    v3 = v1 * 2
    assert v3.x == pytest.approx(4.0)
    assert v3.y == pytest.approx(6.0)


def test_vec2_invalid_addition() -> None:
    v1 = Vec2(1.0, 1.0)
    with pytest.raises(ValueError):
        _ = v1 + 5.0  # type: ignore[operator]


def test_vec2_dot_cross_and_length() -> None:
    a = Vec2(3.0, 4.0)
    b = Vec2(1.0, 2.0)
    assert a.dot(b) == pytest.approx(3.0 * 1.0 + 4.0 * 2.0)
    assert a.cross(b) == pytest.approx(3.0 * 2.0 - 4.0 * 1.0)
    assert a.length() == pytest.approx(5.0)
    unit = a.normalize()
    assert unit.length() == pytest.approx(1.0)
    # rotate 90° CCW == perp
    rotated = a.rotate(math.pi / 2.0)
    perp = a.perp()
    assert rotated.x == pytest.approx(perp.x)
    assert rotated.y == pytest.approx(perp.y)


# ---------------------------------------------------------------------------
# RigidBody
# ---------------------------------------------------------------------------


def test_rigid_body_kinetic_energy_and_speed() -> None:
    body = RigidBody(
        mass=2.0,
        moment_of_inertia=4.0,
        vel=Vec2(3.0, 4.0),
        angular_vel=5.0,
    )
    assert body.speed == pytest.approx(5.0)
    expected_trans = 0.5 * body.mass * body.speed**2
    expected_rot = 0.5 * body.moment_of_inertia * body.angular_vel**2
    assert body.kinetic_energy_trans == pytest.approx(expected_trans)
    assert body.kinetic_energy_rot == pytest.approx(expected_rot)


def test_rigid_body_post_init_rejects_invalid_inertia() -> None:
    with pytest.raises(ValueError):
        RigidBody(mass=1.0, moment_of_inertia=0.0)
    with pytest.raises(ValueError):
        RigidBody(mass=-1.0, moment_of_inertia=1.0)


# ---------------------------------------------------------------------------
# moment_of_inertia_* — analytical solutions
# ---------------------------------------------------------------------------


def test_moment_of_inertia_disk_matches_analytical_formula() -> None:
    # I = (1/2) m r^2 for a solid disk.
    assert moment_of_inertia_disk(mass=4.0, radius=3.0) == pytest.approx(18.0)


def test_moment_of_inertia_ellipse_reduces_to_disk_when_axes_equal() -> None:
    # For a=b=r, (1/4) m (a^2 + b^2) = (1/2) m r^2
    mass = 5.0
    r = 2.0
    disk = moment_of_inertia_disk(mass, r)
    ellipse = moment_of_inertia_ellipse(mass, r, r)
    assert ellipse == pytest.approx(disk)
    assert ellipse == pytest.approx(0.5 * mass * r * r)


def test_moment_of_inertia_rod_matches_analytical_formula() -> None:
    # I = m L^2 / 12 for a thin rod about its centre.
    assert moment_of_inertia_rod(mass=12.0, length=2.0) == pytest.approx(4.0)


# ---------------------------------------------------------------------------
# compute_jump_impulse / apply_impulse
# ---------------------------------------------------------------------------


def test_compute_jump_impulse_axial_push_has_zero_torque() -> None:
    # Jumper at (2,0), asteroid at (0,0), contact at (1,0), push in +x.
    # Contact is on the line joining COMs so no torque on either body.
    jumper_impulse, ast_tau, jmp_tau = compute_jump_impulse(
        force_magnitude=10.0,
        force_direction_rad=0.0,
        contact_point=Vec2(1.0, 0.0),
        asteroid_com=Vec2(0.0, 0.0),
        jumper_com=Vec2(2.0, 0.0),
    )
    assert jumper_impulse.x == pytest.approx(10.0)
    assert jumper_impulse.y == pytest.approx(0.0, abs=1e-12)
    assert ast_tau == pytest.approx(0.0, abs=1e-12)
    assert jmp_tau == pytest.approx(0.0, abs=1e-12)


def test_compute_jump_impulse_off_axis_produces_expected_torque() -> None:
    # Contact at (0,1) above asteroid COM, push in +x direction.
    # r_asteroid = (0,1); asteroid torque = r.cross(-J) = 0*0 - 1*(-10) = 10.
    jumper_impulse, ast_tau, _ = compute_jump_impulse(
        force_magnitude=10.0,
        force_direction_rad=0.0,
        contact_point=Vec2(0.0, 1.0),
        asteroid_com=Vec2(0.0, 0.0),
        jumper_com=Vec2(0.0, 5.0),
    )
    assert jumper_impulse.x == pytest.approx(10.0)
    assert ast_tau == pytest.approx(10.0)


def test_apply_impulse_updates_velocity_and_angular_velocity() -> None:
    body = RigidBody(mass=2.0, moment_of_inertia=5.0)
    apply_impulse(body, Vec2(4.0, -6.0), torque_impulse=10.0)
    # Expected delta-v is impulse over mass; angular delta is torque over inertia.
    assert body.vel.x == pytest.approx(2.0)
    assert body.vel.y == pytest.approx(-3.0)
    assert body.angular_vel == pytest.approx(2.0)


# ---------------------------------------------------------------------------
# integrate_body
# ---------------------------------------------------------------------------


def test_integrate_body_advances_position_linearly_in_zero_gravity() -> None:
    body = RigidBody(
        mass=1.0,
        moment_of_inertia=1.0,
        pos=Vec2(0.0, 0.0),
        vel=Vec2(3.0, -4.0),
        angle=0.0,
        angular_vel=1.0,
    )
    integrate_body(body, dt=0.5)
    assert body.pos.x == pytest.approx(1.5)
    assert body.pos.y == pytest.approx(-2.0)
    assert body.angle == pytest.approx(0.5)
    # No forces → velocity unchanged.
    assert body.vel.x == pytest.approx(3.0)
    assert body.vel.y == pytest.approx(-4.0)


def test_integrate_body_rejects_non_positive_dt() -> None:
    body = RigidBody(mass=1.0, moment_of_inertia=1.0)
    with pytest.raises(ValueError):
        integrate_body(body, dt=0.0)
    with pytest.raises(ValueError):
        integrate_body(body, dt=-1e-6)


# ---------------------------------------------------------------------------
# SpringLaunch
# ---------------------------------------------------------------------------


def test_spring_launch_total_impulse_approximates_requested_value() -> None:
    """Summing the per-step impulses over the full duration must equal
    ``total_impulse`` (that is the defining property of the half-sine
    profile)."""
    launch = SpringLaunch(
        total_impulse=100.0,
        force_direction_rad=0.0,
        contact_point=Vec2(1.0, 0.0),
        asteroid_com=Vec2(0.0, 0.0),
        jumper_com=Vec2(2.0, 0.0),
        duration=0.4,
    )
    dt = 0.001
    total_x = 0.0
    safety = 10000
    while not launch.is_complete and safety > 0:
        result = launch.step(dt)
        assert result is not None
        jumper_impulse, _, _ = result
        total_x += jumper_impulse.x
        safety -= 1
    assert launch.is_complete
    # Integration of half-sine ramp has ~1% error at dt=1ms.
    assert total_x == pytest.approx(100.0, rel=0.02)
    # After completion, further ``step`` calls return None.
    assert launch.step(dt) is None


def test_spring_launch_rejects_invalid_step_dt() -> None:
    launch = SpringLaunch(
        total_impulse=1.0,
        force_direction_rad=0.0,
        contact_point=Vec2(0.0, 0.0),
        asteroid_com=Vec2(0.0, 0.0),
        jumper_com=Vec2(1.0, 0.0),
        duration=0.1,
    )
    with pytest.raises(ValueError):
        launch.step(0.0)


# ---------------------------------------------------------------------------
# SimState / step_simulation — conservation laws
# ---------------------------------------------------------------------------


def _make_state() -> SimState:
    asteroid = RigidBody(
        mass=160.0,
        moment_of_inertia=moment_of_inertia_disk(160.0, 10.0),
        pos=Vec2(0.0, 0.0),
    )
    jumper = RigidBody(
        mass=80.0,
        moment_of_inertia=moment_of_inertia_disk(80.0, 0.3),
        pos=Vec2(0.0, 10.0),
    )
    return SimState(asteroid=asteroid, jumper=jumper)


def test_sim_state_initial_momentum_is_zero() -> None:
    state = _make_state()
    p = state.total_linear_momentum
    assert p.x == pytest.approx(0.0)
    assert p.y == pytest.approx(0.0)
    assert state.total_angular_momentum == pytest.approx(0.0)


def test_step_simulation_conserves_linear_momentum_during_spring_push() -> None:
    """Jump impulses are internal forces, so total linear momentum stays 0."""
    state = _make_state()
    state.spring = SpringLaunch(
        total_impulse=500.0,
        force_direction_rad=math.pi / 2.0,  # jumper launches +y
        contact_point=Vec2(0.0, 10.0),
        asteroid_com=state.asteroid.pos,
        jumper_com=state.jumper.pos,
        duration=0.4,
    )
    state.phase = "jumping"
    dt = 0.001
    for _ in range(1000):  # 1s — covers entire 0.4 s push + flight
        step_simulation(state, dt)
    p = state.total_linear_momentum
    assert p.x == pytest.approx(0.0, abs=1e-9)
    assert p.y == pytest.approx(0.0, abs=1e-9)
    # Jumper should be moving +y, asteroid -y (equal and opposite).
    assert state.jumper.vel.y > 0
    assert state.asteroid.vel.y < 0
    # Momentum magnitudes must match (|m_j v_j| == |m_a v_a|).
    assert state.jumper.mass * state.jumper.vel.y == pytest.approx(
        -state.asteroid.mass * state.asteroid.vel.y, rel=1e-9
    )
    # Spring drained and phase advanced.
    assert state.spring is None
    assert state.phase == "flight"


def test_step_simulation_rejects_non_positive_dt() -> None:
    state = _make_state()
    with pytest.raises(ValueError):
        step_simulation(state, dt=0.0)
    with pytest.raises(ValueError):
        step_simulation(state, dt=-0.01)


# ---------------------------------------------------------------------------
# off_centre_ratio
# ---------------------------------------------------------------------------


def test_off_centre_ratio_zero_for_contact_on_com_line() -> None:
    # Contact lies exactly on the segment between COMs.
    ratio = off_centre_ratio(
        contact_point=Vec2(0.0, 5.0),
        asteroid_com=Vec2(0.0, 0.0),
        jumper_com=Vec2(0.0, 10.0),
    )
    assert ratio == pytest.approx(0.0, abs=1e-12)


def test_off_centre_ratio_clamped_to_unit_interval() -> None:
    # Heavily off-axis contact → ratio saturates at 1.0.
    ratio = off_centre_ratio(
        contact_point=Vec2(50.0, 5.0),
        asteroid_com=Vec2(0.0, 0.0),
        jumper_com=Vec2(0.0, 10.0),
    )
    assert 0.0 <= ratio <= 1.0
    assert ratio == pytest.approx(1.0)


def test_off_centre_ratio_zero_when_coms_coincide() -> None:
    ratio = off_centre_ratio(
        contact_point=Vec2(1.0, 1.0),
        asteroid_com=Vec2(0.0, 0.0),
        jumper_com=Vec2(0.0, 0.0),
    )
    assert ratio == pytest.approx(0.0, abs=1e-12)
