"""SQLite repository layer.

Repository pattern keeps Law of Demeter clean: callers ask the repo, the repo
talks to sqlite. No raw SQL leaks into routes/services.
"""

from __future__ import annotations

import logging
import sqlite3
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from importlib import resources
from pathlib import Path
from typing import Any

from workout_tracker.models import (
    VALID_STATUSES,
    Exercise,
    ExerciseAlias,
    Workout,
    WorkoutSet,
    normalize_name,
)

_NEW_SET_COLUMNS = ("group_id", "protocol", "is_bodyweight")

logger = logging.getLogger(__name__)

_LBS_PER_KG = 2.20462
_KG_PER_LB = 0.453592


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {k: row[k] for k in row.keys()}


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open a connection with foreign keys enabled and Row factory."""
    conn = sqlite3.connect(str(db_path), detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _migrate(conn: sqlite3.Connection) -> None:
    """Add columns introduced after the initial schema deploy. SQLite-safe."""
    migrations = [
        ("exercises", "muscle_tags", "TEXT"),
        ("exercises", "deleted_at", "TEXT"),
        ("workouts", "deleted_at", "TEXT"),
        ("sets", "deleted_at", "TEXT"),
        ("sets", "group_id", "ALTER TABLE sets ADD COLUMN group_id TEXT"),
        ("sets", "protocol", "ALTER TABLE sets ADD COLUMN protocol TEXT"),
        (
            "sets",
            "is_bodyweight",
            "ALTER TABLE sets ADD COLUMN is_bodyweight INTEGER NOT NULL DEFAULT 0",
        ),
    ]
    for table, column, sql in migrations:
        existing = {
            row[1] for row in conn.execute(f"PRAGMA table_info({table})").fetchall()
        }
        if column not in existing:
            conn.execute(sql)
    conn.commit()


def init_db(conn: sqlite3.Connection) -> None:
    """Create tables if missing, then apply column migrations. Idempotent."""
    schema = resources.files("workout_tracker").joinpath("schema.sql").read_text()
    conn.executescript(schema)
    _migrate(conn)
    conn.commit()


class WorkoutRepository:
    """All persistence operations live here. Tests inject an in-memory conn."""

    def __init__(self, conn: sqlite3.Connection) -> None:
        self.conn = conn

    @contextmanager
    def _tx(self) -> Iterator[sqlite3.Cursor]:
        cur = self.conn.cursor()
        try:
            yield cur
            self.conn.commit()
        except Exception:
            self.conn.rollback()
            raise
        finally:
            cur.close()

    # ---- Exercises ---------------------------------------------------------

    def get_or_create_exercise(self, name: str) -> Exercise:
        """Return existing exercise (matched by normalized name) or insert."""
        clean = name.strip()
        if not clean:
            raise ValueError("Exercise name cannot be empty")
        norm = normalize_name(clean)
        row = self.conn.execute(
            "SELECT * FROM exercises WHERE normalized_name = ? AND deleted_at IS NULL",
            (norm,),
        ).fetchone()
        if row is not None:
            return self._row_to_exercise(row)
        with self._tx() as cur:
            cur.execute(
                "INSERT INTO exercises (name, normalized_name) VALUES (?, ?)",
                (clean, norm),
            )
            ex_id = cur.lastrowid
        row = self.conn.execute(
            "SELECT * FROM exercises WHERE id = ?", (ex_id,)
        ).fetchone()
        return self._row_to_exercise(row)

    def _find_exercise_by_normalized(self, normalized: str) -> Exercise | None:
        """Find exercise by normalized name including soft-deleted. Used by import."""
        if not normalized:
            return None
        row = self.conn.execute(
            "SELECT * FROM exercises WHERE normalized_name = ?",
            (normalized,),
        ).fetchone()
        return self._row_to_exercise(row) if row is not None else None

    def list_exercises(self) -> list[Exercise]:
        rows = self.conn.execute(
            "SELECT * FROM exercises WHERE deleted_at IS NULL "
            "ORDER BY use_count DESC, name ASC"
        ).fetchall()
        return [self._row_to_exercise(r) for r in rows]

    def rename_exercise(self, exercise_id: int, new_name: str) -> Exercise:
        clean = new_name.strip()
        if not clean:
            raise ValueError("Exercise name cannot be empty")
        norm = normalize_name(clean)
        with self._tx() as cur:
            cur.execute(
                "UPDATE exercises SET name = ?, normalized_name = ? WHERE id = ?",
                (clean, norm, exercise_id),
            )
        row = self.conn.execute(
            "SELECT * FROM exercises WHERE id = ?", (exercise_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"exercise {exercise_id} not found")
        return self._row_to_exercise(row)

    def update_exercise_tags(self, exercise_id: int, tags: str | None) -> Exercise:
        """Set muscle_tags on an exercise. Pass None or '' to clear."""
        value = tags.strip() if tags else None
        with self._tx() as cur:
            cur.execute(
                "UPDATE exercises SET muscle_tags = ? WHERE id = ?",
                (value or None, exercise_id),
            )
        row = self.conn.execute(
            "SELECT * FROM exercises WHERE id = ?", (exercise_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"exercise {exercise_id} not found")
        return self._row_to_exercise(row)

    def merge_exercise(self, source_id: int, target_id: int) -> None:
        """Reassign sets from source -> target, hard-delete source."""
        if source_id == target_id:
            return
        with self._tx() as cur:
            cur.execute(
                "UPDATE sets SET exercise_id = ? WHERE exercise_id = ?",
                (target_id, source_id),
            )
            cur.execute(
                "UPDATE exercises SET use_count = use_count + "
                "(SELECT use_count FROM exercises WHERE id = ?) WHERE id = ?",
                (source_id, target_id),
            )
            cur.execute("DELETE FROM exercises WHERE id = ?", (source_id,))

    def resolve_exercise_by_name(self, name: str) -> Exercise | None:
        """Look up an exercise by normalized name. Returns None if not found."""
        norm = normalize_name(name)
        row = self.conn.execute(
            "SELECT * FROM exercises WHERE normalized_name = ?",
            (norm,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_exercise(row)

    def last_session_sets(self, exercise_id: int, limit: int = 10) -> list[WorkoutSet]:
        """Return most-recent executed sets for an exercise (last session only)."""
        # Find the most recent workout date that has executed sets for this exercise
        row = self.conn.execute(
            "SELECT w.date FROM workouts w "
            "JOIN sets s ON s.workout_id = w.id "
            "WHERE s.exercise_id = ? AND s.executed = 1 "
            "ORDER BY w.date DESC, w.id DESC LIMIT 1",
            (exercise_id,),
        ).fetchone()
        if row is None:
            return []
        last_date = row["date"]
        rows = self.conn.execute(
            "SELECT s.*, e.name AS exercise_name FROM sets s "
            "JOIN exercises e ON e.id = s.exercise_id "
            "JOIN workouts w ON w.id = s.workout_id "
            "WHERE s.exercise_id = ? AND s.executed = 1 AND w.date = ? "
            "ORDER BY w.id DESC, s.position ASC LIMIT ?",
            (exercise_id, last_date, limit),
        ).fetchall()
        return [self._row_to_set(r) for r in rows]

    def delete_exercise(self, exercise_id: int) -> None:
        """Soft-delete exercise and all its sets."""
        now = datetime.utcnow().isoformat(timespec="seconds")
        with self._tx() as cur:
            cur.execute(
                "UPDATE sets SET deleted_at = ?"
                " WHERE exercise_id = ? AND deleted_at IS NULL",
                (now, exercise_id),
            )
            cur.execute(
                "UPDATE exercises SET deleted_at = ? WHERE id = ?",
                (now, exercise_id),
            )

    def restore_exercise(self, exercise_id: int) -> None:
        """Restore a soft-deleted exercise and its sets."""
        with self._tx() as cur:
            cur.execute(
                "UPDATE exercises SET deleted_at = NULL WHERE id = ?",
                (exercise_id,),
            )
            cur.execute(
                "UPDATE sets SET deleted_at = NULL WHERE exercise_id = ?",
                (exercise_id,),
            )

    def bulk_rename_exercises(self, renames: dict[int, str]) -> None:
        """Rename multiple exercises atomically. renames = {exercise_id: new_name}."""
        if not renames:
            return
        with self._tx() as cur:
            for ex_id, new_name in renames.items():
                clean = new_name.strip()
                if not clean:
                    raise ValueError(f"New name for exercise {ex_id} cannot be empty")
                norm = normalize_name(clean)
                cur.execute(
                    "UPDATE exercises SET name = ?, normalized_name = ? WHERE id = ?",
                    (clean, norm, ex_id),
                )

    def bulk_merge_exercises(self, source_ids: list[int], target_id: int) -> None:
        """Merge multiple source exercises into target (hard-delete sources)."""
        for src_id in source_ids:
            self.merge_exercise(src_id, target_id)

    def convert_sets_unit(
        self, set_ids: list[int], from_unit: str, to_unit: str
    ) -> None:
        """Convert weight values for the given sets from one unit to another.

        Only sets that currently have unit == from_unit are modified.
        Raises ValueError for same-unit or unsupported units.
        """
        if from_unit == to_unit:
            raise ValueError("from_unit and to_unit must differ")
        if from_unit not in ("lbs", "kg") or to_unit not in ("lbs", "kg"):
            raise ValueError("units must be 'lbs' or 'kg'")

        factor = _KG_PER_LB if from_unit == "lbs" else _LBS_PER_KG

        with self._tx() as cur:
            for sid in set_ids:
                row = self.conn.execute(
                    "SELECT unit, planned_weight, actual_weight FROM sets WHERE id = ?",
                    (sid,),
                ).fetchone()
                if row is None or row["unit"] != from_unit:
                    continue
                pw = row["planned_weight"]
                aw = row["actual_weight"]
                new_pw = round(pw * factor, 3) if pw is not None else None
                new_aw = round(aw * factor, 3) if aw is not None else None
                cur.execute(
                    "UPDATE sets SET unit = ?,"
                    " planned_weight = ?, actual_weight = ? WHERE id = ?",
                    (to_unit, new_pw, new_aw, sid),
                )

    # ---- Aliases -------------------------------------------------------

    def add_alias(self, exercise_id: int, alias: str) -> ExerciseAlias:
        norm = normalize_name(alias)
        with self._tx() as cur:
            cur.execute(
                "INSERT INTO exercise_aliases (exercise_id, alias, normalized_alias) "
                "VALUES (?, ?, ?)",
                (exercise_id, alias, norm),
            )
            alias_id = cur.lastrowid
        row = self.conn.execute(
            "SELECT * FROM exercise_aliases WHERE id = ?", (alias_id,)
        ).fetchone()
        return self._row_to_alias(row)

    def delete_alias(self, alias_id: int) -> None:
        with self._tx() as cur:
            cur.execute("DELETE FROM exercise_aliases WHERE id = ?", (alias_id,))

    def list_aliases(self, exercise_id: int) -> list[ExerciseAlias]:
        rows = self.conn.execute(
            "SELECT * FROM exercise_aliases WHERE exercise_id = ? ORDER BY alias ASC",
            (exercise_id,),
        ).fetchall()
        return [self._row_to_alias(r) for r in rows]

    def resolve_alias(self, alias: str) -> Exercise | None:
        norm = normalize_name(alias)
        row = self.conn.execute(
            "SELECT e.* FROM exercises e "
            "JOIN exercise_aliases a ON a.exercise_id = e.id "
            "WHERE a.normalized_alias = ? AND e.deleted_at IS NULL",
            (norm,),
        ).fetchone()
        if row is None:
            return None
        return self._row_to_exercise(row)

    @staticmethod
    def _row_to_alias(row: sqlite3.Row) -> ExerciseAlias:
        return ExerciseAlias(
            id=row["id"],
            exercise_id=row["exercise_id"],
            alias=row["alias"],
            normalized_alias=row["normalized_alias"],
            created_at=row["created_at"],
        )

    def _bump_exercise(self, cur: sqlite3.Cursor, exercise_id: int) -> None:
        cur.execute(
            "UPDATE exercises SET use_count = use_count + 1, "
            "last_used_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(timespec="seconds"), exercise_id),
        )

    # ---- Workouts ----------------------------------------------------------

    def create_workout(
        self,
        date: str,
        title: str | None = None,
        notes: str | None = None,
        status: str = "planned",
    ) -> Workout:
        with self._tx() as cur:
            cur.execute(
                "INSERT INTO workouts (date, title, notes, status) VALUES (?, ?, ?, ?)",
                (date, title, notes, status),
            )
            w_id = cur.lastrowid
        assert w_id is not None
        return self.get_workout(w_id)

    def get_workout(self, workout_id: int) -> Workout:
        row = self.conn.execute(
            "SELECT * FROM workouts WHERE id = ? AND deleted_at IS NULL",
            (workout_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"workout {workout_id} not found")
        sets = self._workout_sets(workout_id)
        w = self._row_to_workout(row)
        w.sets = sets
        return w

    def list_workouts(self, limit: int = 50) -> list[Workout]:
        rows = self.conn.execute(
            "SELECT * FROM workouts WHERE deleted_at IS NULL "
            "ORDER BY date DESC, id DESC LIMIT ?",
            (limit,),
        ).fetchall()
        result: list[Workout] = []
        for r in rows:
            w = self._row_to_workout(r)
            w.sets = self._workout_sets(w.id or 0)
            result.append(w)
        return result

    def update_workout(
        self,
        workout_id: int,
        *,
        date: str | None = None,
        title: str | None = None,
        notes: str | None = None,
        status: str | None = None,
    ) -> Workout:
        existing = self.get_workout(workout_id)
        new_date = date if date is not None else existing.date
        new_title = title if title is not None else existing.title
        new_notes = notes if notes is not None else existing.notes
        new_status = status if status is not None else existing.status
        with self._tx() as cur:
            cur.execute(
                "UPDATE workouts SET date = ?, title = ?, notes = ?, "
                "status = ?, updated_at = datetime('now') WHERE id = ?",
                (new_date, new_title, new_notes, new_status, workout_id),
            )
        return self.get_workout(workout_id)

    def delete_workout(self, workout_id: int) -> None:
        """Soft-delete workout and all its sets."""
        now = datetime.utcnow().isoformat(timespec="seconds")
        with self._tx() as cur:
            cur.execute(
                "UPDATE sets SET deleted_at = ?"
                " WHERE workout_id = ? AND deleted_at IS NULL",
                (now, workout_id),
            )
            cur.execute(
                "UPDATE workouts SET deleted_at = ? WHERE id = ?",
                (now, workout_id),
            )

    def search_workouts(
        self,
        exercise_name: str | None = None,
        date_from: str | None = None,
        date_to: str | None = None,
        min_weight: float | None = None,
        status: str | None = None,
    ) -> list[Workout]:
        if status is not None and status not in VALID_STATUSES:
            raise ValueError(f"status must be one of {VALID_STATUSES}")
        conditions: list[str] = []
        params: list[Any] = []
        if exercise_name is not None:
            norm = "%" + normalize_name(exercise_name) + "%"
            conditions.append(
                "w.id IN (SELECT s.workout_id FROM sets s "
                "JOIN exercises e ON e.id = s.exercise_id "
                "WHERE e.normalized_name LIKE ?)"
            )
            params.append(norm)
        if date_from is not None:
            conditions.append("w.date >= ?")
            params.append(date_from)
        if date_to is not None:
            conditions.append("w.date <= ?")
            params.append(date_to)
        if min_weight is not None:
            conditions.append(
                "w.id IN (SELECT s.workout_id FROM sets s WHERE s.actual_weight >= ?)"
            )
            params.append(min_weight)
        if status is not None:
            conditions.append("w.status = ?")
            params.append(status)
        where = ""
        if conditions:
            where = "WHERE " + " AND ".join(conditions)
        sql = (  # noqa: S608
            f"SELECT w.* FROM workouts w {where} "
            "ORDER BY w.date DESC, w.id DESC LIMIT 200"
        )
        rows = self.conn.execute(sql, params).fetchall()
        result: list[Workout] = []
        for r in rows:
            w = self._row_to_workout(r)
            w.sets = self._workout_sets(w.id or 0)
            result.append(w)
        return result

    def restore_workout(self, workout_id: int) -> None:
        """Restore a soft-deleted workout and its sets."""
        with self._tx() as cur:
            cur.execute(
                "UPDATE workouts SET deleted_at = NULL WHERE id = ?",
                (workout_id,),
            )
            cur.execute(
                "UPDATE sets SET deleted_at = NULL WHERE workout_id = ?",
                (workout_id,),
            )

    # ---- Sets --------------------------------------------------------------

    def add_set(self, s: WorkoutSet) -> WorkoutSet:
        if s.position is None or s.position < 0:
            row = self.conn.execute(
                "SELECT COALESCE(MAX(position), -1) + 1 AS next "
                "FROM sets WHERE workout_id = ? AND deleted_at IS NULL",
                (s.workout_id,),
            ).fetchone()
            s.position = row["next"]
        if s.executed and not s.completed_at:
            s.completed_at = datetime.utcnow().isoformat(timespec="seconds")
        with self._tx() as cur:
            cur.execute(
                "INSERT INTO sets (workout_id, exercise_id, position, "
                "planned_reps, planned_weight, actual_reps, actual_weight, "
                "rpe, unit, executed, notes, completed_at, "
                "group_id, protocol, is_bodyweight) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    s.workout_id,
                    s.exercise_id,
                    s.position,
                    s.planned_reps,
                    s.planned_weight,
                    s.actual_reps,
                    s.actual_weight,
                    s.rpe,
                    s.unit,
                    int(bool(s.executed)),
                    s.notes,
                    s.completed_at,
                    s.group_id,
                    s.protocol,
                    int(bool(s.is_bodyweight)),
                ),
            )
            set_id = cur.lastrowid
            assert set_id is not None
            if s.executed:
                self._bump_exercise(cur, s.exercise_id)
        return self.get_set(set_id)

    def get_set(self, set_id: int) -> WorkoutSet:
        row = self.conn.execute(
            "SELECT s.*, e.name AS exercise_name FROM sets s "
            "JOIN exercises e ON e.id = s.exercise_id "
            "WHERE s.id = ? AND s.deleted_at IS NULL",
            (set_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"set {set_id} not found")
        return self._row_to_set(row)

    def update_set(self, set_id: int, **fields: Any) -> WorkoutSet:
        allowed = {
            "planned_reps",
            "planned_weight",
            "actual_reps",
            "actual_weight",
            "rpe",
            "unit",
            "executed",
            "notes",
            "completed_at",
            "position",
            "exercise_id",
            "group_id",
            "protocol",
            "is_bodyweight",
        }
        unknown = set(fields) - allowed
        if unknown:
            raise ValueError(f"unknown set fields: {unknown}")
        if not fields:
            return self.get_set(set_id)
        was_executed = self.get_set(set_id).executed
        cols = ", ".join(f"{k} = ?" for k in fields)
        values = list(fields.values())
        # Coerce executed -> int
        if "executed" in fields:
            idx = list(fields).index("executed")
            values[idx] = int(bool(values[idx]))
            if values[idx] and not fields.get("completed_at"):
                # auto-stamp completion when marking executed
                cols += ", completed_at = ?"
                values.append(datetime.utcnow().isoformat(timespec="seconds"))
        with self._tx() as cur:
            cur.execute(
                f"UPDATE sets SET {cols} WHERE id = ?",  # noqa: S608 (cols are whitelisted)
                (*values, set_id),
            )
            if fields.get("executed") and not was_executed:
                ex_id = self.get_set(set_id).exercise_id
                self._bump_exercise(cur, ex_id)
        return self.get_set(set_id)

    def delete_set(self, set_id: int) -> None:
        """Soft-delete a single set."""
        now = datetime.utcnow().isoformat(timespec="seconds")
        with self._tx() as cur:
            cur.execute(
                "UPDATE sets SET deleted_at = ? WHERE id = ?",
                (now, set_id),
            )

    def restore_set(self, set_id: int) -> None:
        """Restore a soft-deleted set."""
        with self._tx() as cur:
            cur.execute(
                "UPDATE sets SET deleted_at = NULL WHERE id = ?",
                (set_id,),
            )

    def list_sets_for_exercise(
        self, exercise_id: int, executed_only: bool = True
    ) -> list[WorkoutSet]:
        sql = (
            "SELECT s.*, e.name AS exercise_name, w.date AS _wdate "
            "FROM sets s "
            "JOIN exercises e ON e.id = s.exercise_id "
            "JOIN workouts w ON w.id = s.workout_id "
            "WHERE s.exercise_id = ? AND s.deleted_at IS NULL"
        )
        params: tuple[Any, ...] = (exercise_id,)
        if executed_only:
            sql += " AND s.executed = 1"
        sql += " ORDER BY w.date ASC, s.position ASC"
        rows = self.conn.execute(sql, params).fetchall()
        return [self._row_to_set(r) for r in rows]

    def list_all_executed_sets(self) -> list[WorkoutSet]:
        rows = self.conn.execute(
            "SELECT s.*, e.name AS exercise_name FROM sets s "
            "JOIN exercises e ON e.id = s.exercise_id "
            "WHERE s.executed = 1 AND s.deleted_at IS NULL"
        ).fetchall()
        return [self._row_to_set(r) for r in rows]

    # ---- Trash -------------------------------------------------------------

    def list_trash(self) -> dict[str, list[dict[str, Any]]]:
        """Return all soft-deleted items within the 30-day recovery window."""
        exercises = [
            _row_to_dict(r)
            for r in self.conn.execute(
                "SELECT * FROM exercises WHERE deleted_at IS NOT NULL "
                "AND deleted_at >= datetime('now', '-30 days')"
            ).fetchall()
        ]
        workouts = [
            _row_to_dict(r)
            for r in self.conn.execute(
                "SELECT * FROM workouts WHERE deleted_at IS NOT NULL "
                "AND deleted_at >= datetime('now', '-30 days')"
            ).fetchall()
        ]
        sets = [
            _row_to_dict(r)
            for r in self.conn.execute(
                "SELECT * FROM sets WHERE deleted_at IS NOT NULL "
                "AND deleted_at >= datetime('now', '-30 days')"
            ).fetchall()
        ]
        return {"exercises": exercises, "workouts": workouts, "sets": sets}

    def purge_trash(self) -> None:
        """Hard-delete all soft-deleted items (regardless of age)."""
        with self._tx() as cur:
            cur.execute("DELETE FROM sets WHERE deleted_at IS NOT NULL")
            cur.execute("DELETE FROM workouts WHERE deleted_at IS NOT NULL")
            cur.execute("DELETE FROM exercises WHERE deleted_at IS NOT NULL")

    # ---- Mappers -----------------------------------------------------------

    def _workout_sets(self, workout_id: int) -> list[WorkoutSet]:
        rows = self.conn.execute(
            "SELECT s.*, e.name AS exercise_name FROM sets s "
            "JOIN exercises e ON e.id = s.exercise_id "
            "WHERE s.workout_id = ? AND s.deleted_at IS NULL ORDER BY s.position ASC",
            (workout_id,),
        ).fetchall()
        return [self._row_to_set(r) for r in rows]

    @staticmethod
    def _row_to_exercise(row: sqlite3.Row) -> Exercise:
        keys = row.keys()
        return Exercise(
            id=row["id"],
            name=row["name"],
            normalized_name=row["normalized_name"],
            use_count=row["use_count"],
            last_used_at=row["last_used_at"],
            muscle_tags=row["muscle_tags"] if "muscle_tags" in keys else None,
            created_at=row["created_at"],
        )

    @staticmethod
    def _row_to_workout(row: sqlite3.Row) -> Workout:
        return Workout(
            id=row["id"],
            date=row["date"],
            title=row["title"],
            notes=row["notes"],
            status=row["status"],
            created_at=row["created_at"],
            updated_at=row["updated_at"],
        )

    @staticmethod
    def _row_to_set(row: sqlite3.Row) -> WorkoutSet:
        keys = row.keys()
        return WorkoutSet(
            id=row["id"],
            workout_id=row["workout_id"],
            exercise_id=row["exercise_id"],
            position=row["position"],
            planned_reps=row["planned_reps"],
            planned_weight=row["planned_weight"],
            actual_reps=row["actual_reps"],
            actual_weight=row["actual_weight"],
            rpe=row["rpe"],
            unit=row["unit"],
            executed=bool(row["executed"]),
            notes=row["notes"],
            completed_at=row["completed_at"],
            exercise_name=row["exercise_name"] if "exercise_name" in keys else None,
            group_id=row["group_id"] if "group_id" in keys else None,
            protocol=row["protocol"] if "protocol" in keys else None,
            is_bodyweight=(
                bool(row["is_bodyweight"]) if "is_bodyweight" in keys else False
            ),
        )
