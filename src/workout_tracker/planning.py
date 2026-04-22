"""Workout planning helpers: templates, copy-last, weekly schedule, % sets."""

from __future__ import annotations

from datetime import date as date_t
from datetime import timedelta
from typing import Any

from workout_tracker.db import WorkoutRepository
from workout_tracker.models import Workout, WorkoutSet
from workout_tracker.parser import ParsedEntry
from workout_tracker.stats import best_1rm_estimate

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _copy_sets_as_planned(
    repo: WorkoutRepository,
    source_sets: list[WorkoutSet],
    target_workout_id: int,
) -> None:
    for i, s in enumerate(source_sets):
        planned_weight = (
            s.planned_weight if s.planned_weight is not None else s.actual_weight
        )
        planned_reps = s.planned_reps if s.planned_reps is not None else s.actual_reps
        repo.add_set(
            WorkoutSet(
                workout_id=target_workout_id,
                exercise_id=s.exercise_id,
                position=i,
                planned_reps=planned_reps,
                planned_weight=planned_weight,
                unit=s.unit,
                executed=False,
            )
        )


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------


def save_as_template(
    repo: WorkoutRepository,
    workout_id: int,
    name: str,
) -> dict[str, Any]:
    """Save a workout as a named template. Returns template dict."""
    source = repo.get_workout(workout_id)
    with repo._tx() as cur:
        cur.execute(
            "INSERT INTO workout_templates (name, source_workout_id) VALUES (?, ?)",
            (name, source.id),
        )
        tmpl_id = cur.lastrowid

    with repo._tx() as cur:
        for s in source.sets:
            planned_weight = (
                s.planned_weight if s.planned_weight is not None else s.actual_weight
            )
            planned_reps = (
                s.planned_reps if s.planned_reps is not None else s.actual_reps
            )
            cur.execute(
                "INSERT INTO template_sets "
                "(template_id, exercise_id, position, "
                "planned_reps, planned_weight, unit) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (
                    tmpl_id,
                    s.exercise_id,
                    s.position if s.position is not None else 0,
                    planned_reps,
                    planned_weight,
                    s.unit,
                ),
            )

    row = repo.conn.execute(
        "SELECT * FROM workout_templates WHERE id = ?", (tmpl_id,)
    ).fetchone()
    return _row_to_template(row)


def list_templates(repo: WorkoutRepository) -> list[dict[str, Any]]:
    """Return all saved templates."""
    rows = repo.conn.execute(
        "SELECT * FROM workout_templates ORDER BY created_at DESC"
    ).fetchall()
    return [_row_to_template(r) for r in rows]


def create_workout_from_template(
    repo: WorkoutRepository,
    template_id: int,
    date: str,
    title: str | None = None,
) -> Workout:
    """Create a new planned workout from a template."""
    tmpl_row = repo.conn.execute(
        "SELECT * FROM workout_templates WHERE id = ?", (template_id,)
    ).fetchone()
    if tmpl_row is None:
        raise KeyError(f"template {template_id} not found")

    tmpl = _row_to_template(tmpl_row)
    workout_title = title if title is not None else tmpl["name"]

    w = repo.create_workout(date=date, title=workout_title, status="planned")

    set_rows = repo.conn.execute(
        "SELECT * FROM template_sets WHERE template_id = ? ORDER BY position ASC",
        (template_id,),
    ).fetchall()
    for row in set_rows:
        repo.add_set(
            WorkoutSet(
                workout_id=w.id or 0,
                exercise_id=row["exercise_id"],
                position=row["position"],
                planned_reps=row["planned_reps"],
                planned_weight=row["planned_weight"],
                unit=row["unit"],
                executed=False,
            )
        )

    return repo.get_workout(w.id or 0)


def _row_to_template(row: Any) -> dict[str, Any]:
    return {
        "id": row["id"],
        "name": row["name"],
        "source_workout_id": row["source_workout_id"],
        "created_at": row["created_at"],
    }


# ---------------------------------------------------------------------------
# Copy last weekday session
# ---------------------------------------------------------------------------


