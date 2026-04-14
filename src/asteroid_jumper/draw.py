"""Sprite and primitive drawing helpers for the asteroid-jumper renderer.

All functions are pure QPainter helpers — no QWidget or controller state.
This keeps individual drawing concerns isolated and independently testable.
"""

from __future__ import annotations

import math
from collections.abc import Callable
from typing import TYPE_CHECKING, Protocol

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)

if TYPE_CHECKING:
    from asteroid_jumper.asteroid_shape import AsteroidShape
    from asteroid_jumper.physics import RigidBody

# Type alias for world-to-screen coordinate transform callable
WorldToScreenFn = Callable[[float, float], QPointF]


class _ControllerLike(Protocol):
    """Structural typing for the SimController speed/metric query methods."""

    def jumper_speed(self) -> float: ...
    def jumper_angular_speed(self) -> float: ...
    def asteroid_speed(self) -> float: ...
    def asteroid_angular_speed(self) -> float: ...
    def off_centre_fraction(self) -> float: ...


# Catppuccin Mocha colour palette — re-exported so renderer.py can import from here.
C_BASE = QColor("#1e1e2e")
C_MANTLE = QColor("#181825")
C_CRUST = QColor("#11111b")
C_TEXT = QColor("#cdd6f4")
C_SUBTEXT = QColor("#a6adc8")
C_SURFACE0 = QColor("#313244")
C_SURFACE1 = QColor("#45475a")
C_BLUE = QColor("#89b4fa")
C_GREEN = QColor("#a6e3a1")
C_YELLOW = QColor("#f9e2af")
C_RED = QColor("#f38ba8")
C_MAUVE = QColor("#cba6f7")
C_TEAL = QColor("#94e2d5")
C_PEACH = QColor("#fab387")
C_LAVENDER = QColor("#b4befe")
C_SKY = QColor("#89dceb")
C_FLAMINGO = QColor("#f2cdcd")

STAR_POSITIONS: list[tuple[float, float]] = [
    (i * 0.618033988 % 1.0, (i * 0.381966 % 1.0)) for i in range(200)
]

# Normalised jumper height (fraction of scale)
JUMPER_HEIGHT_REF: float = 0.08


def draw_background(p: QPainter, width: int, height: int) -> None:
    """Fill the viewport with a deep-space gradient.

    Args:
        p: Active QPainter.
        width: Viewport width in pixels.
        height: Viewport height in pixels.
    """
    grad = QLinearGradient(0, 0, 0, height)
    grad.setColorAt(0.0, C_CRUST)
    grad.setColorAt(1.0, C_MANTLE)
    p.fillRect(QRectF(0, 0, width, height), grad)


def draw_stars(p: QPainter, width: int, height: int) -> None:
    """Scatter background star dots across the viewport.

    Args:
        p: Active QPainter.
        width: Viewport width in pixels.
        height: Viewport height in pixels.
    """
    p.save()
    for fx, fy in STAR_POSITIONS:
        sx, sy = fx * width, fy * height
        brightness = int(80 + 175 * ((fx * 7 + fy * 13) % 1.0))
        star_color = QColor(brightness, brightness, brightness, 200)
        p.setPen(QPen(star_color, 1.2))
        p.drawPoint(QPointF(sx, sy))
    p.restore()


def draw_single_trail(
    p: QPainter,
    trail: list[tuple[float, float]],
    color: QColor,
    world_to_screen_fn: WorldToScreenFn,
) -> None:
    """Draw a fading position trail.

    Args:
        p: Active QPainter.
        trail: List of (wx, wy) world-space positions.
        color: Base trail colour (alpha is varied for fade).
        world_to_screen_fn: Callable(wx, wy) -> QPointF.
    """
    if len(trail) < 2:
        return
    p.save()
    for i in range(len(trail) - 1):
        alpha = int(20 + 200 * i / len(trail))
        pen_color = QColor(color)
        pen_color.setAlpha(alpha)
        p.setPen(QPen(pen_color, 1.5))
        a = world_to_screen_fn(*trail[i])
        b = world_to_screen_fn(*trail[i + 1])
        p.drawLine(a, b)
    p.restore()


def draw_arrowhead(
    p: QPainter,
    start: QPointF,
    tip: QPointF,
    color: QColor,
    size: float = 8,
) -> None:
    """Draw a filled triangle arrowhead at *tip* pointing away from *start*.

    Args:
        p: Active QPainter.
        start: Arrow origin point.
        tip: Arrow tip point.
        color: Fill colour.
        size: Arrowhead size in pixels.
    """
    dx = tip.x() - start.x()
    dy = tip.y() - start.y()
    length = math.hypot(dx, dy)
    if length < 1e-3:
        return
    ux, uy = dx / length, dy / length
    px, py = -uy, ux  # perpendicular
    path = QPainterPath()
    path.moveTo(tip)
    path.lineTo(
        QPointF(
            tip.x() - ux * size + px * size / 2,
            tip.y() - uy * size + py * size / 2,
        )
    )
    path.lineTo(
        QPointF(
            tip.x() - ux * size - px * size / 2,
            tip.y() - uy * size - py * size / 2,
        )
    )
    path.closeSubpath()
    p.fillPath(path, QBrush(color))


