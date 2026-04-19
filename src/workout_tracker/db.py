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
    Exercise,
    Workout,
    WorkoutSet,
    normalize_name,
)

logger = logging.getLogger(__name__)


def _row_to_dict(row: sqlite3.Row) -> dict[str, Any]:
    return {k: row[k] for k in row.keys()}


def connect(db_path: str | Path) -> sqlite3.Connection:
    """Open a connection with foreign keys enabled and Row factory."""
    conn = sqlite3.connect(str(db_path), detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db(conn: sqlite3.Connection) -> None:
    """Create tables if missing. Idempotent."""
    schema = resources.files("workout_tracker").joinpath("schema.sql").read_text()
    conn.executescript(schema)
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

    # ---- Exercises -----------------------------------------------------

    def get_or_create_exercise(self, name: str) -> Exercise:
        """Return existing exercise (matched by normalized name) or insert."""
        clean = name.strip()
        if not clean:
            raise ValueError("Exercise name cannot be empty")
        norm = normalize_name(clean)
        row = self.conn.execute(
            "SELECT * FROM exercises WHERE normalized_name = ?",
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

    def list_exercises(self) -> list[Exercise]:
        rows = self.conn.execute(
            "SELECT * FROM exercises ORDER BY use_count DESC, name ASC"
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

    def merge_exercise(self, source_id: int, target_id: int) -> None:
        """Reassign sets from source -> target, delete source. Typo fix helper."""
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

    def delete_exercise(self, exercise_id: int) -> None:
        with self._tx() as cur:
            cur.execute(
                "DELETE FROM sets WHERE exercise_id = ?", (exercise_id,)
            )
            cur.execute("DELETE FROM exercises WHERE id = ?", (exercise_id,))

    def _bump_exercise(self, cur: sqlite3.Cursor, exercise_id: int) -> None:
        cur.execute(
            "UPDATE exercises SET use_count = use_count + 1, "
            "last_used_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(timespec="seconds"), exercise_id),
        )

    # ---- Workouts ------------------------------------------------------

    def create_workout(
        self,
        date: str,
        title: str | None = None,
        notes: str | None = None,
        status: str = "planned",
    ) -> Workout:
        with self._tx() as cur:
            cur.execute(
                "INSERT INTO workouts (date, title, notes, status) "
                "VALUES (?, ?, ?, ?)",
                (date, title, notes, status),
            )
            w_id = cur.lastrowid
        assert w_id is not None
        return self.get_workout(w_id)

    def get_workout(self, workout_id: int) -> Workout:
        row = self.conn.execute(
            "SELECT * FROM workouts WHERE id = ?", (workout_id,)
        ).fetchone()
        if row is None:
            raise KeyError(f"workout {workout_id} not found")
        sets = self._workout_sets(workout_id)
        w = self._row_to_workout(row)
        w.sets = sets
        return w

    def list_workouts(self, limit: int = 50) -> list[Workout]:
        rows = self.conn.execute(
            "SELECT * FROM workouts ORDER BY date DESC, id DESC LIMIT ?",
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
        with self._tx() as cur:
            cur.execute("DELETE FROM workouts WHERE id = ?", (workout_id,))

    # ---- Sets ----------------------------------------------------------

    def add_set(self, s: WorkoutSet) -> WorkoutSet:
        if s.position is None or s.position < 0:
            row = self.conn.execute(
                "SELECT COALESCE(MAX(position), -1) + 1 AS next "
                "FROM sets WHERE workout_id = ?",
                (s.workout_id,),
            ).fetchone()
            s.position = row["next"]
        if s.executed and not s.completed_at:
            s.completed_at = datetime.utcnow().isoformat(timespec="seconds")
        with self._tx() as cur:
            cur.execute(
                "INSERT INTO sets (workout_id, exercise_id, position, "
                "planned_reps, planned_weight, actual_reps, actual_weight, "
                "rpe, unit, executed, notes, completed_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
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
            "JOIN exercises e ON e.id = s.exercise_id WHERE s.id = ?",
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
        with self._tx() as cur:
            cur.execute("DELETE FROM sets WHERE id = ?", (set_id,))

    def list_sets_for_exercise(
        self, exercise_id: int, executed_only: bool = True
    ) -> list[WorkoutSet]:
        sql = (
            "SELECT s.*, e.name AS exercise_name, w.date AS _wdate "
            "FROM sets s "
            "JOIN exercises e ON e.id = s.exercise_id "
            "JOIN workouts w ON w.id = s.workout_id "
            "WHERE s.exercise_id = ?"
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
            "WHERE s.executed = 1"
        ).fetchall()
        return [self._row_to_set(r) for r in rows]

    # ---- Mappers -------------------------------------------------------

    def _workout_sets(self, workout_id: int) -> list[WorkoutSet]:
        rows = self.conn.execute(
            "SELECT s.*, e.name AS exercise_name FROM sets s "
            "JOIN exercises e ON e.id = s.exercise_id "
            "WHERE s.workout_id = ? ORDER BY s.position ASC",
            (workout_id,),
        ).fetchall()
        return [self._row_to_set(r) for r in rows]

    @staticmethod
    def _row_to_exercise(row: sqlite3.Row) -> Exercise:
        return Exercise(
            id=row["id"],
            name=row["name"],
            normalized_name=row["normalized_name"],
            use_count=row["use_count"],
            last_used_at=row["last_used_at"],
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
            exercise_name=row["exercise_name"]
            if "exercise_name" in row.keys()
            else None,
        )