def copy_last_weekday_session(
    repo: WorkoutRepository,
    weekday: int,
    target_date: str,
) -> Workout | None:
    """Copy the most recent workout on the given weekday to target_date.

    weekday: 0=Monday .. 6=Sunday. Returns the new planned workout or None.
    """
    if weekday < 0 or weekday > 6:
        raise ValueError(f"weekday must be 0-6, got {weekday}")

    rows = repo.conn.execute(
        "SELECT id, date FROM workouts "
        "WHERE deleted_at IS NULL AND date < ? "
        "ORDER BY date DESC, id DESC",
        (target_date,),
    ).fetchall()
    source_id = next(
        (
            int(row["id"])
            for row in rows
            if date_t.fromisoformat(row["date"]).weekday() == weekday
        ),
        None,
    )
    if source_id is None:
        return None

    source = repo.get_workout(source_id)
    new_w = repo.create_workout(
        date=target_date,
        title=source.title,
        status="planned",
    )
    _copy_sets_as_planned(repo, source.sets, new_w.id or 0)
    return repo.get_workout(new_w.id or 0)


# ---------------------------------------------------------------------------
# Weekly schedule
# ---------------------------------------------------------------------------


def apply_weekly_schedule(
    repo: WorkoutRepository,
    schedule: dict[int, str],
    week_start: str,
) -> list[Workout]:
    """Create planned workouts per schedule for the given week.

    schedule: {weekday: title} where weekday is 0=Mon .. 6=Sun.
    week_start must be a Monday. Skips dates that already have a workout.
    """
    start = date_t.fromisoformat(week_start)
    if start.weekday() != 0:
        raise ValueError(
            f"week_start must be a Monday, got {week_start} ({start.strftime('%A')})"
        )

    for day in schedule:
        if day < 0 or day > 6:
            raise ValueError(f"weekday must be 0-6, got {day}")

    week_end = (start + timedelta(days=6)).isoformat()
    existing_dates = {
        row["date"]
        for row in repo.conn.execute(
            "SELECT DISTINCT date FROM workouts "
            "WHERE deleted_at IS NULL AND date BETWEEN ? AND ?",
            (week_start, week_end),
        ).fetchall()
    }

    created: list[Workout] = []
    for day_offset, title in sorted(schedule.items()):
        date_str = (start + timedelta(days=day_offset)).isoformat()
        if date_str in existing_dates:
            continue
        w = repo.create_workout(date=date_str, title=title, status="planned")
        created.append(w)

    return created


# ---------------------------------------------------------------------------
# Percentage-based sets
# ---------------------------------------------------------------------------


def get_best_e1rm_for_exercise(
    repo: WorkoutRepository,
    exercise_id: int,
) -> float | None:
    """Return the best estimated 1RM for an exercise from executed sets."""
    sets = repo.list_sets_for_exercise(exercise_id, executed_only=True)
    valid = [s for s in sets if s.actual_weight is not None and s.actual_reps]
    if not valid:
        return None
    return max(
        best_1rm_estimate(s.actual_weight or 0.0, s.actual_reps or 0) for s in valid
    )


def resolve_percentage_sets(
    repo: WorkoutRepository,
    entries: list[ParsedEntry],
    percentage_threshold: float = 1.5,
) -> list[ParsedEntry]:
    """Resolve percentage-based weights in parsed entries.

    Any set with 0 < weight < percentage_threshold is treated as a fraction
    of the exercise's best e1RM (e.g. 0.8 = 80%).
    If no e1RM is available, the value is left as-is.
    """
    for entry in entries:
        ex = repo.get_or_create_exercise(entry.exercise_name)
        e1rm: float | None = None
        for ps in entry.sets:
            if ps.weight is None:
                continue
            if 0 < ps.weight < percentage_threshold:
                if e1rm is None:
                    e1rm = get_best_e1rm_for_exercise(repo, ex.id or 0)
                if e1rm is not None:
                    ps.weight = round(ps.weight * e1rm, 2)
    return entries
