"""Tests for GH295 — ergonomic logging features.

Covers:
- /api/last_session_sets route (last-session recall)
- WorkoutRepository.resolve_exercise_by_name
- WorkoutRepository.last_session_sets
- Plate calculator logic (pure Python port for unit testing)
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from workout_tracker.app import create_app
from workout_tracker.db import WorkoutRepository, connect, init_db

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def client():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        app = create_app(db_path=str(db_path))
        app.config["TESTING"] = True
        with app.test_client() as c:
            yield c


@pytest.fixture()
def repo():
    """In-memory WorkoutRepository for unit-level tests."""
    conn = connect(":memory:")
    init_db(conn)
    return WorkoutRepository(conn)


# ---------------------------------------------------------------------------
# Repository: resolve_exercise_by_name
# ---------------------------------------------------------------------------


class TestResolveExerciseByName:
    def test_finds_by_exact_name(self, repo) -> None:
        repo.get_or_create_exercise("Bench Press")
        ex = repo.resolve_exercise_by_name("Bench Press")
        assert ex is not None
        assert ex.name == "Bench Press"

    def test_finds_by_normalized_name(self, repo) -> None:
        repo.get_or_create_exercise("Bench Press")
        # normalized("Bench Press") == "benchpress"
        ex = repo.resolve_exercise_by_name("bench press")
        assert ex is not None

    def test_returns_none_for_unknown(self, repo) -> None:
        ex = repo.resolve_exercise_by_name("Unknown Exercise")
        assert ex is None


# ---------------------------------------------------------------------------
# Repository: last_session_sets
# ---------------------------------------------------------------------------


class TestLastSessionSets:
    def _add_workout_with_sets(
        self, repo, date: str, exercise_name: str, sets_data: list
    ) -> int:
        """Helper: create workout + add executed sets."""
        w = repo.create_workout(date=date, status="completed")
        from workout_tracker.models import WorkoutSet

        ex = repo.get_or_create_exercise(exercise_name)
        for reps, weight in sets_data:
            s = WorkoutSet(
                workout_id=w.id or 0,
                exercise_id=ex.id or 0,
                position=-1,
                actual_reps=reps,
                actual_weight=weight,
                executed=True,
            )
            repo.add_set(s)
        return w.id or 0

    def test_returns_empty_for_unknown_exercise(self, repo) -> None:
        ex = repo.get_or_create_exercise("Bench Press")
        sets = repo.last_session_sets(ex.id or 0)
        assert sets == []

    def test_returns_sets_from_last_session_only(self, repo) -> None:
        # Two sessions on different dates
        self._add_workout_with_sets(repo, "2024-01-01", "Squat", [(5, 135), (5, 145)])
        self._add_workout_with_sets(repo, "2024-01-08", "Squat", [(3, 185), (3, 190)])

        ex = repo.resolve_exercise_by_name("Squat")
        assert ex is not None
        sets = repo.last_session_sets(ex.id or 0)
        assert len(sets) == 2
        # Should be the latest session weights
        weights = {s.actual_weight for s in sets}
        assert weights == {185.0, 190.0}

    def test_limit_is_respected(self, repo) -> None:
        self._add_workout_with_sets(
            repo,
            "2024-01-10",
            "Deadlift",
            [(5, 225), (5, 245), (5, 265), (3, 275), (1, 285)],
        )
        ex = repo.resolve_exercise_by_name("Deadlift")
        assert ex is not None
        sets = repo.last_session_sets(ex.id or 0, limit=3)
        assert len(sets) == 3

    def test_only_returns_executed_sets(self, repo) -> None:
        from workout_tracker.models import WorkoutSet

        w = repo.create_workout(date="2024-02-01", status="in_progress")
        ex = repo.get_or_create_exercise("OHP")
        # planned set (not executed)
        planned = WorkoutSet(
            workout_id=w.id or 0,
            exercise_id=ex.id or 0,
            position=-1,
            planned_reps=5,
            planned_weight=95,
            executed=False,
        )
        repo.add_set(planned)
        sets = repo.last_session_sets(ex.id or 0)
        assert sets == []


# ---------------------------------------------------------------------------
# Route: /api/last_session_sets
# ---------------------------------------------------------------------------


class TestLastSessionSetsRoute:
    def _setup_exercise_with_sets(self, client):
        # Create a workout and add executed sets
        r = client.post(
            "/api/workouts", json={"date": "2024-03-01", "status": "completed"}
        )
        wid = r.json["id"]
        for reps, weight in [(5, 135), (5, 145), (3, 155)]:
            client.post(
                f"/api/workouts/{wid}/sets",
                json={
                    "exercise_name": "Bench Press",
                    "actual_reps": reps,
                    "actual_weight": weight,
                    "executed": True,
                },
            )
        return wid

    def test_returns_empty_for_unknown_exercise(self, client) -> None:
        r = client.get("/api/last_session_sets?exercise_name=Unknown+Exercise")
        assert r.status_code == 200
        assert r.json == []

    def test_returns_400_when_no_exercise_name(self, client) -> None:
        r = client.get("/api/last_session_sets")
        assert r.status_code == 400

    def test_returns_sets_for_known_exercise(self, client) -> None:
        self._setup_exercise_with_sets(client)
        r = client.get("/api/last_session_sets?exercise_name=Bench+Press")
        assert r.status_code == 200
        assert len(r.json) == 3
        assert all(s["executed"] for s in r.json)

    def test_limit_param(self, client) -> None:
        self._setup_exercise_with_sets(client)
        r = client.get("/api/last_session_sets?exercise_name=Bench+Press&limit=2")
        assert r.status_code == 200
        assert len(r.json) == 2

    def test_only_last_session(self, client) -> None:
        # Two sessions — only the latest should be returned
        for date, weight in [("2024-03-01", 135.0), ("2024-03-08", 155.0)]:
            r = client.post("/api/workouts", json={"date": date, "status": "completed"})
            wid = r.json["id"]
            client.post(
                f"/api/workouts/{wid}/sets",
                json={
                    "exercise_name": "Squat",
                    "actual_reps": 5,
                    "actual_weight": weight,
                    "executed": True,
                },
            )
        r = client.get("/api/last_session_sets?exercise_name=Squat")
        assert r.status_code == 200
        assert len(r.json) == 1
        assert r.json[0]["actual_weight"] == 155.0

    def test_case_insensitive_exercise_name(self, client) -> None:
        r = client.post(
            "/api/workouts", json={"date": "2024-04-01", "status": "completed"}
        )
        wid = r.json["id"]
        client.post(
            f"/api/workouts/{wid}/sets",
            json={
                "exercise_name": "Overhead Press",
                "actual_reps": 5,
                "actual_weight": 95,
                "executed": True,
            },
        )
        r = client.get("/api/last_session_sets?exercise_name=overhead+press")
        assert r.status_code == 200
        assert len(r.json) == 1


# ---------------------------------------------------------------------------
# Plate calculator logic (pure Python, mirrors JS calcPlates)
# ---------------------------------------------------------------------------


PLATE_SIZES_LBS = [45.0, 35.0, 25.0, 10.0, 5.0, 2.5]
PLATE_SIZES_KG = [20.0, 15.0, 10.0, 5.0, 2.5, 1.25]


def calc_plates(target_weight: float, bar_weight: float, unit: str) -> list | None:
    """Python port of the JS calcPlates function. Per-side plate list or None."""
    sizes = PLATE_SIZES_KG if unit == "kg" else PLATE_SIZES_LBS
    per_side = (target_weight - bar_weight) / 2
    if per_side < 0:
        return None
    remaining = per_side
    result = []
    for size in sizes:
        count = int(remaining / size + 1e-9)
        if count > 0:
            result.append({"size": size, "count": count})
            remaining -= count * size
    if remaining > 0.01:
        return None
    return result


class TestPlateCalculator:
    def test_225_lbs_standard_bar(self) -> None:
        plates = calc_plates(225, 45, "lbs")
        assert plates is not None
        # 225 - 45 = 180 total, 90 per side = 2×45
        assert any(p["size"] == 45.0 and p["count"] == 2 for p in plates)

    def test_135_lbs(self) -> None:
        plates = calc_plates(135, 45, "lbs")
        assert plates is not None
        # 135 - 45 = 90, 45 per side = 1×45
        assert any(p["size"] == 45.0 and p["count"] == 1 for p in plates)

    def test_just_bar(self) -> None:
        plates = calc_plates(45, 45, "lbs")
        assert plates == []

    def test_impossible_weight_returns_none(self) -> None:
        # 47 - 45 bar = 2 lbs total, 1 lb per side — impossible (min plate is 2.5)
        plates = calc_plates(47, 45, "lbs")
        assert plates is None

    def test_below_bar_weight_returns_none(self) -> None:
        plates = calc_plates(30, 45, "lbs")
        assert plates is None

    def test_kg_plates(self) -> None:
        # 60kg bar=20kg → 40kg total → 20kg per side → 1×20
        plates = calc_plates(60, 20, "kg")
        assert plates is not None
        assert any(p["size"] == 20.0 and p["count"] == 1 for p in plates)

    def test_complex_lbs(self) -> None:
        # 315 lbs - 45 = 270 total, 135 per side = 3×45
        plates = calc_plates(315, 45, "lbs")
        assert plates is not None
        assert any(p["size"] == 45.0 and p["count"] == 3 for p in plates)
