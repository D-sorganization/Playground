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
