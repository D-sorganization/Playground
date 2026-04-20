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
from datetime import date as date_t
from pathlib import Path
from typing import Any, ParamSpec, Protocol, TypeVar, cast

from flask import Flask, abort, g, jsonify, render_template, request

from workout_tracker import autocomplete, parser, planning, stats
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
    with connect(app.config["DB_PATH"]) as conn:
        init_db(conn)

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
        results = autocomplete.suggest(
            q, catalog, limit=limit, alias_resolver=repo.resolve_alias
        )
        return jsonify([e.to_dict() for e in results])

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

    # ---------- aliases ----------

    @app.post("/api/exercises/<int:ex_id>/aliases")
    def add_alias(ex_id: int) -> Any:
        repo: WorkoutRepository = g.repo
        data = request.get_json(force=True) or {}
        alias_text = (data.get("alias") or "").strip()
        if not alias_text:
            abort(400, "alias required")
        try:
            alias = repo.add_alias(ex_id, alias_text)
        except ValueError as e:
            abort(400, str(e))
        return jsonify(alias.to_dict()), 201

    @app.get("/api/exercises/<int:ex_id>/aliases")
    def list_aliases(ex_id: int) -> Any:
        repo: WorkoutRepository = g.repo
        aliases = repo.list_aliases(ex_id)
        return jsonify([a.to_dict() for a in aliases])

    @app.delete("/api/aliases/<int:alias_id>")
    def delete_alias(alias_id: int) -> Any:
        repo: WorkoutRepository = g.repo
        repo.delete_alias(alias_id)
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

    @app.get("/api/workouts/search")
    def search_workouts() -> Any:
        repo: WorkoutRepository = g.repo
        exercise_name = request.args.get("exercise_name") or None
        date_from = request.args.get("date_from") or None
        date_to = request.args.get("date_to") or None
        min_weight_raw = request.args.get("min_weight") or None
        status = request.args.get("status") or None
        min_weight: float | None = None
        if min_weight_raw is not None:
            try:
                min_weight = float(min_weight_raw)
            except ValueError:
                abort(400, "min_weight must be a number")
        if date_from is not None:
            try:
                date_t.fromisoformat(date_from)
            except ValueError:
                abort(400, f"date_from is not a valid ISO date: {date_from}")
        if date_to is not None:
            try:
                date_t.fromisoformat(date_to)
            except ValueError:
                abort(400, f"date_to is not a valid ISO date: {date_to}")
        try:
            results = repo.search_workouts(
                exercise_name=exercise_name,
                date_from=date_from,
                date_to=date_to,
                min_weight=min_weight,
                status=status,
            )
        except ValueError as e:
            abort(400, str(e))
        return jsonify([w.to_dict() for w in results])

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
                group_id=data.get("group_id") or None,
                protocol=data.get("protocol") or None,
                is_bodyweight=bool(data.get("is_bodyweight", False)),
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
                            "is_bodyweight": s.is_bodyweight,
                            "protocol": s.protocol,
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
        entries = planning.resolve_percentage_sets(repo, parser.parse_notes(text))
        created: list[dict[str, Any]] = []
        for entry in entries:
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
                    is_bodyweight=ps.is_bodyweight,
                    protocol=ps.protocol,
                )
                created.append(repo.add_set(s).to_dict())
        return jsonify(created), 201

    # ---------- templates ----------

    @app.post("/api/workouts/<int:w_id>/save_as_template")
    def save_as_template(w_id: int) -> Any:
        repo: WorkoutRepository = g.repo
        data = request.get_json(force=True) or {}
        name = (data.get("name") or "").strip()
        if not name:
            abort(400, "name required")
        try:
            tmpl = planning.save_as_template(repo, w_id, name=name)
        except KeyError:
            abort(404)
        return jsonify(tmpl), 201

    @app.get("/api/templates")
    def list_templates() -> Any:
        repo: WorkoutRepository = g.repo
        return jsonify(planning.list_templates(repo))

    @app.post("/api/templates/<int:tmpl_id>/create_workout")
    def create_workout_from_template(tmpl_id: int) -> Any:
        repo: WorkoutRepository = g.repo
        data = request.get_json(force=True) or {}
        date = data.get("date") or date_t.today().isoformat()
        title = data.get("title")
        try:
            w = planning.create_workout_from_template(
                repo, tmpl_id, date=date, title=title
            )
        except KeyError:
            abort(404)
        except ValueError as e:
            abort(400, str(e))
        return jsonify(w.to_dict()), 201

    # ---------- copy last weekday ----------

    @app.post("/api/workouts/copy_last_weekday")
    def copy_last_weekday() -> Any:
        repo: WorkoutRepository = g.repo
        data = cast(dict[str, Any], request.get_json(force=True) or {})
        weekday_raw = data.get("weekday")
        target_date: str = data.get("target_date") or date_t.today().isoformat()
        if weekday_raw is None:
            return abort(400, "weekday required")
        try:
            weekday_int = int(cast(int | str, weekday_raw))
        except (ValueError, TypeError):
            return abort(400, "weekday must be an integer 0-6")
        try:
            w = planning.copy_last_weekday_session(
                repo, weekday=weekday_int, target_date=target_date
            )
        except ValueError as e:
            return abort(400, str(e))
        if w is None:
            return abort(404, "no prior session found for that weekday")
        assert w is not None
        return jsonify(w.to_dict()), 201

    # ---------- weekly schedule ----------

    @app.post("/api/schedule/apply")
    def apply_weekly_schedule() -> Any:
        repo: WorkoutRepository = g.repo
        data = cast(dict[str, Any], request.get_json(force=True) or {})
        schedule_raw = data.get("schedule")
        week_start_raw = data.get("week_start")
        if not isinstance(schedule_raw, dict) or not isinstance(week_start_raw, str):
            return abort(400, "schedule and week_start required")
        try:
            schedule: dict[int, Any] = {int(k): v for k, v in schedule_raw.items()}
        except (ValueError, AttributeError):
            return abort(400, "schedule keys must be integer weekdays 0-6")
        try:
            workouts = planning.apply_weekly_schedule(
                repo, schedule, week_start=week_start_raw
            )
        except ValueError as e:
            return abort(400, str(e))
        return jsonify([w.to_dict() for w in workouts]), 201

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

    # ---------- advanced stats (GH298) ----------

    @app.get("/api/stats/advanced")
    def stats_advanced() -> Any:
        repo: WorkoutRepository = g.repo
        all_sets = repo.list_all_executed_sets()
        streak = stats.training_streak(all_sets)
        heatmap = stats.calendar_heatmap_data(all_sets, weeks=26)
        sessions = stats.session_metrics(all_sets)
        return jsonify(
            {
                "streak": streak.__dict__,
                "heatmap": [h.__dict__ for h in heatmap],
                "sessions": [s.__dict__ for s in sessions[:30]],
            }
        )

    @app.get("/api/stats/exercise/<int:ex_id>/trend")
    def stats_exercise_trend(ex_id: int) -> Any:
        repo: WorkoutRepository = g.repo
        period = request.args.get("period", "weekly")
        if period not in ("weekly", "monthly"):
            abort(400, "period must be 'weekly' or 'monthly'")
        sets_for = repo.list_sets_for_exercise(ex_id, executed_only=True)
        trend = stats.volume_trend(sets_for, period=period)
        series = stats.exercise_timeseries(sets_for)
        prs = stats.personal_records(sets_for)
        return jsonify(
            {
                "trend": [tp.__dict__ for tp in trend],
                "timeseries": [tp.__dict__ for tp in series],
                "personal_records": [p.__dict__ for p in prs],
            }
        )

    @app.post("/api/stats/ratio")
    def stats_ratio() -> Any:
        repo: WorkoutRepository = g.repo
        data = cast(dict[str, Any], request.get_json(force=True) or {})
        ex_a_id = data.get("exercise_a_id")
        ex_b_id = data.get("exercise_b_id")
        if not ex_a_id or not ex_b_id:
            return abort(400, "exercise_a_id and exercise_b_id required")
        ex_a_int = int(cast(int | str, ex_a_id))
        ex_b_int = int(cast(int | str, ex_b_id))
        exercises = {e.id: e for e in repo.list_exercises()}
        ex_a = exercises.get(ex_a_int)
        ex_b = exercises.get(ex_b_int)
        if not ex_a or not ex_b:
            return abort(404)
        assert ex_a is not None and ex_b is not None
        sets_a = repo.list_sets_for_exercise(ex_a_int, executed_only=True)
        sets_b = repo.list_sets_for_exercise(ex_b_int, executed_only=True)
        ratio = stats.strength_ratio(sets_a, sets_b)
        return jsonify(
            {
                "ratio": ratio.ratio,
                "e1rm_a": ratio.e1rm_a,
                "e1rm_b": ratio.e1rm_b,
                "name_a": ex_a.name,
                "name_b": ex_b.name,
            }
        )

    # ---------- error handlers ----------

    @app.errorhandler(400)
    def _bad(err: Any) -> Any:
        return jsonify({"error": str(err.description)}), 400

    @app.errorhandler(404)
    def _missing(err: Any) -> Any:
        return jsonify({"error": "not found"}), 404
