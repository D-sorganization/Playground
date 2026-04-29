"""Benchmarks for Workout Tracker hot paths."""

from __future__ import annotations

from typing import Any

import pytest

from workout_tracker.autocomplete import suggest
from workout_tracker.models import Exercise, WorkoutSet
from workout_tracker.parser import parse_notes
from workout_tracker.stats import (
    exercise_timeseries,
    frequency,
    overview,
    per_exercise_summary,
    personal_records,
)

EXERCISE_NAMES = (
    "Bench Press",
    "Back Squat",
    "Deadlift",
    "Overhead Press",
    "Bent-Over Row",
    "Pull-Up",
    "Front Squat",
    "Romanian Deadlift",
)


def _notes_fixture(repetitions: int = 75) -> str:
    blocks: list[str] = []
    for index in range(repetitions):
        name = EXERCISE_NAMES[index % len(EXERCISE_NAMES)]
        weight = 95 + (index % 12) * 10
        blocks.append(f"{name} 3x5 @ {weight}")
        blocks.append(f"{name}\n{weight}x5, {weight + 10}x3, {weight + 20}x1")
    return "\n".join(blocks)


def _exercise_catalog(size: int = 800) -> list[Exercise]:
    return [
        Exercise(
            id=index + 1,
            name=f"{EXERCISE_NAMES[index % len(EXERCISE_NAMES)]} Variation {index}",
            use_count=size - index,
        )
        for index in range(size)
    ]


def _workout_sets(size: int = 2400) -> list[WorkoutSet]:
    sets: list[WorkoutSet] = []
    for index in range(size):
        exercise_id = index % len(EXERCISE_NAMES) + 1
        sets.append(
            WorkoutSet(
                workout_id=index // 8 + 1,
                exercise_id=exercise_id,
                position=index,
                actual_reps=3 + index % 8,
                actual_weight=95.0 + (index % 20) * 5,
                rpe=6.0 + (index % 5) * 0.5,
                executed=True,
                completed_at=f"2024-05-{index % 28 + 1:02d}T08:00:00",
                exercise_name=EXERCISE_NAMES[exercise_id - 1],
            )
        )
    return sets


@pytest.mark.benchmark(group="workout-parser")
def test_benchmark_parse_large_workout_notes(benchmark: Any) -> None:
    notes = _notes_fixture()

    parsed = benchmark(parse_notes, notes)

    assert len(parsed) == 150
    assert sum(len(entry.sets) for entry in parsed) == 450


@pytest.mark.benchmark(group="workout-autocomplete")
def test_benchmark_fuzzy_autocomplete_large_catalog(benchmark: Any) -> None:
    catalog = _exercise_catalog()

    results = benchmark(suggest, "bnech press variation 120", catalog, 8)

    assert results
    assert any(result.name.startswith("Bench Press") for result in results)


@pytest.mark.benchmark(group="workout-stats")
def test_benchmark_workout_stats_rollups(benchmark: Any) -> None:
    workout_sets = _workout_sets()

    def calculate_rollups() -> tuple[int, int, int, int, int]:
        return (
            len(per_exercise_summary(workout_sets)),
            len(exercise_timeseries(workout_sets)),
            len(personal_records(workout_sets)),
            len(frequency(workout_sets, today="2024-06-15")),
            overview(workout_sets).total_sets,
        )

    summary_count, point_count, pr_count, frequency_count, total_sets = benchmark(
        calculate_rollups
    )

    assert summary_count == len(EXERCISE_NAMES)
    assert point_count == 28
    assert pr_count == len(EXERCISE_NAMES) * 3
    assert frequency_count == len(EXERCISE_NAMES)
    assert total_sets == len(workout_sets)
