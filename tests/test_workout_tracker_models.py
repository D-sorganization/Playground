"""Tests for workout_tracker.models."""

from __future__ import annotations

import pytest

from workout_tracker.models import (
    VALID_STATUSES,
    Exercise,
    Workout,
    WorkoutSet,
    normalize_name,
)


class TestNormalizeName:
    def test_lowercases_and_strips_punctuation(self) -> None:
        assert normalize_name("Bench Press") == "benchpress"
        assert normalize_name("Pull-Ups!") == "pullups"
        assert normalize_name("  Squat  ") == "squat"

    def test_handles_unicode_alphanumerics_only(self) -> None:
        assert normalize_name("Romanian Deadlift") == "romaniandeadlift"

    def test_empty_input(self) -> None:
        assert normalize_name("") == ""
        assert normalize_name("   ") == ""


class TestExercise:
    def test_auto_normalizes(self) -> None:
        ex = Exercise(name="Bench Press")
        assert ex.normalized_name == "benchpress"

    def test_rejects_empty_name(self) -> None:
        with pytest.raises(ValueError):
            Exercise(name="   ")

    def test_to_dict_serializable(self) -> None:
        d = Exercise(name="Squat").to_dict()
        assert d["name"] == "Squat"
        assert d["normalized_name"] == "squat"

    def test_frozen(self) -> None:
        from dataclasses import FrozenInstanceError

        ex = Exercise(name="Squat")
        with pytest.raises(FrozenInstanceError):
            ex.name = "no"  # type: ignore[misc]


class TestWorkoutSet:
    def test_default_unit(self) -> None:
        s = WorkoutSet(workout_id=1, exercise_id=1, position=0)
        assert s.unit == "lbs"
        assert s.executed is False

    def test_invalid_unit(self) -> None:
        with pytest.raises(ValueError):
            WorkoutSet(workout_id=1, exercise_id=1, position=0, unit="stones")

    def test_position_none_is_allowed(self) -> None:
        s = WorkoutSet(workout_id=1, exercise_id=1, position=None)
        assert s.position is None

    def test_negative_reps_rejected(self) -> None:
        with pytest.raises(ValueError):
            WorkoutSet(
                workout_id=1, exercise_id=1, position=0, actual_reps=-3
            )

    def test_rpe_range(self) -> None:
        with pytest.raises(ValueError):
            WorkoutSet(workout_id=1, exercise_id=1, position=0, rpe=11.0)

    def test_to_dict_executed_is_bool(self) -> None:
        s = WorkoutSet(workout_id=1, exercise_id=1, position=0, executed=True)
        d = s.to_dict()
        assert d["executed"] is True


class TestWorkout:
    def test_status_validated(self) -> None:
        with pytest.raises(ValueError):
            Workout(date="2024-01-01", status="bogus")
        for s in VALID_STATUSES:
            Workout(date="2024-01-01", status=s)

    def test_invalid_date(self) -> None:
        with pytest.raises(ValueError):
            Workout(date="not-a-date")

    def test_to_dict_includes_sets(self) -> None:
        w = Workout(date="2024-05-01")
        w.sets.append(
            WorkoutSet(workout_id=1, exercise_id=1, position=0)
        )
        d = w.to_dict()
        assert isinstance(d["sets"], list)
        assert len(d["sets"]) == 1
