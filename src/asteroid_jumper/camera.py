"""Viewport camera helper for the asteroid-jumper simulation.

Manages the world-to-screen coordinate transform, zoom, and pan state.
"""

from __future__ import annotations

from PyQt6.QtCore import QPointF

VIEWPORT_SCALE_DEFAULT = 25.0  # pixels per simulation metre (initial)


class Camera:
    """Encapsulates viewport transform: pan and zoom.

    Attributes:
        scale: Zoom level in pixels per simulation metre.
        pan: Pan offset in screen pixels as a QPointF.
    """

    def __init__(self, scale: float = VIEWPORT_SCALE_DEFAULT) -> None:
        assert scale > 0, "scale must be positive"
        self.scale = scale
        self.pan = QPointF(0.0, 0.0)

    def reset(self) -> None:
        """Reset pan to origin and scale to default."""
        self.pan = QPointF(0.0, 0.0)
        self.scale = VIEWPORT_SCALE_DEFAULT

    def set_scale(self, scale: float) -> None:
        """Set zoom level.

        Args:
            scale: Pixels per simulation metre (must be > 0).
        """
        assert scale > 0, "scale must be positive"
        self.scale = scale

    def zoom(
        self, factor: float, min_scale: float = 5.0, max_scale: float = 200.0
    ) -> None:
        """Apply a multiplicative zoom factor clamped to [min_scale, max_scale].

        Args:
            factor: Multiplicative zoom factor (> 1 zooms in, < 1 zooms out).
            min_scale: Lower bound for scale.
            max_scale: Upper bound for scale.
        """
        assert factor > 0, "factor must be positive"
        self.scale = max(min_scale, min(max_scale, self.scale * factor))

    def world_to_screen(self, wx: float, wy: float, width: int, height: int) -> QPointF:
        """Convert world-space coordinates to screen pixels.

        Args:
            wx: World X in metres.
            wy: World Y in metres.
            width: Viewport width in pixels.
            height: Viewport height in pixels.

        Returns:
            Screen-space QPointF (y-flipped for Qt coordinate system).
        """
        cx = width / 2 + self.pan.x()
        cy = height / 2 + self.pan.y()
        return QPointF(cx + wx * self.scale, cy - wy * self.scale)

    def screen_to_world(
        self, sx: float, sy: float, width: int, height: int
    ) -> tuple[float, float]:
        """Convert screen pixels to world-space coordinates.

        Args:
            sx: Screen X in pixels.
            sy: Screen Y in pixels.
            width: Viewport width in pixels.
            height: Viewport height in pixels.

        Returns:
            (wx, wy) world coordinates in metres.
        """
        cx = width / 2 + self.pan.x()
        cy = height / 2 + self.pan.y()
        return (sx - cx) / self.scale, -(sy - cy) / self.scale
