"""Tests for workout_tracker.app (Flask routes)."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from workout_tracker.app import create_app


@pytest.fixture()
def client():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        app = create_app(db_path=str(db_path))
        app.config["TESTING"] = True
        with app.test_client() as c:
            yield c


class TestIndex:
    def test_renders(self, client) -> None:
        r = client.get("/")
        assert r.status_code == 200
        assert b"Workout" in r.data


class TestExerciseRoutes:
    def test_list_empty(self, client) -> None:
        r = client.get("/api/exercises")
        assert r.status_code == 200
        assert r.json == []

    def test_create_and_list(self, client) -> None:
        r = client.post("/api/exercises", json={"name": "Bench Press"})
        assert r.status_code == 201
        ex = r.json
        assert ex["name"] == "Bench Press"
        r = client.get("/api/exercises")
        assert len(r.json) == 1

    def test_suggest_prefix(self, client) -> None:
        client.post("/api/exercises", json={"name": "Bench Press"})
        client.post("/api/exercises", json={"name": "Barbell Row"})
        r = client.get("/api/exercises/suggest?q=ben")
        names = [e["name"] for e in r.json]
        assert names and names[0] == "Bench Press"

    def test_create_rejects_empty(self, client) -> None:
        r = client.post("/api/exercises", json={"name": "   "})
        assert r.status_code == 400


class TestWorkoutRoutes:
    def test_full_cycle(self, client) -> None:
        # create workout
        r = client.post(
            "/api/workouts",
            json={"date": "2024-05-01", "status": "in_progress"},
        )
        assert r.status_code == 201
        wid = r.json["id"]
        # add set using exercise_name (auto-creates exercise)
        r = client.post(
            f"/api/workouts/{wid}/sets",
            json={
                "exercise_name": "Bench Press",
                "actual_reps": 5,
                "actual_weight": 135,
                "executed": True,
            },
        )
        assert r.status_code == 201
        sid = r.json["id"]
        # fetch workout and see the set
        r = client.get(f"/api/workouts/{wid}")
        assert len(r.json["sets"]) == 1
        assert r.json["sets"][0]["exercise_name"] == "Bench Press"
        # update set
        r = client.put(f"/api/sets/{sid}", json={"actual_reps": 6})
        assert r.json["actual_reps"] == 6
        # finish
        r = client.put(f"/api/workouts/{wid}", json={"status": "completed"})
        assert r.json["status"] == "completed"

    def test_404_on_missing_workout(self, client) -> None:
        r = client.get("/api/workouts/99999")
        assert r.status_code == 404


class TestParseRoute:
    def test_parse_and_import(self, client) -> None:
        r = client.post(
            "/api/parse",
            json={"text": "Bench Press 3x5 @ 135\nSquat 5x5 @ 225"},
        )
        assert r.status_code == 200
        names = [e["exercise_name"] for e in r.json]
        assert names == ["Bench Press", "Squat"]

        # import into a workout as planned
        r = client.post(
            "/api/workouts",
            json={"date": "2024-05-02", "status": "planned"},
        )
        wid = r.json["id"]
        r = client.post(
            f"/api/workouts/{wid}/import",
            json={"text": "Deadlift 1x5 @ 315", "executed": False},
        )
        assert r.status_code == 201
        # 1 set created
        w = client.get(f"/api/workouts/{wid}").json
        assert len(w["sets"]) == 1
        assert w["sets"][0]["planned_reps"] == 5


class TestValidation:
    def test_bad_workout_status_returns_400(self, client) -> None:
        r = client.post(
            "/api/workouts",
            json={"date": "2024-05-01", "status": "bogus"},
        )
        assert r.status_code == 400

    def test_bad_workout_date_returns_400(self, client) -> None:
        r = client.post(
            "/api/workouts",
            json={"date": "not-a-date"},
        )
        assert r.status_code == 400

    def test_update_workout_to_bad_status_returns_400(self, client) -> None:
        r = client.post("/api/workouts", json={"date": "2024-05-01"})
        wid = r.json["id"]
        r = client.put(f"/api/workouts/{wid}", json={"status": "bogus"})
        assert r.status_code == 400

    def test_bad_set_rpe_returns_400(self, client) -> None:
        r = client.post("/api/workouts", json={"date": "2024-05-01"})
        wid = r.json["id"]
        r = client.post(
            f"/api/workouts/{wid}/sets",
            json={"exercise_name": "Bench", "rpe": 99},
        )
        assert r.status_code == 400

    def test_lazy_import_models_without_flask(self) -> None:
        # Must be importable without constructing the Flask app.
        import importlib

        mod = importlib.import_module("workout_tracker.models")
        assert mod.normalize_name("Bench Press") == "benchpress"


class TestAliasRoutes:
    def test_add_and_list_aliases(self, client) -> None:
        r = client.post("/api/exercises", json={"name": "Bench Press"})
        ex_id = r.json["id"]
        r = client.post(f"/api/exercises/{ex_id}/aliases", json={"alias": "BP"})
        assert r.status_code == 201
        alias = r.json
        assert alias["alias"] == "BP"
        assert alias["exercise_id"] == ex_id

        r = client.get(f"/api/exercises/{ex_id}/aliases")
        assert r.status_code == 200
        assert len(r.json) == 1
        assert r.json[0]["alias"] == "BP"

    def test_delete_alias(self, client) -> None:
        r = client.post("/api/exercises", json={"name": "Bench Press"})
        ex_id = r.json["id"]
        r = client.post(f"/api/exercises/{ex_id}/aliases", json={"alias": "BP"})
        alias_id = r.json["id"]
        r = client.delete(f"/api/aliases/{alias_id}")
        assert r.status_code == 200
        assert r.json["ok"] is True

        r = client.get(f"/api/exercises/{ex_id}/aliases")
        assert r.json == []

    def test_add_alias_missing_body_returns_400(self, client) -> None:
        r = client.post("/api/exercises", json={"name": "Bench Press"})
        ex_id = r.json["id"]
        r = client.post(f"/api/exercises/{ex_id}/aliases", json={})
        assert r.status_code == 400

    def test_suggest_with_alias(self, client) -> None:
        r = client.post("/api/exercises", json={"name": "Bench Press"})
        ex_id = r.json["id"]
        client.post(f"/api/exercises/{ex_id}/aliases", json={"alias": "BP"})
        # "BP" as query should resolve via alias and boost Bench Press
        r = client.get("/api/exercises/suggest?q=BP")
        assert r.status_code == 200
        names = [e["name"] for e in r.json]
        assert "Bench Press" in names


class TestWorkoutSearchRoute:
    def _create_workout_with_set(
        self, client, date, status, exercise_name, weight=None
    ):
        r = client.post("/api/exercises", json={"name": exercise_name})
        ex_id = r.json["id"]
        r = client.post("/api/workouts", json={"date": date, "status": status})
        wid = r.json["id"]
        set_data = {
            "exercise_id": ex_id,
            "actual_weight": weight,
            "actual_reps": 5,
            "executed": True,
        }
        if weight is not None:
            client.post(f"/api/workouts/{wid}/sets", json=set_data)
        return wid

    def test_search_all(self, client) -> None:
        client.post("/api/workouts", json={"date": "2024-01-01", "status": "planned"})
        client.post("/api/workouts", json={"date": "2024-02-01", "status": "completed"})
        r = client.get("/api/workouts/search")
        assert r.status_code == 200
        assert len(r.json) == 2

    def test_search_by_status(self, client) -> None:
        client.post("/api/workouts", json={"date": "2024-01-01", "status": "planned"})
        client.post("/api/workouts", json={"date": "2024-02-01", "status": "completed"})
        r = client.get("/api/workouts/search?status=completed")
        assert r.status_code == 200
        assert len(r.json) == 1
        assert r.json[0]["status"] == "completed"

    def test_search_by_date_range(self, client) -> None:
        client.post("/api/workouts", json={"date": "2024-01-01", "status": "planned"})
        client.post("/api/workouts", json={"date": "2024-06-01", "status": "planned"})
        r = client.get("/api/workouts/search?date_from=2024-03-01")
        assert r.status_code == 200
        assert len(r.json) == 1
        assert r.json[0]["date"] == "2024-06-01"

    def test_search_invalid_status_returns_400(self, client) -> None:
        r = client.get("/api/workouts/search?status=bogus")
        assert r.status_code == 400

    def test_search_invalid_date_returns_400(self, client) -> None:
        r = client.get("/api/workouts/search?date_from=not-a-date")
        assert r.status_code == 400

    def test_search_route_before_workout_id_route(self, client) -> None:
        # Verifies /api/workouts/search is not mistaken for /api/workouts/<int:w_id>
        # with w_id="search" — Flask should route it correctly
        r = client.get("/api/workouts/search")
        assert r.status_code == 200


class TestExerciseTagsRoute:
    def test_update_tags(self, client) -> None:
        r = client.post("/api/exercises", json={"name": "Bench Press"})
        ex_id = r.json["id"]
        r = client.put(f"/api/exercises/{ex_id}/tags", json={"tags": "chest,shoulders"})
        assert r.status_code == 200
        assert r.json["muscle_tags"] == "chest,shoulders"

    def test_clear_tags(self, client) -> None:
        r = client.post("/api/exercises", json={"name": "Squat"})
        ex_id = r.json["id"]
        client.put(f"/api/exercises/{ex_id}/tags", json={"tags": "legs"})
        r = client.put(f"/api/exercises/{ex_id}/tags", json={"tags": ""})
        assert r.status_code == 200
        assert r.json["muscle_tags"] is None

    def test_tags_on_missing_exercise_returns_404(self, client) -> None:
        r = client.put("/api/exercises/99999/tags", json={"tags": "chest"})
        assert r.status_code == 404

    def test_tags_must_be_string_or_null(self, client) -> None:
        r = client.post("/api/exercises", json={"name": "Row"})
        ex_id = r.json["id"]
        r = client.put(f"/api/exercises/{ex_id}/tags", json={"tags": 123})
        assert r.status_code == 400


class TestSoftDeleteRestoreRoutes:
    def test_delete_and_restore_exercise(self, client) -> None:
        r = client.post("/api/exercises", json={"name": "Bench Press"})
        ex_id = r.json["id"]
        # delete (soft)
        r = client.delete(f"/api/exercises/{ex_id}")
        assert r.status_code == 200
        # no longer in list
        exs = client.get("/api/exercises").json
        assert not any(e["id"] == ex_id for e in exs)
        # restore
        r = client.post(f"/api/exercises/{ex_id}/restore")
        assert r.status_code == 200
        # back in list
        exs = client.get("/api/exercises").json
        assert any(e["id"] == ex_id for e in exs)

    def test_delete_and_restore_workout(self, client) -> None:
        r = client.post("/api/workouts", json={"date": "2024-06-01"})
        wid = r.json["id"]
        client.delete(f"/api/workouts/{wid}")
        r = client.get("/api/workouts?limit=200")
        ids = [w["id"] for w in r.json]
        assert wid not in ids
        client.post(f"/api/workouts/{wid}/restore")
        r = client.get("/api/workouts?limit=200")
        ids = [w["id"] for w in r.json]
        assert wid in ids

    def test_delete_and_restore_set(self, client) -> None:
        r = client.post(
            "/api/workouts", json={"date": "2024-06-01", "status": "in_progress"}
        )
        wid = r.json["id"]
        r = client.post(
            f"/api/workouts/{wid}/sets",
            json={
                "exercise_name": "Deadlift",
                "actual_reps": 3,
                "actual_weight": 300,
                "executed": True,
            },
        )
        sid = r.json["id"]
        client.delete(f"/api/sets/{sid}")
        w = client.get(f"/api/workouts/{wid}").json
        assert not any(s["id"] == sid for s in w["sets"])
        client.post(f"/api/sets/{sid}/restore")
        w = client.get(f"/api/workouts/{wid}").json
        assert any(s["id"] == sid for s in w["sets"])


class TestStatsRoutes:
    def test_overview_after_logging(self, client) -> None:
        # create workout + log sets
        r = client.post(
            "/api/workouts",
            json={"date": "2024-05-03", "status": "in_progress"},
        )
        wid = r.json["id"]
        for w in (100, 110, 120):
            client.post(
                f"/api/workouts/{wid}/sets",
                json={
                    "exercise_name": "Bench Press",
                    "actual_reps": 5,
                    "actual_weight": w,
                    "executed": True,
                },
            )
        r = client.get("/api/stats/overview")
        assert r.status_code == 200
        data = r.json
        assert data["overview"]["total_sets"] == 3
        assert data["overview"]["total_volume"] == 5 * (100 + 110 + 120)
        assert any(
            p["metric"] == "max_weight" and p["weight"] == 120
            for p in data["personal_records"]
        )


class TestAdvancedStatsRoutes:
    """GH298 — advanced stats endpoints."""

    def _setup_workout(self, client):
        """Helper: create a workout with 3 sets; return workout id + exercise id."""
        r = client.post(
            "/api/workouts",
            json={"date": "2024-05-03", "status": "in_progress"},
        )
        wid = r.json["id"]
        ex_id = None
        for w in (100, 110, 120):
            r2 = client.post(
                f"/api/workouts/{wid}/sets",
                json={
                    "exercise_name": "Bench Press",
                    "actual_reps": 5,
                    "actual_weight": w,
                    "executed": True,
                },
            )
            ex_id = r2.json["exercise_id"]
        return wid, ex_id

    def test_advanced_returns_expected_keys(self, client) -> None:
        self._setup_workout(client)
        r = client.get("/api/stats/advanced")
        assert r.status_code == 200
        data = r.json
        assert "streak" in data
        assert "heatmap" in data
        assert "sessions" in data
        assert "current_streak" in data["streak"]
        assert "longest_streak" in data["streak"]

    def test_advanced_empty_db(self, client) -> None:
        r = client.get("/api/stats/advanced")
        assert r.status_code == 200
        data = r.json
        assert data["streak"]["current_streak"] == 0
        assert data["heatmap"] == []
        assert data["sessions"] == []

    def test_exercise_trend_weekly(self, client) -> None:
        _, ex_id = self._setup_workout(client)
        r = client.get(f"/api/stats/exercise/{ex_id}/trend?period=weekly")
        assert r.status_code == 200
        data = r.json
        assert "trend" in data
        assert "timeseries" in data
        assert "personal_records" in data

    def test_exercise_trend_monthly(self, client) -> None:
        _, ex_id = self._setup_workout(client)
        r = client.get(f"/api/stats/exercise/{ex_id}/trend?period=monthly")
        assert r.status_code == 200
        assert "trend" in r.json

    def test_exercise_trend_bad_period_returns_400(self, client) -> None:
        _, ex_id = self._setup_workout(client)
        r = client.get(f"/api/stats/exercise/{ex_id}/trend?period=bogus")
        assert r.status_code == 400

    def test_ratio_returns_result(self, client) -> None:
        # Create two exercises with sets
        r1 = client.post("/api/exercises", json={"name": "Bench Press"})
        ex_a = r1.json["id"]
        r2 = client.post("/api/exercises", json={"name": "Overhead Press"})
        ex_b = r2.json["id"]

        wid = client.post("/api/workouts", json={"date": "2024-05-01"}).json["id"]
        client.post(
            f"/api/workouts/{wid}/sets",
            json={
                "exercise_id": ex_a,
                "actual_reps": 5,
                "actual_weight": 200,
                "executed": True,
            },
        )
        client.post(
            f"/api/workouts/{wid}/sets",
            json={
                "exercise_id": ex_b,
                "actual_reps": 5,
                "actual_weight": 100,
                "executed": True,
            },
        )

        r = client.post(
            "/api/stats/ratio",
            json={"exercise_a_id": ex_a, "exercise_b_id": ex_b},
        )
        assert r.status_code == 200
        data = r.json
        assert "ratio" in data
        assert data["ratio"] is not None
        assert data["ratio"] > 1.0  # 200lb bench > 100lb OHP

    def test_ratio_missing_body_returns_400(self, client) -> None:
        r = client.post("/api/stats/ratio", json={})
        assert r.status_code == 400

    def test_ratio_no_sets_returns_none_ratio(self, client) -> None:
        r1 = client.post("/api/exercises", json={"name": "Bench Press"})
        ex_a = r1.json["id"]
        r2 = client.post("/api/exercises", json={"name": "Overhead Press"})
        ex_b = r2.json["id"]
        r = client.post(
            "/api/stats/ratio",
            json={"exercise_a_id": ex_a, "exercise_b_id": ex_b},
        )
        assert r.status_code == 200
        assert r.json["ratio"] is None
