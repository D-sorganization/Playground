"""Drawing helper functions for the AsteroidJumper renderer.

All functions receive a QPainter and the drawing parameters they need;
none access widget state directly (Law of Demeter).
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from PyQt6.QtCore import QPointF, QRectF, Qt
from PyQt6.QtGui import (
    QBrush,
    QColor,
    QPainter,
    QPainterPath,
    QPen,
    QRadialGradient,
)

if TYPE_CHECKING:
    from asteroid_jumper.asteroid_shape import AsteroidShape
    from asteroid_jumper.physics import RigidBody

# Catppuccin Mocha colours (re-exported so renderer can import from here)
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

JUMPER_HEIGHT_REF: float = 0.08  # fraction of scale


def draw_craters(
    p: QPainter,
    ast: RigidBody,
    shape: AsteroidShape,
    world_to_screen: object,
    scale: float,
) -> None:
    """Draw decorative craters on the asteroid surface."""
    crater_angles = [0.5, 1.8, 3.1, 4.7, 5.5]
    crater_sizes = [0.6, 0.4, 0.5, 0.3, 0.7]
    p.save()
    for ca, cs in zip(crater_angles, crater_sizes, strict=False):
        cx_b = math.cos(ca) * shape.semi_a * 0.55
        cy_b = math.sin(ca) * shape.semi_b * 0.55
        cos_a, sin_a = math.cos(ast.angle), math.sin(ast.angle)
        wx = cx_b * cos_a - cy_b * sin_a + ast.pos.x
        wy = cx_b * sin_a + cy_b * cos_a + ast.pos.y
        sp = world_to_screen(wx, wy)  # type: ignore[operator]
        cr = cs * scale * 0.8
        p.setPen(QPen(QColor("#2a1e15"), 1))
        p.setBrush(QBrush(QColor(42, 30, 21, 180)))
        p.drawEllipse(sp, cr, cr * 0.6)
    p.restore()


def draw_arm(p: QPainter, scale: float, arm_angle: float, *, left: bool) -> None:
    """Draw one arm of the jumper figure."""
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
    """Draw two animated legs: crouch on ground, extend at jump, tuck in flight."""
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
    """Draw human figure: head, torso, arms, animated legs."""
    h = scale * JUMPER_HEIGHT_REF
    head_r = h * 0.12
    torso_h = h * 0.30
    torso_w = h * 0.14

    p.setBrush(QBrush(C_LAVENDER))
    p.setPen(QPen(C_SURFACE1, 1))
    p.drawEllipse(QPointF(0, -h * 0.45), head_r, head_r)
    p.setBrush(QBrush(QColor(137, 180, 250, 120)))
    p.drawEllipse(QPointF(0, -h * 0.45), head_r * 0.7, head_r * 0.7)

    torso_rect = QRectF(-torso_w / 2, -h * 0.35, torso_w, torso_h)
    p.setBrush(QBrush(C_SURFACE1))
    p.setPen(QPen(C_BLUE, 1))
    p.drawRoundedRect(torso_rect, 3, 3)
    p.setBrush(QBrush(C_BLUE))
    p.setPen(Qt.PenStyle.NoPen)
    p.drawRect(QRectF(-torso_w * 0.25, -h * 0.28, torso_w * 0.5, h * 0.07))

    arm_angle = math.radians(30 + 60 * phase)
    draw_arm(p, scale, arm_angle, left=True)
    draw_arm(p, scale, arm_angle, left=False)
    draw_legs(p, scale, phase)


def draw_arrowhead(
    p: QPainter,
    start: QPointF,
    tip: QPointF,
    color: QColor,
    size: float = 8,
) -> None:
    """Draw a filled arrowhead at *tip* pointing away from *start*."""
    dx = tip.x() - start.x()
    dy = tip.y() - start.y()
    length = math.hypot(dx, dy)
    if length < 1e-3:
        return
    ux, uy = dx / length, dy / length
    px, py = -uy, ux
    path = QPainterPath()
    path.moveTo(tip)
    half = size / 2
    path.lineTo(
        QPointF(tip.x() - ux * size + px * half, tip.y() - uy * size + py * half)
    )
    path.lineTo(
        QPointF(tip.x() - ux * size - px * half, tip.y() - uy * size - py * half)
    )
    path.closeSubpath()
    p.fillPath(path, QBrush(color))


def draw_stars(p: QPainter, width: int, height: int) -> None:
    """Scatter small white dots as background stars."""
    star_positions: list[tuple[float, float]] = [
        (i * 0.618033988 % 1.0, (i * 0.381966 % 1.0)) for i in range(200)
    ]
    p.save()
    for fx, fy in star_positions:
        sx, sy = fx * width, fy * height
        brightness = int(80 + 175 * ((fx * 7 + fy * 13) % 1.0))
        star_color = QColor(brightness, brightness, brightness, 200)
        p.setPen(QPen(star_color, 1.2))
        p.drawPoint(QPointF(sx, sy))
    p.restore()


def draw_hud_lines(ctrl: object) -> list[tuple[str, object]]:
    """Return HUD text lines as (text, colour) tuples using the controller state."""
    from asteroid_jumper.renderer_draw import C_BLUE, C_GREEN, C_SUBTEXT

    phase = ctrl.state.phase  # type: ignore[union-attr]
    sim_time = ctrl.state.time  # type: ignore[union-attr]
    raw = [
        f"Phase: {phase.upper()}",
        f"Time:  {sim_time:.2f} s",
        f"Jumper speed:   {ctrl.jumper_speed():.3f} m/s",  # type: ignore[union-attr]
        f"Jumper ω:       {ctrl.jumper_angular_speed():.3f} rad/s",  # type: ignore[union-attr]
        f"Asteroid speed: {ctrl.asteroid_speed():.3f} m/s",  # type: ignore[union-attr]
        f"Asteroid ω:     {ctrl.asteroid_angular_speed():.3f} rad/s",  # type: ignore[union-attr]
        f"Off-centre:     {ctrl.off_centre_fraction():.2%}",  # type: ignore[union-attr]
    ]
    if phase == "ready":
        raw.append("← Drag on asteroid to set jump angle")
    result = []
    for i, text in enumerate(raw):
        color = C_BLUE if i == 0 else (C_GREEN if i < 5 else C_SUBTEXT)
        result.append((text, color))
    return result


def draw_asteroid_body(
    p: QPainter,
    ast: RigidBody,
    shape: AsteroidShape,
    world_to_screen: object,
    scale: float,
) -> None:
    """Draw the asteroid polygon with gradient fill and COM marker."""
    p.save()
    path = QPainterPath()
    first = True
    for bx, by in shape.vertices:
        cos_a, sin_a = math.cos(ast.angle), math.sin(ast.angle)
        wx = bx * cos_a - by * sin_a + ast.pos.x
        wy = bx * sin_a + by * cos_a + ast.pos.y
        sp = world_to_screen(wx, wy)  # type: ignore[operator]
        if first:
            path.moveTo(sp)
            first = False
        else:
            path.lineTo(sp)
    path.closeSubpath()

    rock_center = world_to_screen(ast.pos.x, ast.pos.y)  # type: ignore[operator]
    rg = QRadialGradient(rock_center, scale * shape.semi_a * 1.1)
    rg.setColorAt(0.0, QColor("#6c5c4a"))
    rg.setColorAt(0.4, QColor("#4a3e32"))
    rg.setColorAt(1.0, QColor("#2a2320"))
    p.fillPath(path, rg)
    p.setPen(QPen(QColor("#8b7355"), 2))
    p.drawPath(path)

    com_sp = world_to_screen(ast.pos.x, ast.pos.y)  # type: ignore[operator]
    p.setPen(QPen(C_YELLOW, 1.5))
    p.setBrush(QBrush(C_YELLOW))
    p.drawEllipse(com_sp, 4, 4)
    p.restore()