def draw_asteroid(
    p: QPainter,
    ast: RigidBody,
    shape: AsteroidShape,
    scale: float,
    world_to_screen_fn: WorldToScreenFn,
) -> None:
    """Draw the asteroid polygon with gradient fill, outline, and craters.

    Args:
        p: Active QPainter.
        ast: Asteroid rigid body (position, angle).
        shape: Asteroid shape (vertices, semi axes).
        scale: Pixels per metre for crater sizing.
        world_to_screen_fn: Callable(wx, wy) -> QPointF.
    """
    p.save()
    path = QPainterPath()
    first = True
    for bx, by in shape.vertices:
        cos_a = math.cos(ast.angle)
        sin_a = math.sin(ast.angle)
        wx = bx * cos_a - by * sin_a + ast.pos.x
        wy = bx * sin_a + by * cos_a + ast.pos.y
        sp = world_to_screen_fn(wx, wy)
        if first:
            path.moveTo(sp)
            first = False
        else:
            path.lineTo(sp)
    path.closeSubpath()

    rock_center = world_to_screen_fn(ast.pos.x, ast.pos.y)
    rg = QRadialGradient(rock_center, scale * shape.semi_a * 1.1)
    rg.setColorAt(0.0, QColor("#6c5c4a"))
    rg.setColorAt(0.4, QColor("#4a3e32"))
    rg.setColorAt(1.0, QColor("#2a2320"))
    p.fillPath(path, rg)
    p.setPen(QPen(QColor("#8b7355"), 2))
    p.drawPath(path)

    com_sp = world_to_screen_fn(ast.pos.x, ast.pos.y)
    p.setPen(QPen(C_YELLOW, 1.5))
    p.setBrush(QBrush(C_YELLOW))
    p.drawEllipse(com_sp, 4, 4)

    draw_craters(p, ast, shape, scale, world_to_screen_fn)
    p.restore()


def draw_craters(
    p: QPainter,
    ast: RigidBody,
    shape: AsteroidShape,
    scale: float,
    world_to_screen_fn: WorldToScreenFn,
) -> None:
    """Draw decorative craters on the asteroid surface.

    Args:
        p: Active QPainter.
        ast: Asteroid rigid body.
        shape: Asteroid shape parameters.
        scale: Pixels per metre.
        world_to_screen_fn: Callable(wx, wy) -> QPointF.
    """
    crater_angles = [0.5, 1.8, 3.1, 4.7, 5.5]
    crater_sizes = [0.6, 0.4, 0.5, 0.3, 0.7]
    p.save()
    for ca, cs in zip(crater_angles, crater_sizes, strict=False):
        cx_b = math.cos(ca) * shape.semi_a * 0.55
        cy_b = math.sin(ca) * shape.semi_b * 0.55
        cos_a = math.cos(ast.angle)
        sin_a = math.sin(ast.angle)
        wx = cx_b * cos_a - cy_b * sin_a + ast.pos.x
        wy = cx_b * sin_a + cy_b * cos_a + ast.pos.y
        sp = world_to_screen_fn(wx, wy)
        cr = cs * scale * 0.8
        p.setPen(QPen(QColor("#2a1e15"), 1))
        p.setBrush(QBrush(QColor(42, 30, 21, 180)))
        p.drawEllipse(sp, cr, cr * 0.6)
    p.restore()


def draw_arm(p: QPainter, scale: float, arm_angle: float, *, left: bool) -> None:
    """Draw one astronaut arm.

    Args:
        p: Active QPainter (origin at jumper centre, already translated/rotated).
        scale: Pixels per metre.
        arm_angle: Arm elevation angle in radians.
        left: True for left arm, False for right.
    """
    h = scale * JUMPER_HEIGHT_REF
    torso_w = h * 0.14
    arm_len = h * 0.22
    xsign = -1.0 if left else 1.0
    shoulder_x = xsign * torso_w / 2
    shoulder_y = -h * 0.30
    elbow_x = shoulder_x + xsign * arm_len * 0.5 * math.cos(arm_angle)
    elbow_y = shoulder_y + arm_len * 0.5 * math.sin(arm_angle)
    hand_x = elbow_x + xsign * arm_len * 0.5 * math.cos(arm_angle * 0.7)
    hand_y = elbow_y + arm_len * 0.5 * math.sin(arm_angle * 0.7)
    pen = QPen(C_SURFACE1, max(2, scale * 0.06))
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.drawLine(QPointF(shoulder_x, shoulder_y), QPointF(elbow_x, elbow_y))
    p.drawLine(QPointF(elbow_x, elbow_y), QPointF(hand_x, hand_y))


