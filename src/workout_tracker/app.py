"""Flask application factory + route registration.

Architecture:
  - All persistence goes through `g.repo` (a WorkoutRepository).
  - Templates render the SPA shell; the JS app calls /api/* endpoints.
  - Connection lifecycle is request-scoped (per-request open/close).

Run locally:
    FLASK_APP=workout_tracker:create_app flask run
or:
    python -m workout_tracker
"""

from __future__ import annotations

import logging
import os
from collections.abc import Callable
from contextlib import closing
from datetime import date as date_t
from pathlib import Path
from typing import Any, ParamSpec, Protocol, TypeVar, cast

from flask import Flask, abort, g, jsonify, render_template, request

from workout_tracker import autocomplete, parser, stats
from workout_tracker.db import WorkoutRepository, connect, init_db
from workout_tracker.models import WorkoutSet

logger = logging.getLogger(__name__)


DEFAULT_DB_PATH = os.environ.get(
    "WORKOUT_DB_PATH", str(Path.home() / ".workout_tracker.db")
)

P = ParamSpec("P")
R = TypeVar("R")


class _FlaskApp(Protocol):
    config: dict[str, Any]

    def before_request(self, func: Callable[P, R]) -> Callable[P, R]: ...

    def teardown_request(self, func: Callable[P, R]) -> Callable[P, R]: ...

    def errorhandler(self, code: int) -> Callable[[Callable[P, R]], Callable[P, R]]: ...

    def get(self, rule: str) -> Callable[[Callable[P, R]], Callable[P, R]]: ...

    def post(self, rule: str) -> Callable[[Callable[P, R]], Callable[P, R]]: ...

    def put(self, rule: str) -> Callable[[Callable[P, R]], Callable[P, R]]: ...

    def delete(self, rule: str) -> Callable[[Callable[P, R]], Callable[P, R]]: ...

    def test_client(self) -> Any: ...

    def run(self, *args: Any, **kwargs: Any) -> Any: ...


def create_app(db_path: str | None = None) -> _FlaskApp:
    app = cast(_FlaskApp, Flask(__name__))
    app.config["DB_PATH"] = db_path or DEFAULT_DB_PATH
    app.config["JSON_SORT_KEYS"] = False

    # Initialize the schema once at startup
    with closing(connect(app.config["DB_PATH"])) as conn:
        init_db(conn)
    _log_startup_diagnostic(app.config["DB_PATH"])

    @app.before_request
    def _open_conn() -> None:
        g.conn = connect(app.config["DB_PATH"])
        g.repo = WorkoutRepository(g.conn)

    @app.teardown_request
    def _close_conn(exc: BaseException | None) -> None:
        conn = g.pop("conn", None)
        if conn is not None:
            conn.close()

    register_routes(app)
    return app


# --------------------------------------------------------------------- routes


