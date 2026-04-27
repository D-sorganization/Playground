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


def _create_workout(client, *, date: str = "2024-05-01", **overrides):
    payload = {"date": date, **overrides}
    response = client.post("/api/workouts", json=payload)
    assert response.status_code == 201
    return response.json


def _create_exercise(client, name: str):
    response = client.post("/api/exercises", json={"name": name})
    assert response.status_code == 201
    return response.json


class TestFactory:
    def test_releases_startup_schema_connection(self, tmp_path) -> None:
        db_path = tmp_path / "bootstrap.db"
        create_app(db_path=str(db_path))

        db_path.unlink()

        assert not db_path.exists()


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

    def test_rename_merge_and_delete(self, client) -> None:
        target = _create_exercise(client, "Bench Press")
        source = _create_exercise(client, "Bench Presh")

        r = client.put(
            f"/api/exercises/{source['id']}",
            json={"name": "Incline Bench Press"},
        )
        assert r.status_code == 200
        assert r.json["name"] == "Incline Bench Press"

        r = client.post(
            f"/api/exercises/{source['id']}/merge_into/{target['id']}",
        )
        assert r.status_code == 200
        assert r.json == {"ok": True}

        r = client.delete(f"/api/exercises/{target['id']}")
        assert r.status_code == 200
        assert r.json == {"ok": True}
        assert client.get("/api/exercises").json == []

    def test_rename_rejects_empty_name(self, client) -> None:
        exercise = _create_exercise(client, "Squat")

        r = client.put(f"/api/exercises/{exercise['id']}", json={"name": " "})

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

    def test_list_limit_update_missing_and_delete(self, client) -> None:
        first = _create_workout(client, date="2024-05-01")
        _create_workout(client, date="2024-05-02")

        r = client.get("/api/workouts?limit=1")
        assert r.status_code == 200
        assert len(r.json) == 1
        assert r.json[0]["date"] == "2024-05-02"

        r = client.put("/api/workouts/99999", json={"status": "completed"})
        assert r.status_code == 404

        r = client.delete(f"/api/workouts/{first['id']}")
        assert r.status_code == 200
        assert r.json == {"ok": True}
        assert client.get(f"/api/workouts/{first['id']}").status_code == 404


class TestSetRoutes:
    def test_add_set_requires_exercise_reference(self, client) -> None:
        workout = _create_workout(client)

        r = client.post(f"/api/workouts/{workout['id']}/sets", json={})

        assert r.status_code == 400

    def test_update_missing_unknown_field_and_delete(self, client) -> None:
        workout = _create_workout(client)
        exercise = _create_exercise(client, "Deadlift")
        r = client.post(
            f"/api/workouts/{workout['id']}/sets",
            json={"exercise_id": exercise["id"], "planned_reps": 5},
        )
        assert r.status_code == 201
        set_id = r.json["id"]

        r = client.put("/api/sets/99999", json={"planned_reps": 3})
        assert r.status_code == 404

        r = client.put(f"/api/sets/{set_id}", json={"not_a_field": True})
        assert r.status_code == 400

        r = client.delete(f"/api/sets/{set_id}")
        assert r.status_code == 200
        assert r.json == {"ok": True}
        assert client.get(f"/api/workouts/{workout['id']}").json["sets"] == []


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

    def test_import_executed_sets_populates_actual_fields(self, client) -> None:
        workout = _create_workout(client, status="in_progress")

        r = client.post(
            f"/api/workouts/{workout['id']}/import",
            json={"text": "Bench Press 2x8 @ 95", "executed": True},
        )

        assert r.status_code == 201
        created = r.json
        assert len(created) == 2
        assert created[0]["planned_reps"] is None
        assert created[0]["actual_reps"] == 8
        assert created[0]["actual_weight"] == 95


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

    def test_exercise_timeseries_and_records(self, client) -> None:
        workout = _create_workout(client, date="2024-05-04", status="in_progress")
        first = client.post(
            f"/api/workouts/{workout['id']}/sets",
            json={
                "exercise_name": "Squat",
                "actual_reps": 3,
                "actual_weight": 225,
                "executed": True,
            },
        ).json
        client.post(
            f"/api/workouts/{workout['id']}/sets",
            json={
                "exercise_id": first["exercise_id"],
                "actual_reps": 2,
                "actual_weight": 245,
                "executed": True,
            },
        )

        r = client.get(f"/api/stats/exercise/{first['exercise_id']}")

        assert r.status_code == 200
        assert r.json["timeseries"][0]["sets"] == 2
        assert r.json["timeseries"][0]["volume"] == 3 * 225 + 2 * 245
        assert any(
            record["metric"] == "max_weight" and record["weight"] == 245
            for record in r.json["personal_records"]
        )


