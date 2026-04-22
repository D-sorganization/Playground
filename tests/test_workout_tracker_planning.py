"""Tests for workout_tracker.planning (TDD - written before implementation)."""

from __future__ import annotations

from datetime import date as date_t
from datetime import timedelta

import pytest

from workout_tracker.db import WorkoutRepository, connect, init_db
from workout_tracker.models import WorkoutSet
from workout_tracker.planning import (
    apply_weekly_schedule,
    copy_last_weekday_session,
    create_workout_from_template,
    get_best_e1rm_for_exercise,
    list_templates,
    resolve_percentage_sets,
    save_as_template,
)


@pytest.fixture()
def repo() -> WorkoutRepository:
    conn = connect(":memory:")
    init_db(conn)
    return WorkoutRepository(conn)


def _create_newer_history(
    repo: WorkoutRepository,
    *,
    start_date: str = "2024-02-01",
    count: int = 500,
) -> None:
    start = date_t.fromisoformat(start_date)
    for day_offset in range(count):
        repo.create_workout(
            date=(start + timedelta(days=day_offset)).isoformat(),
            title=f"History {day_offset}",
            status="completed",
        )


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


class TestSaveAsTemplate:
    def test_save_creates_template(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Bench Press")
        w = repo.create_workout(date="2024-05-01", title="Push Day", status="completed")
        repo.add_set(
            WorkoutSet(
                workout_id=w.id or 0,
                exercise_id=ex.id or 0,
                position=0,
                planned_reps=5,
                planned_weight=135.0,
                executed=True,
                actual_reps=5,
                actual_weight=135.0,
            )
        )
        tmpl = save_as_template(repo, w.id or 0, name="Push Day Template")
        assert tmpl["name"] == "Push Day Template"
        assert tmpl["source_workout_id"] == w.id
        assert isinstance(tmpl["id"], int)

    def test_list_templates_returns_saved(self, repo: WorkoutRepository) -> None:
        w = repo.create_workout(date="2024-05-01", title="Pull Day", status="completed")
        save_as_template(repo, w.id or 0, name="Pull Template")
        save_as_template(repo, w.id or 0, name="Another Template")
        templates = list_templates(repo)
        names = [t["name"] for t in templates]
        assert "Pull Template" in names
        assert "Another Template" in names

    def test_list_templates_empty(self, repo: WorkoutRepository) -> None:
        assert list_templates(repo) == []


class TestCreateFromTemplate:
    def test_creates_new_workout_from_template(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Squat")
        w = repo.create_workout(date="2024-05-01", title="Leg Day", status="completed")
        repo.add_set(
            WorkoutSet(
                workout_id=w.id or 0,
                exercise_id=ex.id or 0,
                position=0,
                planned_reps=5,
                planned_weight=225.0,
                executed=True,
                actual_reps=5,
                actual_weight=225.0,
            )
        )
        tmpl = save_as_template(repo, w.id or 0, name="Leg Template")
        new_w = create_workout_from_template(repo, tmpl["id"], date="2024-06-01")
        assert new_w.date == "2024-06-01"
        assert new_w.status == "planned"
        assert len(new_w.sets) == 1
        assert new_w.sets[0].planned_reps == 5
        assert new_w.sets[0].planned_weight == 225.0
        assert new_w.sets[0].exercise_id == ex.id

    def test_creates_with_template_title_when_no_title_given(
        self, repo: WorkoutRepository
    ) -> None:
        w = repo.create_workout(date="2024-05-01", title="Push", status="planned")
        tmpl = save_as_template(repo, w.id or 0, name="Push Template")
        new_w = create_workout_from_template(repo, tmpl["id"], date="2024-06-01")
        assert new_w.title == "Push Template"

    def test_creates_with_custom_title(self, repo: WorkoutRepository) -> None:
        w = repo.create_workout(date="2024-05-01", title="Push", status="planned")
        tmpl = save_as_template(repo, w.id or 0, name="Push Template")
        new_w = create_workout_from_template(
            repo, tmpl["id"], date="2024-06-01", title="My Push"
        )
        assert new_w.title == "My Push"

    def test_raises_on_unknown_template(self, repo: WorkoutRepository) -> None:
        with pytest.raises(KeyError):
            create_workout_from_template(repo, 9999, date="2024-06-01")

    def test_copies_multiple_sets_in_order(self, repo: WorkoutRepository) -> None:
        ex1 = repo.get_or_create_exercise("Bench Press")
        ex2 = repo.get_or_create_exercise("Overhead Press")
        w = repo.create_workout(date="2024-05-01", title="Push", status="completed")
        repo.add_set(
            WorkoutSet(
                workout_id=w.id or 0,
                exercise_id=ex1.id or 0,
                position=0,
                planned_reps=5,
                planned_weight=135.0,
                executed=True,
                actual_reps=5,
                actual_weight=135.0,
            )
        )
        repo.add_set(
            WorkoutSet(
                workout_id=w.id or 0,
                exercise_id=ex2.id or 0,
                position=1,
                planned_reps=8,
                planned_weight=95.0,
                executed=True,
                actual_reps=8,
                actual_weight=95.0,
            )
        )
        tmpl = save_as_template(repo, w.id or 0, name="Push")
        new_w = create_workout_from_template(repo, tmpl["id"], date="2024-06-01")
        assert len(new_w.sets) == 2
        assert new_w.sets[0].exercise_id == ex1.id
        assert new_w.sets[1].exercise_id == ex2.id


# ---------------------------------------------------------------------------
# Template FK cascade (issue #333)
# ---------------------------------------------------------------------------


class TestTemplateFKCascade:
    def test_purge_exercise_cascades_to_template_sets(
        self, repo: WorkoutRepository
    ) -> None:
        """Purging an exercise must cascade to template_sets (issue #333).

        The schema must have ON DELETE CASCADE on template_sets.exercise_id so that
        a hard DELETE of an exercise row automatically removes its template_set rows
        rather than raising sqlite3.IntegrityError and returning HTTP 500.

        The real trigger is purge_trash(), which hard-deletes soft-deleted exercises.
        """
        import sqlite3

        ex = repo.get_or_create_exercise("Romanian Deadlift")
        w = repo.create_workout(date="2024-05-01", title="Leg Day", status="completed")
        repo.add_set(
            WorkoutSet(
                workout_id=w.id or 0,
                exercise_id=ex.id or 0,
                position=0,
                planned_reps=8,
                planned_weight=185.0,
                executed=True,
                actual_reps=8,
                actual_weight=185.0,
            )
        )
        tmpl = save_as_template(repo, w.id or 0, name="Leg Template")
        # Verify template_sets row exists
        ts_count = repo.conn.execute(
            "SELECT COUNT(*) FROM template_sets WHERE template_id = ?", (tmpl["id"],)
        ).fetchone()[0]
        assert ts_count == 1

        # Soft-delete the exercise first (simulates DELETE /api/exercises/<id>)
        repo.delete_exercise(ex.id or 0)

        # purge_trash does the real hard DELETE — this must not raise IntegrityError
        try:
            repo.purge_trash()
        except sqlite3.IntegrityError as exc:  # pragma: no cover
            pytest.fail(
                f"purge_trash() raised IntegrityError when exercises table had "
                f"template_sets rows — template_sets FK is missing ON DELETE CASCADE "
                f"(issue #333): {exc}"
            )

        # The template_sets row should have been cascaded away by the hard DELETE
        ts_after = repo.conn.execute(
            "SELECT COUNT(*) FROM template_sets WHERE template_id = ?", (tmpl["id"],)
        ).fetchone()[0]
        assert ts_after == 0, (
            "template_sets row was not cascade-deleted when exercise was hard-deleted; "
            "ON DELETE CASCADE is required on template_sets.exercise_id (issue #333)"
        )

    def test_schema_template_sets_exercise_fk_has_cascade(
        self, repo: WorkoutRepository
    ) -> None:
        """template_sets.exercise_id FK must have ON DELETE CASCADE (issue #333)."""
        fk_rows = repo.conn.execute(
            "PRAGMA foreign_key_list('template_sets')"
        ).fetchall()
        exercise_fk = next(
            (r for r in fk_rows if r["table"] == "exercises"),
            None,
        )
        assert exercise_fk is not None, "template_sets has no FK to exercises"
        assert exercise_fk["on_delete"] == "CASCADE", (
            f"template_sets.exercise_id FK has on_delete={exercise_fk['on_delete']!r}; "
            "expected CASCADE (issue #333)"
        )


# ---------------------------------------------------------------------------
# Copy last weekday session
# ---------------------------------------------------------------------------


class TestCopyLastWeekdaySession:
    def test_copies_most_recent_same_weekday(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Deadlift")
        # Monday 2024-05-06
        w = repo.create_workout(
            date="2024-05-06", title="Monday Pull", status="completed"
        )
        repo.add_set(
            WorkoutSet(
                workout_id=w.id or 0,
                exercise_id=ex.id or 0,
                position=0,
                planned_reps=5,
                planned_weight=315.0,
                executed=True,
                actual_reps=5,
                actual_weight=315.0,
            )
        )
        # Copy to next Monday 2024-05-13
        new_w = copy_last_weekday_session(repo, weekday=0, target_date="2024-05-13")
        assert new_w is not None
        assert new_w.date == "2024-05-13"
        assert new_w.status == "planned"
        assert len(new_w.sets) == 1
        assert new_w.sets[0].planned_weight == 315.0
        assert new_w.sets[0].executed is False

    def test_returns_none_when_no_prior_session(self, repo: WorkoutRepository) -> None:
        result = copy_last_weekday_session(repo, weekday=0, target_date="2024-05-13")
        assert result is None

    def test_picks_most_recent_weekday(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Squat")
        # Two Mondays: pick the most recent
        w1 = repo.create_workout(
            date="2024-04-29", title="Old Monday", status="completed"
        )
        repo.add_set(
            WorkoutSet(
                workout_id=w1.id or 0,
                exercise_id=ex.id or 0,
                position=0,
                planned_reps=5,
                planned_weight=200.0,
                executed=True,
                actual_reps=5,
                actual_weight=200.0,
            )
        )
        w2 = repo.create_workout(
            date="2024-05-06", title="Recent Monday", status="completed"
        )
        repo.add_set(
            WorkoutSet(
                workout_id=w2.id or 0,
                exercise_id=ex.id or 0,
                position=0,
                planned_reps=5,
                planned_weight=225.0,
                executed=True,
                actual_reps=5,
                actual_weight=225.0,
            )
        )
        new_w = copy_last_weekday_session(repo, weekday=0, target_date="2024-05-13")
        assert new_w is not None
        assert new_w.sets[0].planned_weight == 225.0

    def test_only_looks_at_target_weekday(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Bench")
        # Tuesday (weekday=1), 2024-05-07
        w = repo.create_workout(date="2024-05-07", title="Tuesday", status="completed")
        repo.add_set(
            WorkoutSet(
                workout_id=w.id or 0,
                exercise_id=ex.id or 0,
                position=0,
                planned_reps=5,
                planned_weight=100.0,
                executed=True,
                actual_reps=5,
                actual_weight=100.0,
            )
        )
        # Request Monday (weekday=0) — should return None
        result = copy_last_weekday_session(repo, weekday=0, target_date="2024-05-13")
        assert result is None

    def test_finds_prior_weekday_beyond_latest_500_workouts(
        self, repo: WorkoutRepository
    ) -> None:
        ex = repo.get_or_create_exercise("Bench")
        w = repo.create_workout(
            date="2024-01-01",
            title="Historical Monday",
            status="completed",
        )
        repo.add_set(
            WorkoutSet(
                workout_id=w.id or 0,
                exercise_id=ex.id or 0,
                position=0,
                planned_reps=5,
                planned_weight=135.0,
                executed=True,
                actual_reps=5,
                actual_weight=135.0,
            )
        )
        _create_newer_history(repo)

        new_w = copy_last_weekday_session(repo, weekday=0, target_date="2024-01-08")

        assert new_w is not None
        assert new_w.title == "Historical Monday"
        assert new_w.sets[0].planned_weight == 135.0


# ---------------------------------------------------------------------------
# Weekly schedule
# ---------------------------------------------------------------------------


class TestWeeklySchedule:
    def test_creates_planned_workouts_for_week(self, repo: WorkoutRepository) -> None:
        schedule = {0: "Push", 2: "Pull", 4: "Legs"}
        # Week of 2024-05-06 (Monday)
        workouts = apply_weekly_schedule(repo, schedule, week_start="2024-05-06")
        assert len(workouts) == 3
        dates = {w.date for w in workouts}
        assert "2024-05-06" in dates  # Monday = Push
        assert "2024-05-08" in dates  # Wednesday = Pull
        assert "2024-05-10" in dates  # Friday = Legs

    def test_workout_titles_from_schedule(self, repo: WorkoutRepository) -> None:
        schedule = {1: "Upper Body", 3: "Lower Body"}
        workouts = apply_weekly_schedule(repo, schedule, week_start="2024-05-06")
        titles = {w.date: w.title for w in workouts}
        assert titles["2024-05-07"] == "Upper Body"
        assert titles["2024-05-09"] == "Lower Body"

    def test_all_created_as_planned(self, repo: WorkoutRepository) -> None:
        schedule = {0: "Push", 4: "Pull"}
        workouts = apply_weekly_schedule(repo, schedule, week_start="2024-05-06")
        assert all(w.status == "planned" for w in workouts)

    def test_skips_existing_workout_on_same_date(self, repo: WorkoutRepository) -> None:
        existing = repo.create_workout(date="2024-05-06", title="Already Planned")
        schedule = {0: "Push"}
        workouts = apply_weekly_schedule(repo, schedule, week_start="2024-05-06")
        # Should not create a duplicate; returns empty (or skips that day)
        ids = [w.id for w in workouts]
        assert existing.id not in ids

    def test_invalid_weekday_raises(self, repo: WorkoutRepository) -> None:
        with pytest.raises(ValueError):
            apply_weekly_schedule(repo, {7: "Bad"}, week_start="2024-05-06")

    def test_week_start_not_monday_raises(self, repo: WorkoutRepository) -> None:
        with pytest.raises(ValueError):
            apply_weekly_schedule(repo, {0: "Push"}, week_start="2024-05-07")

    def test_skips_existing_workout_beyond_latest_500_workouts(
        self, repo: WorkoutRepository
    ) -> None:
        existing = repo.create_workout(date="2024-01-01", title="Existing Monday")
        _create_newer_history(repo)

        workouts = apply_weekly_schedule(repo, {0: "Push"}, week_start="2024-01-01")

        same_date_count = repo.conn.execute(
            "SELECT COUNT(*) FROM workouts WHERE date = ? AND deleted_at IS NULL",
            (existing.date,),
        ).fetchone()[0]
        assert workouts == []
        assert same_date_count == 1


# ---------------------------------------------------------------------------
# Percentage-based sets
# ---------------------------------------------------------------------------


class TestGetBestE1rm:
    def test_returns_best_e1rm_for_exercise(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Bench Press")
        w = repo.create_workout(date="2024-05-01", status="completed")
        repo.add_set(
            WorkoutSet(
                workout_id=w.id or 0,
                exercise_id=ex.id or 0,
                position=0,
                actual_reps=5,
                actual_weight=200.0,
                executed=True,
            )
        )
        e1rm = get_best_e1rm_for_exercise(repo, ex.id or 0)
        assert e1rm is not None
        assert e1rm > 200.0  # Should be > raw weight due to reps

    def test_returns_none_when_no_executed_sets(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Bench Press")
        result = get_best_e1rm_for_exercise(repo, ex.id or 0)
        assert result is None

    def test_picks_best_across_multiple_sets(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Squat")
        w = repo.create_workout(date="2024-05-01", status="completed")
        repo.add_set(
            WorkoutSet(
                workout_id=w.id or 0,
                exercise_id=ex.id or 0,
                position=0,
                actual_reps=5,
                actual_weight=225.0,
                executed=True,
            )
        )
        repo.add_set(
            WorkoutSet(
                workout_id=w.id or 0,
                exercise_id=ex.id or 0,
                position=1,
                actual_reps=1,
                actual_weight=300.0,
                executed=True,
            )
        )
        e1rm = get_best_e1rm_for_exercise(repo, ex.id or 0)
        assert e1rm is not None
        # 225x5 epley gives 225*(1+5/30)=262.5; 300x1=300 => best is 300
        assert e1rm == pytest.approx(300.0, abs=1.0)


class TestResolvePercentageSets:
    def test_resolves_percentage_weight(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Bench Press")
        w = repo.create_workout(date="2024-05-01", status="completed")
        repo.add_set(
            WorkoutSet(
                workout_id=w.id or 0,
                exercise_id=ex.id or 0,
                position=0,
                actual_reps=1,
                actual_weight=200.0,
                executed=True,
            )
        )
        from workout_tracker.parser import ParsedEntry, ParsedSet

        entries = [
            ParsedEntry(
                exercise_name="Bench Press",
                sets=[ParsedSet(reps=5, weight=0.8, unit="lbs", rpe=None)],
            )
        ]
        resolved = resolve_percentage_sets(repo, entries, percentage_threshold=1.5)
        assert len(resolved) == 1
        assert resolved[0].sets[0].weight == pytest.approx(160.0, abs=1.0)

    def test_leaves_absolute_weight_unchanged(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Squat")
        w = repo.create_workout(date="2024-05-01", status="completed")
        repo.add_set(
            WorkoutSet(
                workout_id=w.id or 0,
                exercise_id=ex.id or 0,
                position=0,
                actual_reps=1,
                actual_weight=300.0,
                executed=True,
            )
        )
        from workout_tracker.parser import ParsedEntry, ParsedSet

        entries = [
            ParsedEntry(
                exercise_name="Squat",
                sets=[ParsedSet(reps=5, weight=225.0, unit="lbs", rpe=None)],
            )
        ]
        resolved = resolve_percentage_sets(repo, entries, percentage_threshold=1.5)
        assert resolved[0].sets[0].weight == pytest.approx(225.0)

    def test_no_e1rm_leaves_set_unchanged(self, repo: WorkoutRepository) -> None:
        repo.get_or_create_exercise("Overhead Press")
        from workout_tracker.parser import ParsedEntry, ParsedSet

        entries = [
            ParsedEntry(
                exercise_name="Overhead Press",
                sets=[ParsedSet(reps=5, weight=0.75, unit="lbs", rpe=None)],
            )
        ]
        resolved = resolve_percentage_sets(repo, entries, percentage_threshold=1.5)
        # No executed sets -> can't resolve -> leave as-is
        assert resolved[0].sets[0].weight == pytest.approx(0.75)

    def test_none_weight_unchanged(self, repo: WorkoutRepository) -> None:
        from workout_tracker.parser import ParsedEntry, ParsedSet

        entries = [
            ParsedEntry(
                exercise_name="Pull-ups",
                sets=[ParsedSet(reps=5, weight=None, unit="lbs", rpe=None)],
            )
        ]
        resolved = resolve_percentage_sets(repo, entries, percentage_threshold=1.5)
        assert resolved[0].sets[0].weight is None
