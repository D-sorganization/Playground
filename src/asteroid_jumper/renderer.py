"""Simulation renderer widget — PyQt6 QPainter-based canvas.

Draws with Catppuccin Mocha colour palette to match Tools repo theme.
Animation runs via QTimer.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from PyQt6.QtCore import QPointF, QRectF, Qt, QTimer
from PyQt6.QtGui import (
    QColor,
    QFont,
    QLinearGradient,
    QPainter,
    QPen,
)
from PyQt6.QtWidgets import QSizePolicy, QWidget

from asteroid_jumper.renderer_draw import (
    C_CRUST,
    C_MANTLE,
    C_PEACH,
    C_SURFACE1,
    C_TEAL,
    C_YELLOW,
    draw_arrowhead,
    draw_asteroid_body,
    draw_craters,
    draw_hud_lines,
    draw_jumper_body,
    draw_stars,
)

if TYPE_CHECKING:
    from asteroid_jumper.controller import SimController

FPS = 60
SIM_SPEED = 1.0
VIEWPORT_SCALE = 25.0
TRAIL_LENGTH = 120


class AsteroidJumperRenderer(QWidget):
    """Interactive PyQt6 canvas rendering the asteroid-jumper simulation."""

    def __init__(
        self, controller: SimController, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        if not (controller is not None):
            raise ValueError("controller must not be None")
        self._ctrl = controller
        self._scale = VIEWPORT_SCALE
        self._pan = QPointF(0.0, 0.0)
        self._running = False
        self._asteroid_trail: list[tuple[float, float]] = []
        self._jumper_trail: list[tuple[float, float]] = []
        self._force_angle_drag = False
        self._force_angle_screen: QPointF | None = None
        self.force_angle_changed = _SimpleSignal()

        self.setMinimumSize(600, 500)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.setMouseTracking(True)

        self._timer = QTimer(self)
        self._timer.setInterval(1000 // FPS)
        self._timer.timeout.connect(self._on_tick)

    def start_animation(self) -> None:
        """Start or resume the animation timer."""
        self._running = True
        self._timer.start()

    def stop_animation(self) -> None:
        """Pause the animation timer."""
        self._running = False
        self._timer.stop()

    def reset_view(self) -> None:
        """Centre the view and clear trails."""
        self._pan = QPointF(0.0, 0.0)
        self._scale = VIEWPORT_SCALE
        self._asteroid_trail.clear()
        self._jumper_trail.clear()
        self.update()

    def set_scale(self, scale: float) -> None:
        """Set zoom level (pixels per metre)."""
        if not (scale > 0):
            raise ValueError("DbC Blocked: Precondition failed.")
        self._scale = scale
        self.update()

    def _world_to_screen(self, wx: float, wy: float) -> QPointF:
        """World (m) → screen (px), y-flipped for Qt."""
        cx = self.width() / 2 + self._pan.x()
        cy = self.height() / 2 + self._pan.y()
        return QPointF(cx + wx * self._scale, cy - wy * self._scale)

    def _screen_to_world(self, sx: float, sy: float) -> tuple[float, float]:
        """Screen (px) → world (m)."""
        cx = self.width() / 2 + self._pan.x()
        cy = self.height() / 2 + self._pan.y()
        return (sx - cx) / self._scale, -(sy - cy) / self._scale

    def paintEvent(self, _event: object) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        self._draw_background(painter)
        self._draw_stars(painter)
        if self._ctrl.state.phase != "ready":
            self._draw_trails(painter)
        self._draw_force_indicator(painter)
        self._draw_asteroid(painter)
        self._draw_jumper(painter)
        self._draw_hud(painter)
        painter.end()

    def mousePressEvent(self, event: object) -> None:  # noqa: N802
        from PyQt6.QtGui import QMouseEvent

        if isinstance(event, QMouseEvent):
            if event.button() == Qt.MouseButton.LeftButton:
                self._force_angle_drag = True
                self._update_force_from_mouse(event.position())
            elif event.button() == Qt.MouseButton.RightButton:
                self._pan_start = event.position()

    def mouseMoveEvent(self, event: object) -> None:  # noqa: N802
        from PyQt6.QtGui import QMouseEvent

        if isinstance(event, QMouseEvent):
            if self._force_angle_drag and event.buttons() == Qt.MouseButton.LeftButton:
                self._update_force_from_mouse(event.position())
                self.update()

    def mouseReleaseEvent(self, event: object) -> None:  # noqa: N802
        self._force_angle_drag = False

    def wheelEvent(self, event: object) -> None:  # noqa: N802
        from PyQt6.QtGui import QWheelEvent

        if isinstance(event, QWheelEvent):
            delta = event.angleDelta().y()
            factor = 1.1 if delta > 0 else 0.9
            self._scale = max(5.0, min(200.0, self._scale * factor))
            self.update()

    def _update_force_from_mouse(self, pos: QPointF) -> None:
        """Set force angle based on mouse position relative to asteroid."""
        ast = self._ctrl.state.asteroid
        asteroid_screen = self._world_to_screen(ast.pos.x, ast.pos.y)
        dx = pos.x() - asteroid_screen.x()
        dy = -(pos.y() - asteroid_screen.y())
        angle_deg = math.degrees(math.atan2(dy, dx))
        self._ctrl.set_force_angle(angle_deg)
        self._ctrl.set_jump_direction(angle_deg)
        self._ctrl.state = self._ctrl._build_state()
        self.force_angle_changed.emit(angle_deg)
        self.update()

    def _on_tick(self) -> None:
        if not self._running:
            return
        dt = SIM_SPEED / FPS
        if self._ctrl.state.phase in ("jumping", "flight"):
            ast = self._ctrl.state.asteroid
            jmp = self._ctrl.state.jumper
            self._asteroid_trail.append((ast.pos.x, ast.pos.y))
            self._jumper_trail.append((jmp.pos.x, jmp.pos.y))
            if len(self._asteroid_trail) > TRAIL_LENGTH:
                self._asteroid_trail.pop(0)
            if len(self._jumper_trail) > TRAIL_LENGTH:
                self._jumper_trail.pop(0)
            self._ctrl.tick(dt)
        self.update()

    def _draw_background(self, p: QPainter) -> None:
        """Fill with deep-space gradient."""
        grad = QLinearGradient(0, 0, 0, self.height())
        grad.setColorAt(0.0, C_CRUST)
        grad.setColorAt(1.0, C_MANTLE)
        p.fillRect(self.rect(), grad)

    def _draw_stars(self, p: QPainter) -> None:
        """Scatter small white dots as background stars."""
        draw_stars(p, self.width(), self.height())

    def _draw_trails(self, p: QPainter) -> None:
        """Draw position trails for asteroid and jumper."""
        self._draw_single_trail(p, self._asteroid_trail, C_TEAL)
        self._draw_single_trail(p, self._jumper_trail, C_PEACH)

    def _draw_single_trail(
        self, p: QPainter, trail: list[tuple[float, float]], color: QColor
    ) -> None:
        """Draw a single fading trail."""
        if len(trail) < 2:
            return
        p.save()
        for i in range(len(trail) - 1):
            alpha = int(20 + 200 * i / len(trail))
            pen_color = QColor(color)
            pen_color.setAlpha(alpha)
            p.setPen(QPen(pen_color, 1.5))
            a = self._world_to_screen(*trail[i])
            b = self._world_to_screen(*trail[i + 1])
            p.drawLine(a, b)
        p.restore()

    def _draw_asteroid(self, p: QPainter) -> None:
        """Draw the asteroid as a textured polygon."""
        ast = self._ctrl.state.asteroid
        shape = self._ctrl.shape
        draw_asteroid_body(p, ast, shape, self._world_to_screen, self._scale)
        draw_craters(p, ast, shape, self._world_to_screen, self._scale)

    def _draw_jumper(self, p: QPainter) -> None:
        """Draw the astronaut-style jumper with animated legs."""
        jmp = self._ctrl.state.jumper
        phase = self._ctrl.leg_phase()
        p.save()
        sp = self._world_to_screen(jmp.pos.x, jmp.pos.y)
        angle = jmp.angle
        p.translate(sp)
        p.rotate(-math.degrees(angle))
        draw_jumper_body(p, self._scale, phase)
        p.restore()

    def _draw_force_indicator(self, p: QPainter) -> None:
        """Draw the adjustable force vector arrow on the asteroid."""
        if self._ctrl.state.phase != "ready":
            return
        ast = self._ctrl.state.asteroid
        shape = self._ctrl.shape
        angle_rad = math.radians(self._ctrl.force_angle_deg)
        from asteroid_jumper.asteroid_shape import surface_point_at_angle

        sx, sy = surface_point_at_angle(shape, angle_rad)
        contact_screen = self._world_to_screen(sx + ast.pos.x, sy + ast.pos.y)
        arrow_len = self._scale * 4
        dir_x = math.cos(angle_rad)
        dir_y = -math.sin(angle_rad)
        tip = QPointF(
            contact_screen.x() + dir_x * arrow_len,
            contact_screen.y() + dir_y * arrow_len,
        )
        p.save()
        p.setPen(QPen(C_YELLOW, 2.5, Qt.PenStyle.SolidLine))
        p.drawLine(contact_screen, tip)
        draw_arrowhead(p, contact_screen, tip, C_YELLOW, size=8)
        p.setPen(QPen(C_YELLOW))
        p.setFont(QFont("monospace", 9))
        p.drawText(QPointF(tip.x() + 5, tip.y() - 5), "Jump")
        p.restore()

    def _draw_hud(self, p: QPainter) -> None:
        """Draw HUD overlay with key metrics."""
        p.save()
        p.setFont(QFont("monospace", 9))
        hud_lines = draw_hud_lines(self._ctrl)
        bg = QColor(C_MANTLE)
        bg.setAlpha(200)
        row_h, margin, box_w = 16, 8, 240
        box_h = row_h * len(hud_lines) + margin * 2
        p.fillRect(QRectF(8, 8, box_w, box_h), bg)
        p.setPen(QPen(C_SURFACE1, 1))
        p.drawRect(QRectF(8, 8, box_w, box_h))
        for i, (text, color) in enumerate(hud_lines):
            p.setPen(QPen(color))
            p.drawText(QPointF(margin + 8, margin + 8 + (i + 1) * row_h - 3), text)
        p.restore()


class _SimpleSignal:
    """Lightweight callable signal (wraps a list of callbacks)."""

    def __init__(self) -> None:
        from collections.abc import Callable

        self._slots: list[Callable[..., object]] = []

    def connect(self, slot: object) -> None:
        if not (callable(slot)):
            raise ValueError("DbC Blocked: Precondition failed.")
        self._slots.append(slot)

    def emit(self, *args: object) -> None:
        for slot in self._slots:
            slot(*args)
