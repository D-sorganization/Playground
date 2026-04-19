"""Tests for workout_tracker.db (repository layer)."""

from __future__ import annotations

import pytest

from workout_tracker.db import WorkoutRepository, connect, init_db
from workout_tracker.models import WorkoutSet


@pytest.fixture()
def repo() -> WorkoutRepository:
    conn = connect(":memory:")
    init_db(conn)
    return WorkoutRepository(conn)


class TestExerciseRepo:
    def test_create_and_get(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Bench Press")
        assert ex.id is not None
        assert ex.name == "Bench Press"

    def test_idempotent_across_typo_variants(self, repo: WorkoutRepository) -> None:
        a = repo.get_or_create_exercise("Bench Press")
        b = repo.get_or_create_exercise("bench press")
        c = repo.get_or_create_exercise("Bench-Press")
        assert a.id == b.id == c.id

    def test_rejects_empty(self, repo: WorkoutRepository) -> None:
        with pytest.raises(ValueError):
            repo.get_or_create_exercise("   ")

    def test_list_sorted_by_use_count(self, repo: WorkoutRepository) -> None:
        repo.get_or_create_exercise("A")
        b = repo.get_or_create_exercise("B")
        w = repo.create_workout(date="2024-05-01", status="in_progress")
        repo.add_set(
            WorkoutSet(
                workout_id=w.id or 0,
                exercise_id=b.id or 0,
                position=0,
                actual_reps=5,
                actual_weight=100,
                executed=True,
            )
        )
        listed = repo.list_exercises()
        assert listed[0].name == "B"
        assert listed[1].name == "A"

    def test_rename(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Bnech Press")
        renamed = repo.rename_exercise(ex.id or 0, "Bench Press")
        assert renamed.name == "Bench Press"
        assert renamed.normalized_name == "benchpress"

    def test_merge_moves_sets_and_deletes_source(self, repo: WorkoutRepository) -> None:
        a = repo.get_or_create_exercise("Bench")
        b = repo.get_or_create_exercise("Bench Press")
        w = repo.create_workout(date="2024-05-01", status="in_progress")
        s = repo.add_set(
            WorkoutSet(
                workout_id=w.id or 0,
                exercise_id=a.id or 0,
                position=0,
                actual_reps=5,
                actual_weight=100,
                executed=True,
            )
        )
        repo.merge_exercise(a.id or 0, b.id or 0)
        refreshed = repo.get_set(s.id or 0)
        assert refreshed.exercise_id == b.id
        # source exercise gone
        names = [e.name for e in repo.list_exercises()]
        assert "Bench" not in names


class TestWorkoutRepo:
    def test_create_update_delete(self, repo: WorkoutRepository) -> None:
        w = repo.create_workout(date="2024-05-01", status="planned", title="Push")
        assert w.id is not None
        assert w.title == "Push"
        w2 = repo.update_workout(w.id, status="completed")
        assert w2.status == "completed"
        repo.delete_workout(w.id)
        with pytest.raises(KeyError):
            repo.get_workout(w.id)

    def test_list_in_date_desc(self, repo: WorkoutRepository) -> None:
        w1 = repo.create_workout(date="2024-01-01")
        w2 = repo.create_workout(date="2024-05-01")
        listed = repo.list_workouts()
        assert listed[0].id == w2.id
        assert listed[1].id == w1.id

    def test_delete_cascades_sets(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Squat")
        w = repo.create_workout(date="2024-05-01", status="in_progress")
        s = repo.add_set(
            WorkoutSet(
                workout_id=w.id or 0,
                exercise_id=ex.id or 0,
                position=0,
                actual_reps=5,
                actual_weight=100,
                executed=True,
            )
        )
        repo.delete_workout(w.id or 0)
        with pytest.raises(KeyError):
            repo.get_set(s.id or 0)


class TestSetsRepo:
    def test_add_and_auto_position(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Squat")
        w = repo.create_workout(date="2024-05-01", status="in_progress")
        first = repo.add_set(
            WorkoutSet(workout_id=w.id or 0, exercise_id=ex.id or 0, position=-1)
        )
        second = repo.add_set(
            WorkoutSet(workout_id=w.id or 0, exercise_id=ex.id or 0, position=-1)
        )
        assert first.position == 0
        assert second.position == 1

    def test_executed_bumps_use_count(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Squat")
        w = repo.create_workout(date="2024-05-01", status="in_progress")
        repo.add_set(
            WorkoutSet(
                workout_id=w.id or 0,
                exercise_id=ex.id or 0,
                position=0,
                actual_reps=5,
                actual_weight=100,
                executed=True,
            )
        )
        updated = [e for e in repo.list_exercises() if e.id == ex.id][0]
        assert updated.use_count == 1

    def test_update_set_marks_executed_stamps_completed(
        self, repo: WorkoutRepository
    ) -> None:
        ex = repo.get_or_create_exercise("Squat")
        w = repo.create_workout(date="2024-05-01", status="in_progress")
        s = repo.add_set(
            WorkoutSet(
                workout_id=w.id or 0,
                exercise_id=ex.id or 0,
                position=0,
                planned_reps=5,
                planned_weight=100,
            )
        )
        assert not s.executed
        after = repo.update_set(
            s.id or 0, executed=True, actual_reps=5, actual_weight=100
        )
        assert after.executed
        assert after.completed_at is not None

    def test_update_rejects_unknown_fields(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Squat")
        w = repo.create_workout(date="2024-05-01", status="in_progress")
        s = repo.add_set(
            WorkoutSet(workout_id=w.id or 0, exercise_id=ex.id or 0, position=0)
        )
        with pytest.raises(ValueError):
            repo.update_set(s.id or 0, bogus=1)

    def test_list_for_exercise(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Squat")
        w = repo.create_workout(date="2024-05-01", status="in_progress")
        repo.add_set(
            WorkoutSet(
                workout_id=w.id or 0,
                exercise_id=ex.id or 0,
                position=0,
                actual_reps=5,
                actual_weight=100,
                executed=True,
            )
        )
        sets = repo.list_sets_for_exercise(ex.id or 0)
        assert len(sets) == 1
        assert sets[0].exercise_name == "Squat"
