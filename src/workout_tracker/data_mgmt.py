"""Data management helpers: JSON export/import, CSV import (Strong/Hevy/FitNotes).

All CSV parsers return a list of ImportedWorkout objects that callers can
persist via WorkoutRepository.  The module has no side-effects on import.
"""

from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)

# ─── Domain types ─────────────────────────────────────────────────────────────


@dataclass
class ImportedSet:
    exercise_name: str
    weight: float | None = None
    reps: int | None = None
    unit: str = "lbs"
    rpe: float | None = None


@dataclass
class ImportedWorkout:
    date: str  # ISO YYYY-MM-DD
    title: str | None = None
    sets: list[ImportedSet] = field(default_factory=list)


# ─── CSV helpers ──────────────────────────────────────────────────────────────


def _parse_float(val: str | None) -> float | None:
    if val is None:
        return None
    val = val.strip()
    if not val:
        return None
    try:
        return float(val)
    except ValueError:
        return None


def _parse_int(val: str) -> int | None:
    f = _parse_float(val)
    return int(f) if f is not None else None


def _date_from_datetime(dt_str: str) -> str:
    """Extract YYYY-MM-DD from 'YYYY-MM-DD HH:MM:SS' or 'YYYY-MM-DD'."""
    return dt_str.strip()[:10]


# ─── Strong CSV ───────────────────────────────────────────────────────────────
# Date,Workout Name,Duration,Exercise Name,Set Order,Weight,Reps,...,RPE


def parse_strong_csv(text: str) -> list[ImportedWorkout]:
    """Parse a Strong app CSV export."""
    reader = csv.DictReader(io.StringIO(text.strip()))
    workouts: dict[tuple[str, str], ImportedWorkout] = {}

    for row in reader:
        date = _date_from_datetime(row.get("Date", ""))
        if not date or len(date) < 10:
            continue
        title = (row.get("Workout Name") or "").strip() or None
        key = (date, title or "")
        if key not in workouts:
            workouts[key] = ImportedWorkout(date=date, title=title)
        exercise = (row.get("Exercise Name") or "").strip()
        if not exercise:
            continue
        weight = _parse_float(row.get("Weight", ""))
        reps = _parse_int(row.get("Reps", ""))
        rpe = _parse_float(row.get("RPE", ""))
        workouts[key].sets.append(
            ImportedSet(
                exercise_name=exercise,
                weight=weight,
                reps=reps,
                unit="lbs",
                rpe=rpe,
            )
        )

    return list(workouts.values())


# ─── Hevy CSV ─────────────────────────────────────────────────────────────────
# title,start_time,end_time,exercise_title,...,weight_lbs,reps,...


def parse_hevy_csv(text: str) -> list[ImportedWorkout]:
    """Parse a Hevy app CSV export."""
    reader = csv.DictReader(io.StringIO(text.strip()))
    workouts: dict[tuple[str, str], ImportedWorkout] = {}

    for row in reader:
        start = _date_from_datetime(row.get("start_time", ""))
        if not start or len(start) < 10:
            continue
        title = (row.get("title") or "").strip() or None
        key = (start, title or "")
        if key not in workouts:
            workouts[key] = ImportedWorkout(date=start, title=title)
        exercise = (row.get("exercise_title") or "").strip()
        if not exercise:
            continue
        weight = _parse_float(row.get("weight_lbs", ""))
        reps = _parse_int(row.get("reps", ""))
        rpe = _parse_float(row.get("rpe", ""))
        workouts[key].sets.append(
            ImportedSet(
                exercise_name=exercise,
                weight=weight,
                reps=reps,
                unit="lbs",
                rpe=rpe,
            )
        )

    return list(workouts.values())


# ─── FitNotes CSV ─────────────────────────────────────────────────────────────
# Date,Category,Exercise,Weight (lbs),Reps,...


def parse_fitnotes_csv(text: str) -> list[ImportedWorkout]:
    """Parse a FitNotes CSV export."""
    reader = csv.DictReader(io.StringIO(text.strip()))
    workouts: dict[str, ImportedWorkout] = {}

    for row in reader:
        date = (row.get("Date") or "").strip()
        if not date or len(date) < 10:
            continue
        if date not in workouts:
            workouts[date] = ImportedWorkout(date=date)
        exercise = (row.get("Exercise") or "").strip()
        if not exercise:
            continue
        # FitNotes uses "Weight (lbs)" or "Weight (kg)"
        weight_key = next((k for k in row if k.startswith("Weight")), None)
        weight = _parse_float(row[weight_key]) if weight_key else None
        unit = "kg" if weight_key and "kg" in weight_key else "lbs"
        reps = _parse_int(row.get("Reps", ""))
        workouts[date].sets.append(
            ImportedSet(exercise_name=exercise, weight=weight, reps=reps, unit=unit)
        )

    return list(workouts.values())


