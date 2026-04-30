"""SQLite repository layer.

Repository pattern keeps Law of Demeter clean: callers ask the repo, the repo
talks to sqlite. No raw SQL leaks into routes/services.
"""

from __future__ import annotations

import logging
import sqlite3
from importlib import resources
from pathlib import Path
from typing import Any

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
    _migrate_sets_exercise_fk(conn)
    conn.commit()


def _migrate_sets_exercise_fk(conn: sqlite3.Connection) -> None:
    """Rebuild legacy sets tables so exercise deletes cascade.

    Older databases were created before ``sets.exercise_id`` used
    ``ON DELETE CASCADE``. SQLite cannot alter a foreign key action in place,
    so upgraded databases need a one-time table rebuild.
    """

    exists = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = 'sets'"
    ).fetchone()
    if exists is None:
        return

    fk_rows = conn.execute("PRAGMA foreign_key_list(sets)").fetchall()
    needs_migration = not any(
        row[2] == "exercises"
        and row[3] == "exercise_id"
        and row[4] == "id"
        and row[6] == "CASCADE"
        for row in fk_rows
    )
    if not needs_migration:
        return

    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute("BEGIN IMMEDIATE")
        conn.execute("""
            CREATE TABLE sets_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                workout_id INTEGER NOT NULL,
                exercise_id INTEGER NOT NULL,
                position INTEGER NOT NULL,
                planned_reps INTEGER,
                planned_weight REAL,
                actual_reps INTEGER,
                actual_weight REAL,
                rpe REAL,
                unit TEXT NOT NULL DEFAULT 'lbs',
                executed INTEGER NOT NULL DEFAULT 0,
                notes TEXT,
                completed_at TEXT,
                FOREIGN KEY (workout_id) REFERENCES workouts(id) ON DELETE CASCADE,
                FOREIGN KEY (exercise_id) REFERENCES exercises(id) ON DELETE CASCADE
            )
            """)
        conn.execute("""
            INSERT INTO sets_new (
                id,
                workout_id,
                exercise_id,
                position,
                planned_reps,
                planned_weight,
                actual_reps,
                actual_weight,
                rpe,
                unit,
                executed,
                notes,
                completed_at
            )
            SELECT
                id,
                workout_id,
                exercise_id,
                position,
                planned_reps,
                planned_weight,
                actual_reps,
                actual_weight,
                rpe,
                unit,
                executed,
                notes,
                completed_at
            FROM sets
            """)
        conn.execute("DROP TABLE sets")
        conn.execute("ALTER TABLE sets_new RENAME TO sets")
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sets_workout ON sets(workout_id, position)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_sets_exercise ON sets(exercise_id)"
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sets_executed ON sets(executed)")
        conn.execute("""
            INSERT OR REPLACE INTO sqlite_sequence(name, seq)
            SELECT 'sets', COALESCE(MAX(id), 0) FROM sets
            """)
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.execute("PRAGMA foreign_keys = ON")
