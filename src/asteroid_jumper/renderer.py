"""Simulation renderer widget — PyQt6 QPainter-based canvas.

Draws with Catppuccin Mocha colour palette to match Tools repo theme.
Animation runs via QTimer.

Drawing primitives live in :mod:`draw_helpers`.
Camera/viewport maths live in :mod:`camera`.
"""

from __future__ import annotations

import math
from typing import TYPE_CHECKING

from PyQt6.QtCore import QPointF, Qt, QTimer
from PyQt6.QtGui import QMouseEvent, QPainter, QPen, QWheelEvent
from PyQt6.QtWidgets import QSizePolicy, QWidget

from asteroid_jumper.camera import Camera
from asteroid_jumper.draw_helpers import (
    C_YELLOW,
    build_hud_lines,
    draw_arrowhead,
    draw_asteroid,
    draw_background,
    draw_hud_overlay,
    draw_jumper_body,
    draw_single_trail,
    draw_stars,
)

if TYPE_CHECKING:
    from asteroid_jumper.controller import SimController

FPS = 60
SIM_SPEED = 1.0  # simulation seconds per real second
TRAIL_LENGTH = 120  # max trail points stored

# Re-export colour palette for any code that imports from renderer.py
from asteroid_jumper.draw_helpers import (  # noqa: E402, F401
    C_BASE,
    C_BLUE,
    C_CRUST,
    C_FLAMINGO,
    C_GREEN,
    C_LAVENDER,
    C_MANTLE,
    C_MAUVE,
    C_PEACH,
    C_RED,
    C_SKY,
    C_SUBTEXT,
    C_SURFACE0,
    C_SURFACE1,
    C_TEAL,
    C_TEXT,
    STAR_POSITIONS,
)


class AsteroidJumperRenderer(QWidget):
    """Interactive PyQt6 canvas rendering the asteroid-jumper simulation."""

    def __init__(
        self, controller: SimController, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        if not (controller is not None):
            raise ValueError("controller must not be None")
        self._ctrl = controller
        self._camera = Camera()
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

    # ------------------------------------------------------------------
    # Public API (called by main window)
    # ------------------------------------------------------------------

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
        self._camera.reset()
        self._asteroid_trail.clear()
        self._jumper_trail.clear()
        self.update()

    def set_scale(self, scale: float) -> None:
        """Set zoom level (pixels per metre)."""
        self._camera.set_scale(scale)
        self.update()

    # ------------------------------------------------------------------
    # Coordinate helpers (delegates to Camera)
    # ------------------------------------------------------------------

    def _world_to_screen(self, wx: float, wy: float) -> QPointF:
        """World (m) → screen (px), y-flipped for Qt."""
        return self._camera.world_to_screen(wx, wy, self.width(), self.height())

    def _screen_to_world(self, sx: float, sy: float) -> tuple[float, float]:
        """Screen (px) → world (m)."""
        return self._camera.screen_to_world(sx, sy, self.width(), self.height())

    # ------------------------------------------------------------------
    # Qt event overrides
    # ------------------------------------------------------------------

    def paintEvent(self, _event: object) -> None:  # noqa: N802
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        draw_background(painter, self.width(), self.height())
        draw_stars(painter, self.width(), self.height())
        if self._ctrl.state.phase != "ready":
            self._draw_trails(painter)
        self._draw_force_indicator(painter)
        self._draw_asteroid(painter)
        self._draw_jumper(painter)
        self._draw_hud(painter)
        painter.end()

    def mousePressEvent(self, event: object) -> None:  # noqa: N802
        if isinstance(event, QMouseEvent):
            if event.button() == Qt.MouseButton.LeftButton:
                self._force_angle_drag = True
                self._update_force_from_mouse(event.position())
            elif event.button() == Qt.MouseButton.RightButton:
                self._pan_start = event.position()

    def mouseMoveEvent(self, event: object) -> None:  # noqa: N802
        if isinstance(event, QMouseEvent):
            if self._force_angle_drag and event.buttons() == Qt.MouseButton.LeftButton:
                self._update_force_from_mouse(event.position())
                self.update()

    def mouseReleaseEvent(self, event: object) -> None:  # noqa: N802
        self._force_angle_drag = False

    def wheelEvent(self, event: object) -> None:  # noqa: N802
        if isinstance(event, QWheelEvent):
            delta = event.angleDelta().y()
            factor = 1.1 if delta > 0 else 0.9
            self._camera.zoom(factor)
            self.update()

    # ------------------------------------------------------------------
    # Interaction helpers
    # ------------------------------------------------------------------

    def _update_force_from_mouse(self, pos: QPointF) -> None:
        """Set force angle based on mouse position relative to asteroid."""
        ast = self._ctrl.state.asteroid
        asteroid_screen = self._world_to_screen(ast.pos.x, ast.pos.y)
        dx = pos.x() - asteroid_screen.x()
        dy = -(pos.y() - asteroid_screen.y())  # flip y
        angle_deg = math.degrees(math.atan2(dy, dx))
        self._ctrl.set_force_angle(angle_deg)
        self._ctrl.set_jump_direction(angle_deg)
        self._ctrl.state = self._ctrl._build_state()
        self.force_angle_changed.emit(angle_deg)
        self.update()

    # ------------------------------------------------------------------
    # Animation tick
    # ------------------------------------------------------------------

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

    # ------------------------------------------------------------------
    # Drawing methods (thin wrappers around draw_helpers functions)
    # ------------------------------------------------------------------

    def _draw_trails(self, p: QPainter) -> None:
        """Draw position trails for asteroid and jumper."""
        draw_single_trail(p, self._asteroid_trail, C_TEAL, self._world_to_screen)
        draw_single_trail(p, self._jumper_trail, C_PEACH, self._world_to_screen)

    def _draw_asteroid(self, p: QPainter) -> None:
        """Draw the asteroid polygon."""
        draw_asteroid(
            p,
            self._ctrl.state.asteroid,
            self._ctrl.shape,
            self._camera.scale,
            self._world_to_screen,
        )

    def _draw_jumper(self, p: QPainter) -> None:
        """Draw the astronaut-style jumper with animated legs."""
        jmp = self._ctrl.state.jumper
        phase = self._ctrl.leg_phase()
        p.save()
        sp = self._world_to_screen(jmp.pos.x, jmp.pos.y)
        p.translate(sp)
        p.rotate(-math.degrees(jmp.angle))
        draw_jumper_body(p, self._camera.scale, phase)
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
        arrow_len = self._camera.scale * 4
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
        from PyQt6.QtGui import QFont

        p.setPen(QPen(C_YELLOW))
        p.setFont(QFont("monospace", 9))
        p.drawText(QPointF(tip.x() + 5, tip.y() - 5), "Jump")
        p.restore()

    def _draw_hud(self, p: QPainter) -> None:
        """Draw HUD overlay with key metrics."""
        lines = build_hud_lines(
            self._ctrl.state.phase, self._ctrl.state.time, self._ctrl
        )
        draw_hud_overlay(p, lines, self.width(), self.height())


# ---------------------------------------------------------------------------
# Mini signal helper
# ---------------------------------------------------------------------------


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
