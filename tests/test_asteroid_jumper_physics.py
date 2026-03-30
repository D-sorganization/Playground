import pytest

from src.asteroid_jumper.physics import Vec2


def test_vec2_addition():
    v1 = Vec2(1.0, 2.0)
    v2 = Vec2(3.0, 4.0)
    v3 = v1 + v2
    assert v3.x == 4.0
    assert v3.y == 6.0


def test_vec2_subtraction():
    v1 = Vec2(5.0, 5.0)
    v2 = Vec2(3.0, 2.0)
    v3 = v1 - v2
    assert v3.x == 2.0
    assert v3.y == 3.0


def test_vec2_multiplication():
    v1 = Vec2(2.0, 3.0)
    v3 = v1 * 2
    assert v3.x == 4.0
    assert v3.y == 6.0


def test_vec2_invalid_addition():
    v1 = Vec2(1.0, 1.0)
    with pytest.raises(ValueError):
        _ = v1 + 5.0
