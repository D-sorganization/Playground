"""Tests for workout_tracker.stats."""

from __future__ import annotations

import pytest

from workout_tracker.models import WorkoutSet
from workout_tracker.stats import (
    best_1rm_estimate,
    brzycki_1rm,
    epley_1rm,
    exercise_timeseries,
    frequency,
    overview,
    per_exercise_summary,
    personal_records,
    set_volume,
    total_volume,
)


def _s(
    *,
    ex_id: int = 1,
    ex_name: str = "Bench Press",
    reps: int = 5,
    weight: float = 135.0,
    rpe: float | None = None,
    executed: bool = True,
    completed_at: str | None = "2024-05-01T10:00:00",
    workout_id: int = 1,
    pos: int = 0,
) -> WorkoutSet:
    return WorkoutSet(
        workout_id=workout_id,
        exercise_id=ex_id,
        position=pos,
        actual_reps=reps,
        actual_weight=weight,
        rpe=rpe,
        executed=executed,
        completed_at=completed_at,
        exercise_name=ex_name,
    )


class TestOneRepMax:
    def test_epley_1rm(self) -> None:
        assert epley_1rm(135, 1) == 135.0
        assert epley_1rm(135, 5) == pytest.approx(157.5)

    def test_brzycki_1rm(self) -> None:
        assert brzycki_1rm(135, 1) == pytest.approx(135.0)
        assert brzycki_1rm(135, 5) == pytest.approx(151.875)

    def test_best_1rm_combines(self) -> None:
        r = best_1rm_estimate(135, 5)
        e = epley_1rm(135, 5)
        b = brzycki_1rm(135, 5)
        assert r == pytest.approx((e + b) / 2)

    def test_brzycki_diverges(self) -> None:
        with pytest.raises(ValueError):
            brzycki_1rm(135, 37)

    def test_negative_inputs_rejected(self) -> None:
        with pytest.raises(ValueError):
            epley_1rm(-10, 5)
        with pytest.raises(ValueError):
            epley_1rm(10, 0)


class TestVolume:
    def test_set_volume_executed(self) -> None:
        assert set_volume(_s(reps=5, weight=100)) == 500.0

    def test_set_volume_not_executed_is_zero(self) -> None:
        assert set_volume(_s(executed=False)) == 0.0

    def test_total_volume(self) -> None:
        sets = [_s(reps=5, weight=100), _s(reps=3, weight=200)]
        assert total_volume(sets) == 5 * 100 + 3 * 200


class TestPerExerciseSummary:
    def test_aggregates(self) -> None:
        sets = [
            _s(reps=5, weight=100),
            _s(reps=3, weight=150),
            _s(reps=8, weight=80, ex_id=2, ex_name="Row"),
        ]
        out = per_exercise_summary(sets)
        by_name = {s.exercise_name: s for s in out}
        assert by_name["Bench Press"].total_sets == 2
        assert by_name["Bench Press"].max_weight == 150
        assert by_name["Row"].total_sets == 1
        # sorted by volume desc -- Bench has 500+450=950 vol vs Row 640
        assert out[0].exercise_name == "Bench Press"

    def test_ignores_non_executed(self) -> None:
        sets = [_s(executed=False)]
        assert per_exercise_summary(sets) == []


class TestTimeseries:
    def test_groups_per_day(self) -> None:
        sets = [
            _s(completed_at="2024-05-01T08:00:00", reps=5, weight=100),
            _s(completed_at="2024-05-01T09:00:00", reps=3, weight=110),
            _s(completed_at="2024-05-03T08:00:00", reps=5, weight=120),
        ]
        pts = exercise_timeseries(sets)
        assert [p.date for p in pts] == ["2024-05-01", "2024-05-03"]
        assert pts[0].sets == 2
        assert pts[0].volume == 5 * 100 + 3 * 110


class TestPRs:
    def test_three_axes(self) -> None:
        sets = [
            _s(reps=5, weight=100, completed_at="2024-05-01T08:00:00"),
            _s(reps=8, weight=90, completed_at="2024-05-05T08:00:00"),
            _s(reps=3, weight=150, completed_at="2024-05-10T08:00:00"),
        ]
        prs = personal_records(sets)
        metrics = {p.metric: p for p in prs}
        assert metrics["max_weight"].weight == 150
        assert metrics["max_reps"].reps == 8
        assert metrics["best_e1rm"].value == pytest.approx(
            best_1rm_estimate(150, 3)
        )


class TestFrequency:
    def test_sessions_and_days_since(self) -> None:
        sets = [
            _s(completed_at="2024-05-01T08:00:00"),
            _s(completed_at="2024-05-05T08:00:00"),
            _s(completed_at="2024-05-05T08:10:00"),  # same day
        ]
        out = frequency(sets, today="2024-05-10")
        assert out[0].sessions == 2
        assert out[0].days_since_last == 5


class TestOverview:
    def test_counts(self) -> None:
        sets = [
            _s(workout_id=1, reps=5, weight=100),
            _s(workout_id=1, reps=5, weight=100, pos=1),
            _s(workout_id=2, reps=3, weight=200, ex_id=2, ex_name="Dead"),
        ]
        ov = overview(sets)
        assert ov.total_workouts == 2
        assert ov.total_sets == 3
        assert ov.distinct_exercises == 2
        assert ov.total_volume == 5 * 100 + 5 * 100 + 3 * 200
