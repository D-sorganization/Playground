"""Tests for asteroid_jumper.particles — TrailBuffer particle system."""

from __future__ import annotations

import pytest

from src.asteroid_jumper.particles import MAX_TRAIL_LENGTH, TrailBuffer

# ---------------------------------------------------------------------------
# Construction and defaults
# ---------------------------------------------------------------------------


def test_trail_buffer_default_capacity():
    """Default capacity equals MAX_TRAIL_LENGTH."""
    buf = TrailBuffer()
    assert buf.capacity == MAX_TRAIL_LENGTH


def test_trail_buffer_custom_capacity():
    """Custom capacity is stored correctly."""
    buf = TrailBuffer(capacity=10)
    assert buf.capacity == 10


def test_trail_buffer_invalid_capacity_zero():
    """Zero capacity raises ValueError."""
    with pytest.raises(ValueError, match="positive integer"):
        TrailBuffer(capacity=0)


def test_trail_buffer_invalid_capacity_negative():
    """Negative capacity raises ValueError."""
    with pytest.raises(ValueError, match="positive integer"):
        TrailBuffer(capacity=-5)


def test_trail_buffer_invalid_capacity_float():
    """Float capacity raises ValueError."""
    with pytest.raises(ValueError, match="positive integer"):
        TrailBuffer(capacity=3.5)  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Appending and reading
# ---------------------------------------------------------------------------


def test_trail_buffer_starts_empty():
    """Newly created buffer has no points."""
    buf = TrailBuffer(capacity=5)
    assert len(buf) == 0
    assert buf.points == []


def test_trail_buffer_append_single():
    """Single append produces one point."""
    buf = TrailBuffer(capacity=5)
    buf.append(1.0, 2.0)
    assert len(buf) == 1
    assert buf.points == [(1.0, 2.0)]


def test_trail_buffer_append_multiple():
    """Multiple appends are stored in insertion order."""
    buf = TrailBuffer(capacity=5)
    buf.append(0.0, 0.0)
    buf.append(1.0, 1.0)
    buf.append(2.0, 2.0)
    assert buf.points == [(0.0, 0.0), (1.0, 1.0), (2.0, 2.0)]


def test_trail_buffer_evicts_oldest_when_full():
    """When buffer is full, the oldest point is evicted on next append."""
    buf = TrailBuffer(capacity=3)
    buf.append(0.0, 0.0)
    buf.append(1.0, 1.0)
    buf.append(2.0, 2.0)
    buf.append(3.0, 3.0)  # should evict (0, 0)
    assert buf.points == [(1.0, 1.0), (2.0, 2.0), (3.0, 3.0)]
    assert len(buf) == 3


def test_trail_buffer_never_exceeds_capacity():
    """Buffer length never exceeds its capacity after many appends."""
    cap = 10
    buf = TrailBuffer(capacity=cap)
    for i in range(100):
        buf.append(float(i), float(i))
    assert len(buf) == cap


def test_trail_buffer_points_returns_snapshot():
    """points property returns a copy — mutating it does not affect the buffer."""
    buf = TrailBuffer(capacity=5)
    buf.append(1.0, 2.0)
    snapshot = buf.points
    snapshot.append((99.0, 99.0))
    assert len(buf) == 1


# ---------------------------------------------------------------------------
# clear()
# ---------------------------------------------------------------------------


def test_trail_buffer_clear_empties_buffer():
    """clear() removes all stored points."""
    buf = TrailBuffer(capacity=5)
    buf.append(1.0, 2.0)
    buf.append(3.0, 4.0)
    buf.clear()
    assert len(buf) == 0
    assert buf.points == []


def test_trail_buffer_append_after_clear():
    """Buffer works correctly after clear() is called."""
    buf = TrailBuffer(capacity=5)
    buf.append(0.0, 0.0)
    buf.clear()
    buf.append(5.0, 6.0)
    assert buf.points == [(5.0, 6.0)]


# ---------------------------------------------------------------------------
# __len__
# ---------------------------------------------------------------------------


def test_trail_buffer_len_reflects_appends():
    """len() grows with each append up to capacity."""
    buf = TrailBuffer(capacity=4)
    assert len(buf) == 0
    buf.append(0.0, 0.0)
    assert len(buf) == 1
    buf.append(1.0, 1.0)
    assert len(buf) == 2