def register_routes(app: _FlaskApp) -> None:
    @app.get("/")
    def index() -> Any:
        return render_template("index.html")

    @app.get("/api/health")
    def health() -> Any:
        g.conn.execute("SELECT 1").fetchone()
        logger.info(
            "workout_tracker_health_check",
            extra={
                "status": "ok",
                "database": "reachable",
                "db_path": app.config["DB_PATH"],
            },
        )
        return jsonify({"status": "ok", "database": "reachable"})

    # ---------- exercises ----------

    @app.get("/api/exercises")
    def list_exercises() -> Any:
        repo: WorkoutRepository = g.repo
        return jsonify([e.to_dict() for e in repo.list_exercises()])

    @app.get("/api/exercises/suggest")
    def suggest_exercises() -> Any:
        repo: WorkoutRepository = g.repo
        q = request.args.get("q", "")
        limit = int(request.args.get("limit", 8))
        catalog = repo.list_exercises()
        results = autocomplete.suggest(q, catalog, limit=limit)
        return jsonify([e.to_dict() for e in results])

    @app.get("/api/exercises/last_session")
    def exercise_last_session() -> Any:
        """Return the most recent previous session's executed sets for an
        exercise, keyed by either `q` (name) or `id`. Excludes the workout
        with id `exclude` so the currently-active workout isn't returned as
        its own "last session".

        Response: `{date, exercise_name, sets: [{reps, weight, unit, rpe}]}`
        or `{date: null, sets: []}` when no prior session exists.
        """
        repo: WorkoutRepository = g.repo
        q = (request.args.get("q") or "").strip()
        ex_id_str = request.args.get("id")
        exclude_raw = request.args.get("exclude")
        exclude_id = int(exclude_raw) if exclude_raw and exclude_raw.isdigit() else None

        ex = None
        if ex_id_str and ex_id_str.isdigit():
            ex_id = int(ex_id_str)
            ex = next((e for e in repo.list_exercises() if e.id == ex_id), None)
        elif q:
            norm = q.lower()
            for e in repo.list_exercises():
                if e.name.lower() == norm:
                    ex = e
                    break
        if ex is None or ex.id is None:
            return jsonify({"date": None, "exercise_name": q, "sets": []})

        sets_for = repo.list_sets_for_exercise(ex.id, executed_only=True)
        # Group by workout and pick the most recent that isn't `exclude_id`.
        by_workout: dict[int, list[Any]] = {}
        for s in sets_for:
            if exclude_id is not None and s.workout_id == exclude_id:
                continue
            by_workout.setdefault(s.workout_id, []).append(s)
        if not by_workout:
            return jsonify({"date": None, "exercise_name": ex.name, "sets": []})
        # Direct per-workout lookup — no arbitrary cap (fixes issue #330).
        # Guard against stale set references with KeyError fallback.
        workout_dates = {}
        for wid in by_workout:
            try:
                workout_dates[wid] = repo.get_workout(wid).date
            except KeyError:
                pass
        if not workout_dates:
            return jsonify({"date": None, "exercise_name": ex.name, "sets": []})
        best_wid = max(workout_dates.keys(), key=lambda wid: workout_dates[wid])
        last_sets = by_workout[best_wid]
        return jsonify(
            {
                "date": workout_dates[best_wid],
                "exercise_name": ex.name,
                "sets": [
                    {
                        "reps": s.actual_reps,
                        "weight": s.actual_weight,
                        "unit": s.unit,
                        "rpe": s.rpe,
                    }
                    for s in last_sets
                ],
            }
        )

    @app.post("/api/exercises")
    def create_exercise() -> Any:
        repo: WorkoutRepository = g.repo
        data = request.get_json(force=True) or {}
        name = (data.get("name") or "").strip()
        if not name:
            abort(400, "name required")
        ex = repo.get_or_create_exercise(name)
        return jsonify(ex.to_dict()), 201

    @app.put("/api/exercises/<int:ex_id>")
    def rename_exercise(ex_id: int) -> Any:
        repo: WorkoutRepository = g.repo
        data = request.get_json(force=True) or {}
        name = (data.get("name") or "").strip()
        if not name:
            abort(400, "name required")
        ex = repo.rename_exercise(ex_id, name)
        return jsonify(ex.to_dict())

    @app.post("/api/exercises/<int:source_id>/merge_into/<int:target_id>")
    def merge_exercises(source_id: int, target_id: int) -> Any:
        repo: WorkoutRepository = g.repo
        repo.merge_exercise(source_id, target_id)
        return jsonify({"ok": True})

    @app.delete("/api/exercises/<int:ex_id>")
    def delete_exercise(ex_id: int) -> Any:
        repo: WorkoutRepository = g.repo
        repo.delete_exercise(ex_id)
        return jsonify({"ok": True})

    # ---------- workouts ----------

    @app.get("/api/workouts")
    def list_workouts() -> Any:
        repo: WorkoutRepository = g.repo
        limit = int(request.args.get("limit", 50))
        ws = repo.list_workouts(limit=limit)
        return jsonify([w.to_dict() for w in ws])

    @app.post("/api/workouts")
    def create_workout() -> Any:
        repo: WorkoutRepository = g.repo
        data = request.get_json(force=True) or {}
        date = data.get("date") or date_t.today().isoformat()
        title = data.get("title")
        notes = data.get("notes")
        status = data.get("status", "planned")
        try:
            w = repo.create_workout(date=date, title=title, notes=notes, status=status)
        except ValueError as e:
            abort(400, str(e))
        return jsonify(w.to_dict()), 201

    @app.get("/api/workouts/<int:w_id>")
    def get_workout(w_id: int) -> Any:
        repo: WorkoutRepository = g.repo
        try:
            return jsonify(repo.get_workout(w_id).to_dict())
        except KeyError:
            abort(404)

    @app.put("/api/workouts/<int:w_id>")
    def update_workout(w_id: int) -> Any:
        repo: WorkoutRepository = g.repo
        data = request.get_json(force=True) or {}
        try:
            w = repo.update_workout(
                w_id,
                date=data.get("date"),
                title=data.get("title"),
                notes=data.get("notes"),
                status=data.get("status"),
            )
        except KeyError:
            abort(404)
        except ValueError as e:
            abort(400, str(e))
        return jsonify(w.to_dict())

    @app.delete("/api/workouts/<int:w_id>")
    def delete_workout(w_id: int) -> Any:
        repo: WorkoutRepository = g.repo
        repo.delete_workout(w_id)
        return jsonify({"ok": True})

    # ---------- sets ----------

    @app.post("/api/workouts/<int:w_id>/sets")
    def add_set(w_id: int) -> Any:
        repo: WorkoutRepository = g.repo
        data = request.get_json(force=True) or {}
        ex_name = (data.get("exercise_name") or "").strip()
        ex_id = data.get("exercise_id")
        if not ex_id:
            if not ex_name:
                abort(400, "exercise_id or exercise_name required")
            try:
                ex_id = repo.get_or_create_exercise(ex_name).id
            except ValueError as e:
                abort(400, str(e))
        assert ex_id is not None
        try:
            s = WorkoutSet(
                workout_id=w_id,
                exercise_id=int(ex_id),
                position=int(data.get("position", -1)),
                planned_reps=data.get("planned_reps"),
                planned_weight=data.get("planned_weight"),
                actual_reps=data.get("actual_reps"),
                actual_weight=data.get("actual_weight"),
                rpe=data.get("rpe"),
                unit=data.get("unit", "lbs"),
                executed=bool(data.get("executed", False)),
                notes=data.get("notes"),
            )
        except ValueError as e:
            abort(400, str(e))
        return jsonify(repo.add_set(s).to_dict()), 201

    @app.put("/api/sets/<int:set_id>")
    def update_set(set_id: int) -> Any:
        repo: WorkoutRepository = g.repo
        data = request.get_json(force=True) or {}
        try:
            s = repo.update_set(set_id, **data)
        except KeyError:
            abort(404)
        except ValueError as e:
            abort(400, str(e))
        return jsonify(s.to_dict())

    @app.delete("/api/sets/<int:set_id>")
    def delete_set(set_id: int) -> Any:
        repo: WorkoutRepository = g.repo
        repo.delete_set(set_id)
        return jsonify({"ok": True})

    # ---------- parser ----------

    @app.post("/api/parse")
    def parse_text() -> Any:
        data = request.get_json(force=True) or {}
        text = data.get("text", "")
        entries = parser.parse_notes(text)
        return jsonify(
            [
                {
                    "exercise_name": e.exercise_name,
                    "sets": [
                        {
                            "reps": s.reps,
                            "weight": s.weight,
                            "rpe": s.rpe,
                            "unit": s.unit,
                        }
                        for s in e.sets
                    ],
                }
                for e in entries
            ]
        )

    @app.post("/api/workouts/<int:w_id>/import")
    def import_text_into_workout(w_id: int) -> Any:
        """Parse text and append parsed sets to the workout (planned)."""
        repo: WorkoutRepository = g.repo
        data = request.get_json(force=True) or {}
        text = data.get("text", "")
        executed = bool(data.get("executed", False))
        created: list[dict[str, Any]] = []
        for entry in parser.parse_notes(text):
            ex = repo.get_or_create_exercise(entry.exercise_name)
            for ps in entry.sets:
                s = WorkoutSet(
                    workout_id=w_id,
                    exercise_id=ex.id or 0,
                    position=-1,
                    planned_reps=ps.reps if not executed else None,
                    planned_weight=ps.weight if not executed else None,
                    actual_reps=ps.reps if executed else None,
                    actual_weight=ps.weight if executed else None,
                    rpe=ps.rpe,
                    unit=ps.unit,
                    executed=executed,
                )
                created.append(repo.add_set(s).to_dict())
        return jsonify(created), 201

    # ---------- stats ----------

    @app.get("/api/stats/overview")
    def stats_overview() -> Any:
        repo: WorkoutRepository = g.repo
        all_sets = repo.list_all_executed_sets()
        ov = stats.overview(all_sets)
        summary = stats.per_exercise_summary(all_sets)
        prs = stats.personal_records(all_sets)
        freq = stats.frequency(all_sets)
        return jsonify(
            {
                "overview": ov.__dict__,
                "per_exercise": [s.to_dict() for s in summary],
                "personal_records": [p.__dict__ for p in prs],
                "frequency": [f.__dict__ for f in freq],
            }
        )

    @app.get("/api/stats/exercise/<int:ex_id>")
    def stats_exercise(ex_id: int) -> Any:
        repo: WorkoutRepository = g.repo
        sets_for = repo.list_sets_for_exercise(ex_id, executed_only=True)
        series = stats.exercise_timeseries(sets_for)
        prs = stats.personal_records(sets_for)
        return jsonify(
            {
                "timeseries": [tp.__dict__ for tp in series],
                "personal_records": [p.__dict__ for p in prs],
            }
        )

    # ---------- error handlers ----------

    @app.errorhandler(400)
    def _bad(err: Any) -> Any:
        return jsonify({"error": str(err.description)}), 400

    @app.errorhandler(404)
    def _missing(err: Any) -> Any:
        return jsonify({"error": "not found"}), 404


def _log_startup_diagnostic(db_path: str) -> None:
    db_file = Path(db_path)
    logger.info(
        "workout_tracker_startup",
        extra={
            "db_path": db_path,
            "db_ready": db_file.exists(),
            "db_size_bytes": db_file.stat().st_size if db_file.exists() else 0,
        },
    )