class TestExerciseLastSession:
    """/api/exercises/last_session powers the in-gym recall strip (#295)."""

    def test_no_history_returns_empty(self, client) -> None:
        r = client.get("/api/exercises/last_session?q=Bench%20Press")
        assert r.status_code == 200
        assert r.json == {"date": None, "exercise_name": "Bench Press", "sets": []}

    def test_returns_most_recent_session_sorted(self, client) -> None:
        old = _create_workout(client, date="2024-05-01", status="in_progress")
        for weight in (135, 145):
            client.post(
                f"/api/workouts/{old['id']}/sets",
                json={
                    "exercise_name": "Bench Press",
                    "actual_reps": 5,
                    "actual_weight": weight,
                    "executed": True,
                },
            )
        new = _create_workout(client, date="2024-05-10", status="in_progress")
        for weight in (155, 165):
            client.post(
                f"/api/workouts/{new['id']}/sets",
                json={
                    "exercise_name": "Bench Press",
                    "actual_reps": 5,
                    "actual_weight": weight,
                    "executed": True,
                },
            )

        r = client.get("/api/exercises/last_session?q=Bench%20Press")
        assert r.status_code == 200
        assert r.json["date"] == "2024-05-10"
        assert r.json["exercise_name"] == "Bench Press"
        weights = [s["weight"] for s in r.json["sets"]]
        assert weights == [155, 165]

    def test_exclude_active_workout(self, client) -> None:
        old = _create_workout(client, date="2024-05-01", status="in_progress")
        client.post(
            f"/api/workouts/{old['id']}/sets",
            json={
                "exercise_name": "Squat",
                "actual_reps": 5,
                "actual_weight": 225,
                "executed": True,
            },
        )
        active = _create_workout(client, date="2024-05-20", status="in_progress")
        client.post(
            f"/api/workouts/{active['id']}/sets",
            json={
                "exercise_name": "Squat",
                "actual_reps": 5,
                "actual_weight": 245,
                "executed": True,
            },
        )

        r = client.get(f"/api/exercises/last_session?q=Squat&exclude={active['id']}")
        assert r.status_code == 200
        assert r.json["date"] == "2024-05-01"
        assert [s["weight"] for s in r.json["sets"]] == [225]

    def test_last_session_uses_all_candidate_workouts(self, client) -> None:
        older = _create_workout(client, date="2023-01-01", status="completed")
        client.post(
            f"/api/workouts/{older['id']}/sets",
            json={
                "exercise_name": "Bench Press",
                "actual_reps": 5,
                "actual_weight": 135,
                "executed": True,
            },
        )
        newer = _create_workout(client, date="2023-01-02", status="completed")
        client.post(
            f"/api/workouts/{newer['id']}/sets",
            json={
                "exercise_name": "Bench Press",
                "actual_reps": 5,
                "actual_weight": 155,
                "executed": True,
            },
        )
        for day in range(1, 501):
            _create_workout(client, date=f"2024-01-{(day % 28) + 1:02d}")

        r = client.get("/api/exercises/last_session?q=Bench%20Press")

        assert r.status_code == 200
        assert r.json["date"] == "2023-01-02"
        assert [s["weight"] for s in r.json["sets"]] == [155]

    def test_unknown_exercise_returns_empty(self, client) -> None:
        r = client.get("/api/exercises/last_session?q=Nonexistent")
        assert r.status_code == 200
        assert r.json["sets"] == []
