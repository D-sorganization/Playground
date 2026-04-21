"""Tests for workout_tracker.db (repository layer)."""

from __future__ import annotations

import sqlite3

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


class TestAliasRepo:
    def test_add_and_list_aliases(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Bench Press")
        alias = repo.add_alias(ex.id or 0, "BP")
        assert alias.id is not None
        assert alias.alias == "BP"
        assert alias.exercise_id == ex.id
        aliases = repo.list_aliases(ex.id or 0)
        assert len(aliases) == 1
        assert aliases[0].alias == "BP"

    def test_alias_normalized(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Bench Press")
        alias = repo.add_alias(ex.id or 0, "Bench-Press!")
        assert alias.normalized_alias == "benchpress"

    def test_resolve_alias_returns_exercise(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Bench Press")
        repo.add_alias(ex.id or 0, "BP")
        resolved = repo.resolve_alias("BP")
        assert resolved is not None
        assert resolved.id == ex.id

    def test_resolve_alias_unknown_returns_none(self, repo: WorkoutRepository) -> None:
        assert repo.resolve_alias("nonexistent") is None

    def test_delete_alias(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Bench Press")
        alias = repo.add_alias(ex.id or 0, "BP")
        repo.delete_alias(alias.id or 0)
        aliases = repo.list_aliases(ex.id or 0)
        assert aliases == []

    def test_alias_unique_constraint(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Bench Press")
        repo.add_alias(ex.id or 0, "BP")
        with pytest.raises(sqlite3.IntegrityError):
            repo.add_alias(ex.id or 0, "BP")

    def test_alias_cascade_delete_with_exercise(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Bench Press")
        repo.add_alias(ex.id or 0, "BP")
        repo.delete_exercise(ex.id or 0)
        # Exercise deleted, alias should be gone too
        resolved = repo.resolve_alias("BP")
        assert resolved is None


class TestSearchWorkouts:
    def test_search_all_returns_workouts(self, repo: WorkoutRepository) -> None:
        repo.create_workout(date="2024-01-10", status="completed")
        repo.create_workout(date="2024-02-10", status="planned")
        results = repo.search_workouts()
        assert len(results) == 2

    def test_search_by_date_from(self, repo: WorkoutRepository) -> None:
        repo.create_workout(date="2024-01-10", status="completed")
        repo.create_workout(date="2024-06-10", status="completed")
        results = repo.search_workouts(date_from="2024-03-01")
        assert len(results) == 1
        assert results[0].date == "2024-06-10"

    def test_search_by_date_to(self, repo: WorkoutRepository) -> None:
        repo.create_workout(date="2024-01-10", status="completed")
        repo.create_workout(date="2024-06-10", status="completed")
        results = repo.search_workouts(date_to="2024-03-01")
        assert len(results) == 1
        assert results[0].date == "2024-01-10"

    def test_search_by_status(self, repo: WorkoutRepository) -> None:
        repo.create_workout(date="2024-01-10", status="completed")
        repo.create_workout(date="2024-02-10", status="planned")
        results = repo.search_workouts(status="completed")
        assert len(results) == 1
        assert results[0].status == "completed"

    def test_search_by_exercise_name(self, repo: WorkoutRepository) -> None:
        ex1 = repo.get_or_create_exercise("Bench Press")
        ex2 = repo.get_or_create_exercise("Squat")
        w1 = repo.create_workout(date="2024-01-10", status="completed")
        w2 = repo.create_workout(date="2024-02-10", status="completed")
        from workout_tracker.models import WorkoutSet as WS

        repo.add_set(WS(workout_id=w1.id or 0, exercise_id=ex1.id or 0, position=0))
        repo.add_set(WS(workout_id=w2.id or 0, exercise_id=ex2.id or 0, position=0))
        results = repo.search_workouts(exercise_name="bench")
        assert len(results) == 1
        assert results[0].id == w1.id

    def test_search_by_min_weight(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Bench Press")
        w1 = repo.create_workout(date="2024-01-10", status="completed")
        w2 = repo.create_workout(date="2024-02-10", status="completed")
        from workout_tracker.models import WorkoutSet as WS

        repo.add_set(
            WS(
                workout_id=w1.id or 0,
                exercise_id=ex.id or 0,
                position=0,
                actual_weight=100.0,
                executed=True,
            )
        )
        repo.add_set(
            WS(
                workout_id=w2.id or 0,
                exercise_id=ex.id or 0,
                position=0,
                actual_weight=200.0,
                executed=True,
            )
        )
        results = repo.search_workouts(min_weight=150.0)
        assert len(results) == 1
        assert results[0].id == w2.id

    def test_search_invalid_status_raises(self, repo: WorkoutRepository) -> None:
        with pytest.raises(ValueError):
            repo.search_workouts(status="bogus")

    def test_search_limit_200(self, repo: WorkoutRepository) -> None:
        for i in range(5):
            repo.create_workout(date=f"2024-01-{i + 1:02d}", status="planned")
        results = repo.search_workouts()
        assert len(results) == 5


class TestNewSetFields:
    def test_add_set_with_group_and_protocol(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Bench Press")
        w = repo.create_workout(date="2024-06-01", status="in_progress")
        s = repo.add_set(
            WorkoutSet(
                workout_id=w.id or 0,
                exercise_id=ex.id or 0,
                position=0,
                actual_reps=10,
                actual_weight=135,
                executed=True,
                group_id="A1",
                protocol="amrap",
            )
        )
        assert s.group_id == "A1"
        assert s.protocol == "amrap"
        assert s.is_bodyweight is False

    def test_add_bodyweight_set(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Pull-ups")
        w = repo.create_workout(date="2024-06-01", status="in_progress")
        s = repo.add_set(
            WorkoutSet(
                workout_id=w.id or 0,
                exercise_id=ex.id or 0,
                position=0,
                actual_reps=8,
                actual_weight=25,
                executed=True,
                is_bodyweight=True,
            )
        )
        assert s.is_bodyweight is True
        assert s.actual_weight == 25.0

    def test_update_set_group_and_protocol(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Squat")
        w = repo.create_workout(date="2024-06-01", status="in_progress")
        s = repo.add_set(
            WorkoutSet(workout_id=w.id or 0, exercise_id=ex.id or 0, position=0)
        )
        after = repo.update_set(s.id or 0, group_id="B2", protocol="emom")
        assert after.group_id == "B2"
        assert after.protocol == "emom"

    def test_update_set_is_bodyweight(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Dips")
        w = repo.create_workout(date="2024-06-01", status="in_progress")
        s = repo.add_set(
            WorkoutSet(workout_id=w.id or 0, exercise_id=ex.id or 0, position=0)
        )
        after = repo.update_set(s.id or 0, is_bodyweight=True, actual_weight=45)
        assert after.is_bodyweight is True

    def test_fields_persisted_across_get_workout(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Pull-ups")
        w = repo.create_workout(date="2024-06-01", status="in_progress")
        repo.add_set(
            WorkoutSet(
                workout_id=w.id or 0,
                exercise_id=ex.id or 0,
                position=0,
                actual_reps=10,
                is_bodyweight=True,
                group_id="A1",
                protocol="failure",
                executed=True,
            )
        )
        fetched = repo.get_workout(w.id or 0)
        s = fetched.sets[0]
        assert s.is_bodyweight is True
        assert s.group_id == "A1"
        assert s.protocol == "failure"


class TestMuscleTags:
    def test_update_and_clear_tags(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Bench Press")
        updated = repo.update_exercise_tags(ex.id or 0, "chest, shoulders")
        assert updated.muscle_tags == "chest, shoulders"
        cleared = repo.update_exercise_tags(ex.id or 0, "")
        assert cleared.muscle_tags is None

    def test_tags_persist_in_exercise_listing(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Deadlift")
        repo.update_exercise_tags(ex.id or 0, "back,legs")
        listed = [e for e in repo.list_exercises() if e.name == "Deadlift"]
        assert listed[0].muscle_tags == "back,legs"

    def test_unknown_exercise_raises(self, repo: WorkoutRepository) -> None:
        with pytest.raises(KeyError):
            repo.update_exercise_tags(99999, "chest")


class TestSoftDelete:
    def test_delete_and_restore_exercise(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Bench Press")
        repo.delete_exercise(ex.id or 0)
        assert "Bench Press" not in [e.name for e in repo.list_exercises()]
        repo.restore_exercise(ex.id or 0)
        assert "Bench Press" in [e.name for e in repo.list_exercises()]

    def test_delete_and_restore_workout(self, repo: WorkoutRepository) -> None:
        w = repo.create_workout(date="2024-05-01")
        repo.delete_workout(w.id or 0)
        with pytest.raises(KeyError):
            repo.get_workout(w.id or 0)
        repo.restore_workout(w.id or 0)
        assert w.id in [x.id for x in repo.list_workouts()]

    def test_delete_and_restore_set(self, repo: WorkoutRepository) -> None:
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
        repo.delete_set(s.id or 0)
        assert all(x.id != s.id for x in repo.get_workout(w.id or 0).sets)
        repo.restore_set(s.id or 0)
        assert any(x.id == s.id for x in repo.get_workout(w.id or 0).sets)

    def test_restore_set_blocked_when_workout_deleted(
        self, repo: WorkoutRepository
    ) -> None:
        """restore_set raises ValueError when parent workout is deleted (issue #339)."""
        ex = repo.get_or_create_exercise("Deadlift")
        w = repo.create_workout(date="2024-06-01", status="in_progress")
        s = repo.add_set(
            WorkoutSet(
                workout_id=w.id or 0,
                exercise_id=ex.id or 0,
                position=0,
                actual_reps=3,
                actual_weight=200,
                executed=True,
            )
        )
        repo.delete_set(s.id or 0)
        # Soft-delete the parent workout (sets remain but workout is trashed)
        repo.delete_workout(w.id or 0)
        with pytest.raises(ValueError, match="workout"):
            repo.restore_set(s.id or 0)

    def test_restore_set_blocked_when_exercise_deleted(
        self, repo: WorkoutRepository
    ) -> None:
        """restore_set raises ValueError when parent exercise deleted (issue #339)."""
        ex = repo.get_or_create_exercise("Overhead Press")
        w = repo.create_workout(date="2024-06-02", status="in_progress")
        s = repo.add_set(
            WorkoutSet(
                workout_id=w.id or 0,
                exercise_id=ex.id or 0,
                position=0,
                actual_reps=5,
                actual_weight=95,
                executed=True,
            )
        )
        repo.delete_set(s.id or 0)
        # Soft-delete the parent exercise
        repo.delete_exercise(ex.id or 0)
        with pytest.raises(ValueError, match="exercise"):
            repo.restore_set(s.id or 0)
