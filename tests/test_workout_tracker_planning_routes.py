"""Tests for planning-related Flask routes."""

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


def _make_workout_with_set(client, date, exercise_name, weight, reps=5):
    r = client.post("/api/workouts", json={"date": date, "status": "completed"})
    wid = r.json["id"]
    r2 = client.post(
        f"/api/workouts/{wid}/sets",
        json={
            "exercise_name": exercise_name,
            "actual_reps": reps,
            "actual_weight": weight,
            "executed": True,
        },
    )
    assert r2.status_code == 201
    return wid


class TestTemplateRoutes:
    def test_save_and_list_template(self, client) -> None:
        wid = _make_workout_with_set(client, "2024-05-01", "Bench Press", 135)
        r = client.post(
            f"/api/workouts/{wid}/save_as_template",
            json={"name": "My Push"},
        )
        assert r.status_code == 201
        tmpl = r.json
        assert tmpl["name"] == "My Push"
        assert tmpl["source_workout_id"] == wid

        r2 = client.get("/api/templates")
        assert r2.status_code == 200
        names = [t["name"] for t in r2.json]
        assert "My Push" in names

    def test_create_workout_from_template(self, client) -> None:
        wid = _make_workout_with_set(client, "2024-05-01", "Squat", 225)
        r = client.post(
            f"/api/workouts/{wid}/save_as_template",
            json={"name": "Leg Day"},
        )
        tmpl_id = r.json["id"]
        r2 = client.post(
            f"/api/templates/{tmpl_id}/create_workout",
            json={"date": "2024-06-01"},
        )
        assert r2.status_code == 201
        w = r2.json
        assert w["date"] == "2024-06-01"
        assert w["status"] == "planned"
        assert len(w["sets"]) == 1
        assert w["sets"][0]["planned_weight"] == 225.0

    def test_create_from_unknown_template_returns_404(self, client) -> None:
        r = client.post(
            "/api/templates/9999/create_workout", json={"date": "2024-06-01"}
        )
        assert r.status_code == 404

    def test_save_template_missing_name_returns_400(self, client) -> None:
        r = client.post("/api/workouts", json={"date": "2024-05-01"})
        wid = r.json["id"]
        r2 = client.post(f"/api/workouts/{wid}/save_as_template", json={})
        assert r2.status_code == 400


class TestCopyLastWeekdayRoute:
    def test_copy_last_monday_to_next_monday(self, client) -> None:
        # Monday 2024-05-06
        _make_workout_with_set(client, "2024-05-06", "Deadlift", 315)
        r = client.post(
            "/api/workouts/copy_last_weekday",
            json={"weekday": 0, "target_date": "2024-05-13"},
        )
        assert r.status_code == 201
        w = r.json
        assert w["date"] == "2024-05-13"
        assert w["status"] == "planned"
        assert len(w["sets"]) == 1

    def test_no_prior_session_returns_404(self, client) -> None:
        r = client.post(
            "/api/workouts/copy_last_weekday",
            json={"weekday": 0, "target_date": "2024-05-13"},
        )
        assert r.status_code == 404

    def test_invalid_weekday_returns_400(self, client) -> None:
        r = client.post(
            "/api/workouts/copy_last_weekday",
            json={"weekday": 7, "target_date": "2024-05-13"},
        )
        assert r.status_code == 400


class TestWeeklyScheduleRoute:
    def test_apply_schedule_creates_workouts(self, client) -> None:
        r = client.post(
            "/api/schedule/apply",
            json={
                "schedule": {"0": "Push", "2": "Pull", "4": "Legs"},
                "week_start": "2024-05-06",
            },
        )
        assert r.status_code == 201
        workouts = r.json
        assert len(workouts) == 3
        dates = {w["date"] for w in workouts}
        assert "2024-05-06" in dates
        assert "2024-05-08" in dates
        assert "2024-05-10" in dates

    def test_invalid_week_start_returns_400(self, client) -> None:
        r = client.post(
            "/api/schedule/apply",
            json={
                "schedule": {"0": "Push"},
                "week_start": "2024-05-07",
            },
        )
        assert r.status_code == 400

    def test_missing_schedule_returns_400(self, client) -> None:
        r = client.post("/api/schedule/apply", json={"week_start": "2024-05-06"})
        assert r.status_code == 400


class TestImportWithPercentage:
    def test_import_resolves_percentage_sets(self, client) -> None:
        # First, log an executed set to establish e1RM
        _make_workout_with_set(client, "2024-05-01", "Bench Press", 200, reps=1)

        # Now create a planned workout
        r = client.post(
            "/api/workouts", json={"date": "2024-05-08", "status": "planned"}
        )
        wid_plan = r.json["id"]

        # Import with percentage notation: 5 @ 0.8 should resolve to 80% of 200 = 160
        r2 = client.post(
            f"/api/workouts/{wid_plan}/import",
            json={"text": "Bench Press\n5 @ 0.8", "executed": False},
        )
        assert r2.status_code == 201
        sets = r2.json
        assert len(sets) == 1
        # 80% of e1RM (200) = 160
        assert sets[0]["planned_weight"] == pytest.approx(160.0, abs=1.0)

    def test_import_with_absolute_weight_unchanged(self, client) -> None:
        r = client.post(
            "/api/workouts", json={"date": "2024-05-08", "status": "planned"}
        )
        wid = r.json["id"]
        r2 = client.post(
            f"/api/workouts/{wid}/import",
            json={"text": "Bench Press 3x5 @ 135", "executed": False},
        )
        assert r2.status_code == 201
        for s in r2.json:
            assert s["planned_weight"] == pytest.approx(135.0)