# ─── Format detection ─────────────────────────────────────────────────────────

_FORMAT_HEADERS: dict[str, frozenset[str]] = {
    "strong": frozenset(
        {"Date", "Workout Name", "Exercise Name", "Set Order", "Weight", "Reps"}
    ),
    "hevy": frozenset({"title", "start_time", "exercise_title", "weight_lbs", "reps"}),
    "fitnotes": frozenset({"Date", "Category", "Exercise", "Reps"}),
}


def detect_csv_format(text: str) -> str:
    """Detect CSV format from header row. Raises ValueError if unrecognised."""
    first_line = text.strip().splitlines()[0] if text.strip() else ""
    reader = csv.reader(io.StringIO(first_line))
    try:
        headers = frozenset(next(reader))
    except StopIteration:
        headers = frozenset()

    for fmt, required in _FORMAT_HEADERS.items():
        if required.issubset(headers):
            return fmt

    raise ValueError(
        f"Cannot detect CSV format. Headers found: {headers!r}. "
        "Supported: strong, hevy, fitnotes."
    )


# ─── JSON export / import ─────────────────────────────────────────────────────


def export_db(repo: Any) -> dict[str, Any]:
    """Produce a full JSON backup of the DB (all non-deleted records)."""
    exercises = [e.to_dict() for e in repo.list_exercises()]
    workouts_raw = repo.list_workouts(limit=100_000)
    workouts = []
    all_sets = []
    for w in workouts_raw:
        wd = w.to_dict()
        wd.pop("sets", None)
        workouts.append(wd)
        all_sets.extend(s.to_dict() for s in w.sets)

    return {
        "version": "1",
        "exercises": exercises,
        "workouts": workouts,
        "sets": all_sets,
    }


def import_db(repo: Any, data: dict[str, Any], mode: str = "merge") -> dict[str, int]:
    """Import a JSON backup into the repo.

    mode="restore" — clears the DB first, then imports.
    mode="merge"   — skips exercises that already exist (by normalized_name);
                     imports new workouts/sets unconditionally.

    Returns counts of inserted records.
    """
    if mode not in ("restore", "merge"):
        raise ValueError(f"mode must be 'restore' or 'merge', got {mode!r}")

    exercises_in = data.get("exercises") or []
    workouts_in = data.get("workouts") or []
    sets_in = data.get("sets") or []

    if mode == "restore":
        _clear_db(repo)

    ex_inserted = 0
    ex_id_map: dict[int, int] = {}  # old_id → new_id

    for ex_data in exercises_in:
        old_id = ex_data.get("id")
        name = (ex_data.get("name") or "").strip()
        if not name:
            continue
        existing = repo._find_exercise_by_normalized(
            ex_data.get("normalized_name") or ""
        )
        if existing is not None:
            if old_id:
                ex_id_map[old_id] = existing.id
            continue
        new_ex = repo.get_or_create_exercise(name)
        if old_id:
            ex_id_map[old_id] = new_ex.id
        ex_inserted += 1

    w_inserted = 0
    w_id_map: dict[int, int] = {}

    for w_data in workouts_in:
        old_wid = w_data.get("id")
        try:
            new_w = repo.create_workout(
                date=w_data["date"],
                title=w_data.get("title"),
                notes=w_data.get("notes"),
                status=w_data.get("status", "completed"),
            )
        except (KeyError, ValueError):
            continue
        if old_wid:
            w_id_map[old_wid] = new_w.id
        w_inserted += 1

    from workout_tracker.models import WorkoutSet

    s_inserted = 0
    for s_data in sets_in:
        old_eid = s_data.get("exercise_id")
        old_wid = s_data.get("workout_id")
        new_eid = ex_id_map.get(old_eid) if old_eid else None
        new_wid = w_id_map.get(old_wid) if old_wid else None
        if not new_eid or not new_wid:
            continue
        try:
            s = WorkoutSet(
                workout_id=new_wid,
                exercise_id=new_eid,
                position=-1,
                planned_reps=s_data.get("planned_reps"),
                planned_weight=s_data.get("planned_weight"),
                actual_reps=s_data.get("actual_reps"),
                actual_weight=s_data.get("actual_weight"),
                rpe=s_data.get("rpe"),
                unit=s_data.get("unit", "lbs"),
                executed=bool(s_data.get("executed", False)),
                notes=s_data.get("notes"),
            )
            repo.add_set(s)
            s_inserted += 1
        except (ValueError, KeyError):
            continue

    return {"exercises": ex_inserted, "workouts": w_inserted, "sets": s_inserted}


def _clear_db(repo: Any) -> None:
    """Hard-delete all non-deleted records (for restore mode)."""
    with repo._tx() as cur:
        cur.execute("DELETE FROM sets")
        cur.execute("DELETE FROM workouts")
        cur.execute("DELETE FROM exercises")
