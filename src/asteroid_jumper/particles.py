"""Particle and trail-buffer system for the asteroid-jumper renderer.

Manages collections of positional samples that fade over time and are
rendered as smooth trails by the draw helpers.  The trail abstraction is
modelled as a fixed-capacity ring buffer of world-space (x, y) samples.
"""

from __future__ import annotations

MAX_TRAIL_LENGTH: int = 120  # default maximum trail points


class TrailBuffer:
    """Fixed-capacity FIFO buffer of world-space (x, y) positions.

    Older positions are discarded once the buffer is full.

    Attributes:
        capacity: Maximum number of points retained.

    Example::

        trail = TrailBuffer(capacity=10)
        trail.append(1.0, 2.0)
        trail.append(3.0, 4.0)
        points = trail.points  # [(1.0, 2.0), (3.0, 4.0)]
    """

    def __init__(self, capacity: int = MAX_TRAIL_LENGTH) -> None:
        """Initialise with a given capacity.

        Args:
            capacity: Maximum number of (x, y) samples retained (must be > 0).

        Raises:
            ValueError: If capacity is not a positive integer.
        """
        if not (isinstance(capacity, int) and capacity > 0):
            raise ValueError(
                f"TrailBuffer capacity must be a positive integer, got {capacity!r}"
            )
        self._capacity = capacity
        self._points: list[tuple[float, float]] = []

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def capacity(self) -> int:
        """Maximum number of points this buffer retains."""
        return self._capacity

    @property
    def points(self) -> list[tuple[float, float]]:
        """Snapshot of buffered (x, y) world-space positions (oldest first)."""
        return list(self._points)

    def __len__(self) -> int:
        return len(self._points)

    # ------------------------------------------------------------------
    # Mutation
    # ------------------------------------------------------------------

    def append(self, x: float, y: float) -> None:
        """Append a world-space position sample.

        Evicts the oldest sample when the buffer is at capacity.

        Args:
            x: World X coordinate in metres.
            y: World Y coordinate in metres.
        """
        if len(self._points) >= self._capacity:
            self._points.pop(0)
        self._points.append((x, y))

    def clear(self) -> None:
        """Remove all buffered positions."""
        self._points.clear()