def draw_legs(p: QPainter, scale: float, phase: float) -> None:
    """Draw two animated astronaut legs.

    Args:
        p: Active QPainter (origin at jumper centre, already translated/rotated).
        scale: Pixels per metre.
        phase: Animation phase 0 (crouched) to 1 (extended/tucked).
    """
    h = scale * JUMPER_HEIGHT_REF
    hip_y = -h * 0.05
    thigh = h * 0.20
    shin = h * 0.18
    foot_r = max(2, scale * 0.05)
    crouch = math.pi * 0.55 * (1.0 - phase)
    spread = math.radians(12)

    for xsign in (-1.0, 1.0):
        hip_x = xsign * h * 0.07
        thigh_angle = math.pi / 2 + xsign * spread + crouch * 0.5
        kx = hip_x + thigh * math.cos(thigh_angle)
        ky = hip_y + thigh * math.sin(thigh_angle)
        shin_angle = math.pi / 2 - xsign * spread * 0.5 - crouch
        fx = kx + shin * math.cos(shin_angle)
        fy = ky + shin * math.sin(shin_angle)

        pen = QPen(C_SURFACE1, max(2, scale * 0.06))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.drawLine(QPointF(hip_x, hip_y), QPointF(kx, ky))
        p.drawLine(QPointF(kx, ky), QPointF(fx, fy))
        p.setBrush(QBrush(C_SURFACE0))
        p.setPen(QPen(C_BLUE, 1))
        p.drawEllipse(QPointF(fx, fy), foot_r * 1.6, foot_r)


def draw_jumper_body(p: QPainter, scale: float, phase: float) -> None:
    """Draw the astronaut figure: head, torso, arms, and animated legs.

    Args:
        p: Active QPainter (origin at jumper centre, already translated/rotated).
        scale: Pixels per metre.
        phase: Animation phase 0 (crouched) to 1 (extended/tucked).
    """
    h = scale * JUMPER_HEIGHT_REF
    head_r = h * 0.12
    torso_h = h * 0.30
    torso_w = h * 0.14

    # Head / visor
    p.setBrush(QBrush(C_LAVENDER))
    p.setPen(QPen(C_SURFACE1, 1))
    p.drawEllipse(QPointF(0, -h * 0.45), head_r, head_r)
    p.setBrush(QBrush(QColor(137, 180, 250, 120)))
    p.drawEllipse(QPointF(0, -h * 0.45), head_r * 0.7, head_r * 0.7)

    # Torso
    torso_rect = QRectF(-torso_w / 2, -h * 0.35, torso_w, torso_h)
    p.setBrush(QBrush(C_SURFACE1))
    p.setPen(QPen(C_BLUE, 1))
    p.drawRoundedRect(torso_rect, 3, 3)
    p.setBrush(QBrush(C_BLUE))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRect(QRectF(-torso_w * 0.25, -h * 0.28, torso_w * 0.5, h * 0.07))

    # Arms
    arm_angle = math.radians(30 + 60 * phase)
    draw_arm(p, scale, arm_angle, left=True)
    draw_arm(p, scale, arm_angle, left=False)

    # Legs
    draw_legs(p, scale, phase)


def build_hud_lines(
    phase: str, sim_time: float, controller: _ControllerLike
) -> list[str]:
    """Build the text lines for the HUD overlay.

    Args:
        phase: Current simulation phase string.
        sim_time: Current simulation time in seconds.
        controller: SimController instance (duck-typed for speed/angle queries).

    Returns:
        List of formatted HUD text strings.
    """
    lines = [
        f"Phase: {phase.upper()}",
        f"Time:  {sim_time:.2f} s",
        f"Jumper speed:   {controller.jumper_speed():.3f} m/s",
        f"Jumper \u03c9:       {controller.jumper_angular_speed():.3f} rad/s",
        f"Asteroid speed: {controller.asteroid_speed():.3f} m/s",
        f"Asteroid \u03c9:     {controller.asteroid_angular_speed():.3f} rad/s",
        f"Off-centre:     {controller.off_centre_fraction():.2%}",
    ]
    if phase == "ready":
        lines.append("\u2190 Drag on asteroid to set jump angle")
    return lines


def draw_hud_overlay(
    p: QPainter,
    lines: list[str],
    width: int,
    height: int,  # noqa: ARG001
) -> None:
    """Draw the HUD text overlay in the top-left corner.

    Args:
        p: Active QPainter.
        lines: HUD text lines from build_hud_lines().
        width: Viewport width (unused, reserved for future layout).
        height: Viewport height (unused, reserved for future layout).
    """
    p.save()
    p.setFont(QFont("monospace", 9))
    bg = QColor(C_MANTLE)
    bg.setAlpha(200)
    row_h = 16
    margin = 8
    box_w = 240
    box_h = row_h * len(lines) + margin * 2
    p.fillRect(QRectF(8, 8, box_w, box_h), bg)
    p.setPen(QPen(C_SURFACE1, 1))
    p.drawRect(QRectF(8, 8, box_w, box_h))
    for i, line in enumerate(lines):
        color = C_BLUE if i == 0 else (C_GREEN if i < 5 else C_SUBTEXT)
        p.setPen(QPen(color))
        p.drawText(QPointF(margin + 8, margin + 8 + (i + 1) * row_h - 3), line)
    p.restore()
