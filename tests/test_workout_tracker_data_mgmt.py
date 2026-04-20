"""Tests for GH299: export/import/CSV/trash/bulk-edit."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from workout_tracker.app import create_app
from workout_tracker.data_mgmt import (
    detect_csv_format,
    export_db,
    import_db,
    parse_fitnotes_csv,
    parse_hevy_csv,
    parse_strong_csv,
)
from workout_tracker.db import WorkoutRepository, connect, init_db
from workout_tracker.models import WorkoutSet

# ─── fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture()
def repo() -> WorkoutRepository:
    conn = connect(":memory:")
    init_db(conn)
    return WorkoutRepository(conn)


@pytest.fixture()
def client():
    with tempfile.TemporaryDirectory() as tmp:
        db_path = Path(tmp) / "test.db"
        app = create_app(db_path=str(db_path))
        app.config["TESTING"] = True
        with app.test_client() as c:
            yield c


def _populate_repo(repo: WorkoutRepository) -> dict:
    """Seed two exercises, one workout, two sets. Returns ids."""
    ex1 = repo.get_or_create_exercise("Bench Press")
    ex2 = repo.get_or_create_exercise("Squat")
    w = repo.create_workout(date="2024-05-01", title="Push Day", status="completed")
    s1 = repo.add_set(
        WorkoutSet(
            workout_id=w.id or 0,
            exercise_id=ex1.id or 0,
            position=0,
            actual_reps=5,
            actual_weight=135.0,
            unit="lbs",
            executed=True,
        )
    )
    s2 = repo.add_set(
        WorkoutSet(
            workout_id=w.id or 0,
            exercise_id=ex2.id or 0,
            position=1,
            actual_reps=5,
            actual_weight=225.0,
            unit="lbs",
            executed=True,
        )
    )
    return {
        "ex1_id": ex1.id,
        "ex2_id": ex2.id,
        "w_id": w.id,
        "s1_id": s1.id,
        "s2_id": s2.id,
    }


# ─── Export / Import JSON ────────────────────────────────────────────────────


class TestExportDB:
    def test_export_structure(self, repo: WorkoutRepository) -> None:
        _populate_repo(repo)
        data = export_db(repo)
        assert data["version"] == "1"
        assert len(data["exercises"]) == 2
        assert len(data["workouts"]) == 1
        assert len(data["sets"]) == 2

    def test_export_is_serialisable(self, repo: WorkoutRepository) -> None:
        _populate_repo(repo)
        data = export_db(repo)
        s = json.dumps(data)
        assert len(s) > 0

    def test_export_empty_db(self, repo: WorkoutRepository) -> None:
        data = export_db(repo)
        assert data["exercises"] == []
        assert data["workouts"] == []
        assert data["sets"] == []


class TestImportDBRestore:
    def test_restore_repopulates(self, repo: WorkoutRepository) -> None:
        _populate_repo(repo)
        snapshot = export_db(repo)

        # wipe and restore
        conn2 = connect(":memory:")
        init_db(conn2)
        repo2 = WorkoutRepository(conn2)
        result = import_db(repo2, snapshot, mode="restore")

        assert result["exercises"] == 2
        assert result["workouts"] == 1
        assert result["sets"] == 2
        assert len(repo2.list_exercises()) == 2
        assert len(repo2.list_workouts()) == 1

    def test_restore_clears_existing(self, repo: WorkoutRepository) -> None:
        _populate_repo(repo)
        snapshot = export_db(repo)
        # add extra exercise before restoring
        repo.get_or_create_exercise("OHP")
        result = import_db(repo, snapshot, mode="restore")
        assert result["exercises"] == 2  # OHP wiped, original 2 restored
        assert len(repo.list_exercises()) == 2


class TestImportDBMerge:
    def test_merge_adds_missing(self, repo: WorkoutRepository) -> None:
        snapshot = {
            "version": "1",
            "exercises": [{"name": "Deadlift", "normalized_name": "deadlift"}],
            "workouts": [],
            "sets": [],
        }
        repo.get_or_create_exercise("Bench Press")
        result = import_db(repo, snapshot, mode="merge")
        assert result["exercises"] == 1  # 1 new exercise added
        names = [e.name for e in repo.list_exercises()]
        assert "Deadlift" in names
        assert "Bench Press" in names

    def test_merge_skips_duplicate_exercises(self, repo: WorkoutRepository) -> None:
        repo.get_or_create_exercise("Bench Press")
        snapshot = {
            "version": "1",
            "exercises": [{"name": "Bench Press", "normalized_name": "benchpress"}],
            "workouts": [],
            "sets": [],
        }
        result = import_db(repo, snapshot, mode="merge")
        assert result["exercises"] == 0  # skipped
        assert len(repo.list_exercises()) == 1

    def test_import_rejects_unknown_mode(self, repo: WorkoutRepository) -> None:
        with pytest.raises(ValueError, match="mode"):
            import_db(
                repo,
                {"version": "1", "exercises": [], "workouts": [], "sets": []},
                mode="bad",
            )


# ─── CSV Import parsers ───────────────────────────────────────────────────────

_STRONG_HEADER = (
    "Date,Workout Name,Duration,Exercise Name,"
    "Set Order,Weight,Reps,Distance,Seconds,Notes,Workout Notes,RPE"
)
STRONG_CSV = f"""\
{_STRONG_HEADER}
2024-05-01 08:00:00,Morning Push,2700s,Bench Press (Barbell),1,135,5,,,,
2024-05-01 08:00:00,Morning Push,2700s,Bench Press (Barbell),2,145,3,,,,
2024-05-02 09:00:00,Leg Day,,Squat (Barbell),1,225,5,,,,
"""

HEVY_CSV = """\
title,start_time,end_time,exercise_title,superset_id,exercise_notes,set_index,set_type,weight_lbs,reps,distance_miles,duration_seconds,rpe
Morning Push,2024-05-01 08:00:00,2024-05-01 08:45:00,Bench Press,,, 0,normal,135,5,,,
Morning Push,2024-05-01 08:00:00,2024-05-01 08:45:00,Bench Press,,, 1,normal,145,3,,,
Leg Day,2024-05-02 09:00:00,2024-05-02 10:00:00,Squat,,, 0,normal,225,5,,,
"""

FITNOTES_CSV = """\
Date,Category,Exercise,Weight (lbs),Reps,Distance,Distance Unit,Time
2024-05-01,Chest,Bench Press,135,5,,,
2024-05-01,Chest,Bench Press,145,3,,,
2024-05-02,Legs,Squat,225,5,,,
"""


class TestStrongCSV:
    def test_parses_two_workouts(self) -> None:
        workouts = parse_strong_csv(STRONG_CSV)
        assert len(workouts) == 2

    def test_first_workout_sets(self) -> None:
        workouts = parse_strong_csv(STRONG_CSV)
        w = workouts[0]
        assert w.date == "2024-05-01"
        assert len(w.sets) == 2
        assert w.sets[0].exercise_name == "Bench Press (Barbell)"
        assert w.sets[0].weight == 135.0
        assert w.sets[0].reps == 5

    def test_second_workout(self) -> None:
        workouts = parse_strong_csv(STRONG_CSV)
        w = workouts[1]
        assert w.date == "2024-05-02"
        assert w.sets[0].exercise_name == "Squat (Barbell)"

    def test_empty_csv_returns_empty(self) -> None:
        assert parse_strong_csv("") == []
        assert (
            parse_strong_csv(
                "Date,Workout Name,Duration,Exercise Name,Set Order,Weight,Reps\n"
            )
            == []
        )


class TestHevyCSV:
    def test_parses_two_workouts(self) -> None:
        workouts = parse_hevy_csv(HEVY_CSV)
        assert len(workouts) == 2

    def test_first_workout(self) -> None:
        workouts = parse_hevy_csv(HEVY_CSV)
        w = workouts[0]
        assert w.date == "2024-05-01"
        assert len(w.sets) == 2
        assert w.sets[0].exercise_name == "Bench Press"
        assert w.sets[0].weight == 135.0

    def test_unit_is_lbs(self) -> None:
        workouts = parse_hevy_csv(HEVY_CSV)
        assert all(s.unit == "lbs" for w in workouts for s in w.sets)


class TestFitNotesCSV:
    def test_parses_two_dates(self) -> None:
        workouts = parse_fitnotes_csv(FITNOTES_CSV)
        assert len(workouts) == 2

    def test_groups_by_date(self) -> None:
        workouts = parse_fitnotes_csv(FITNOTES_CSV)
        w = workouts[0]
        assert w.date == "2024-05-01"
        assert len(w.sets) == 2

    def test_second_date(self) -> None:
        workouts = parse_fitnotes_csv(FITNOTES_CSV)
        assert workouts[1].date == "2024-05-02"
        assert workouts[1].sets[0].exercise_name == "Squat"


class TestDetectCSVFormat:
    def test_detects_strong(self) -> None:
        assert detect_csv_format(STRONG_CSV) == "strong"

    def test_detects_hevy(self) -> None:
        assert detect_csv_format(HEVY_CSV) == "hevy"

    def test_detects_fitnotes(self) -> None:
        assert detect_csv_format(FITNOTES_CSV) == "fitnotes"

    def test_unknown_raises(self) -> None:
        with pytest.raises(ValueError, match="format"):
            detect_csv_format("col1,col2\n1,2\n")


# ─── Soft delete + trash (repo layer) ────────────────────────────────────────


class TestSoftDeleteWorkout:
    def test_soft_delete_removes_from_list(self, repo: WorkoutRepository) -> None:
        w = repo.create_workout(date="2024-05-01")
        repo.delete_workout(w.id or 0)
        assert repo.list_workouts() == []

    def test_soft_delete_raises_on_get(self, repo: WorkoutRepository) -> None:
        w = repo.create_workout(date="2024-05-01")
        repo.delete_workout(w.id or 0)
        with pytest.raises(KeyError):
            repo.get_workout(w.id or 0)

    def test_soft_deleted_workout_appears_in_trash(
        self, repo: WorkoutRepository
    ) -> None:
        w = repo.create_workout(date="2024-05-01")
        repo.delete_workout(w.id or 0)
        trash = repo.list_trash()
        assert any(t["id"] == w.id for t in trash["workouts"])

    def test_restore_workout(self, repo: WorkoutRepository) -> None:
        w = repo.create_workout(date="2024-05-01", title="Restore Me")
        repo.delete_workout(w.id or 0)
        repo.restore_workout(w.id or 0)
        restored = repo.get_workout(w.id or 0)
        assert restored.title == "Restore Me"
        assert repo.list_workouts() != []

    def test_purge_workout(self, repo: WorkoutRepository) -> None:
        w = repo.create_workout(date="2024-05-01")
        repo.delete_workout(w.id or 0)
        repo.purge_trash()
        trash = repo.list_trash()
        assert trash["workouts"] == []


class TestSoftDeleteExercise:
    def test_soft_delete_removes_from_list(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Bench Press")
        repo.delete_exercise(ex.id or 0)
        assert repo.list_exercises() == []

    def test_soft_deleted_appears_in_trash(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Bench Press")
        repo.delete_exercise(ex.id or 0)
        trash = repo.list_trash()
        assert any(t["id"] == ex.id for t in trash["exercises"])

    def test_restore_exercise(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Deadlift")
        repo.delete_exercise(ex.id or 0)
        repo.restore_exercise(ex.id or 0)
        names = [e.name for e in repo.list_exercises()]
        assert "Deadlift" in names


class TestSoftDeleteSet:
    def test_soft_delete_removes_from_workout(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Squat")
        w = repo.create_workout(date="2024-05-01", status="in_progress")
        s = repo.add_set(
            WorkoutSet(workout_id=w.id or 0, exercise_id=ex.id or 0, position=0)
        )
        repo.delete_set(s.id or 0)
        refreshed = repo.get_workout(w.id or 0)
        assert refreshed.sets == []

    def test_soft_deleted_set_appears_in_trash(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Squat")
        w = repo.create_workout(date="2024-05-01", status="in_progress")
        s = repo.add_set(
            WorkoutSet(workout_id=w.id or 0, exercise_id=ex.id or 0, position=0)
        )
        repo.delete_set(s.id or 0)
        trash = repo.list_trash()
        assert any(t["id"] == s.id for t in trash["sets"])

    def test_restore_set(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Squat")
        w = repo.create_workout(date="2024-05-01", status="in_progress")
        s = repo.add_set(
            WorkoutSet(workout_id=w.id or 0, exercise_id=ex.id or 0, position=0)
        )
        repo.delete_set(s.id or 0)
        repo.restore_set(s.id or 0)
        refreshed = repo.get_workout(w.id or 0)
        assert len(refreshed.sets) == 1


class TestTrashCascade:
    def test_delete_workout_soft_deletes_its_sets(
        self, repo: WorkoutRepository
    ) -> None:
        ex = repo.get_or_create_exercise("Squat")
        w = repo.create_workout(date="2024-05-01", status="in_progress")
        s = repo.add_set(
            WorkoutSet(workout_id=w.id or 0, exercise_id=ex.id or 0, position=0)
        )
        repo.delete_workout(w.id or 0)
        with pytest.raises(KeyError):
            repo.get_set(s.id or 0)
        trash = repo.list_trash()
        assert any(t["id"] == s.id for t in trash["sets"])


# ─── Bulk edit ────────────────────────────────────────────────────────────────


class TestBulkRename:
    def test_rename_multiple(self, repo: WorkoutRepository) -> None:
        ex1 = repo.get_or_create_exercise("Bnech Press")
        ex2 = repo.get_or_create_exercise("Squatt")
        repo.bulk_rename_exercises({ex1.id or 0: "Bench Press", ex2.id or 0: "Squat"})
        names = {e.name for e in repo.list_exercises()}
        assert "Bench Press" in names
        assert "Squat" in names
        assert "Bnech Press" not in names

    def test_rename_empty_dict_no_op(self, repo: WorkoutRepository) -> None:
        repo.get_or_create_exercise("Bench Press")
        repo.bulk_rename_exercises({})
        assert repo.list_exercises()[0].name == "Bench Press"


class TestUnitConversion:
    def test_convert_lbs_to_kg(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Bench Press")
        w = repo.create_workout(date="2024-05-01", status="in_progress")
        s = repo.add_set(
            WorkoutSet(
                workout_id=w.id or 0,
                exercise_id=ex.id or 0,
                position=0,
                planned_weight=100.0,
                actual_weight=100.0,
                unit="lbs",
            )
        )
        repo.convert_sets_unit(set_ids=[s.id or 0], from_unit="lbs", to_unit="kg")
        updated = repo.get_set(s.id or 0)
        assert updated.unit == "kg"
        assert abs((updated.planned_weight or 0) - 45.359) < 0.1
        assert abs((updated.actual_weight or 0) - 45.359) < 0.1

    def test_convert_kg_to_lbs(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("Squat")
        w = repo.create_workout(date="2024-05-01", status="in_progress")
        s = repo.add_set(
            WorkoutSet(
                workout_id=w.id or 0,
                exercise_id=ex.id or 0,
                position=0,
                actual_weight=100.0,
                unit="kg",
            )
        )
        repo.convert_sets_unit(set_ids=[s.id or 0], from_unit="kg", to_unit="lbs")
        updated = repo.get_set(s.id or 0)
        assert updated.unit == "lbs"
        assert abs((updated.actual_weight or 0) - 220.462) < 0.1

    def test_convert_skips_wrong_unit(self, repo: WorkoutRepository) -> None:
        ex = repo.get_or_create_exercise("OHP")
        w = repo.create_workout(date="2024-05-01", status="in_progress")
        s = repo.add_set(
            WorkoutSet(
                workout_id=w.id or 0,
                exercise_id=ex.id or 0,
                position=0,
                actual_weight=50.0,
                unit="kg",
            )
        )
        repo.convert_sets_unit(set_ids=[s.id or 0], from_unit="lbs", to_unit="kg")
        updated = repo.get_set(s.id or 0)
        assert updated.unit == "kg"
        assert updated.actual_weight == 50.0  # unchanged

    def test_convert_invalid_units_raises(self, repo: WorkoutRepository) -> None:
        with pytest.raises(ValueError):
            repo.convert_sets_unit(set_ids=[], from_unit="lbs", to_unit="lbs")
        with pytest.raises(ValueError):
            repo.convert_sets_unit(set_ids=[], from_unit="lbs", to_unit="stones")


class TestBulkMergeExercises:
    def test_merge_selected_into_target(self, repo: WorkoutRepository) -> None:
        a = repo.get_or_create_exercise("Bench")
        b = repo.get_or_create_exercise("Bench Press")
        c = repo.get_or_create_exercise("BP")
        w = repo.create_workout(date="2024-05-01", status="in_progress")
        repo.add_set(
            WorkoutSet(workout_id=w.id or 0, exercise_id=a.id or 0, position=0)
        )
        repo.add_set(
            WorkoutSet(workout_id=w.id or 0, exercise_id=c.id or 0, position=1)
        )
        repo.bulk_merge_exercises(
            source_ids=[a.id or 0, c.id or 0], target_id=b.id or 0
        )
        names = {e.name for e in repo.list_exercises()}
        assert "Bench Press" in names
        assert "Bench" not in names
        assert "BP" not in names
        # all sets now on target
        sets = repo.list_sets_for_exercise(b.id or 0, executed_only=False)
        assert len(sets) == 2


# ─── HTTP routes ─────────────────────────────────────────────────────────────


class TestExportRoute:
    def test_export_returns_json(self, client) -> None:
        client.post("/api/exercises", json={"name": "Bench Press"})
        r = client.get("/api/export")
        assert r.status_code == 200
        data = r.json
        assert data["version"] == "1"
        assert len(data["exercises"]) == 1

    def test_export_empty_db(self, client) -> None:
        r = client.get("/api/export")
        assert r.status_code == 200
        assert r.json["exercises"] == []


class TestImportRoute:
    def test_import_restore(self, client) -> None:
        snapshot = {
            "version": "1",
            "exercises": [{"name": "Deadlift", "normalized_name": "deadlift"}],
            "workouts": [],
            "sets": [],
        }
        r = client.post("/api/import/json", json={"mode": "restore", "data": snapshot})
        assert r.status_code == 200
        assert r.json["exercises"] == 1
        exs = client.get("/api/exercises").json
        assert any(e["name"] == "Deadlift" for e in exs)

    def test_import_merge(self, client) -> None:
        client.post("/api/exercises", json={"name": "Bench Press"})
        snapshot = {
            "version": "1",
            "exercises": [{"name": "Squat", "normalized_name": "squat"}],
            "workouts": [],
            "sets": [],
        }
        r = client.post("/api/import/json", json={"mode": "merge", "data": snapshot})
        assert r.status_code == 200
        exs = client.get("/api/exercises").json
        names = [e["name"] for e in exs]
        assert "Bench Press" in names
        assert "Squat" in names

    def test_import_bad_mode(self, client) -> None:
        r = client.post("/api/import/json", json={"mode": "bad", "data": {}})
        assert r.status_code == 400

    def test_import_missing_data(self, client) -> None:
        r = client.post("/api/import/json", json={"mode": "restore"})
        assert r.status_code == 400


class TestCSVImportRoute:
    def test_import_strong_csv(self, client) -> None:
        r = client.post(
            "/api/import/csv",
            json={"format": "strong", "csv": STRONG_CSV},
        )
        assert r.status_code == 200
        result = r.json
        assert result["workouts_created"] == 2
        workouts = client.get("/api/workouts").json
        assert len(workouts) == 2

    def test_import_hevy_csv(self, client) -> None:
        r = client.post(
            "/api/import/csv",
            json={"format": "hevy", "csv": HEVY_CSV},
        )
        assert r.status_code == 200
        assert r.json["workouts_created"] == 2

    def test_import_fitnotes_csv(self, client) -> None:
        r = client.post(
            "/api/import/csv",
            json={"format": "fitnotes", "csv": FITNOTES_CSV},
        )
        assert r.status_code == 200
        assert r.json["workouts_created"] == 2

    def test_import_auto_detect(self, client) -> None:
        r = client.post(
            "/api/import/csv",
            json={"csv": STRONG_CSV},
        )
        assert r.status_code == 200
        assert r.json["workouts_created"] == 2

    def test_import_bad_format(self, client) -> None:
        r = client.post("/api/import/csv", json={"format": "bad", "csv": "x"})
        assert r.status_code == 400

    def test_import_missing_csv(self, client) -> None:
        r = client.post("/api/import/csv", json={"format": "strong"})
        assert r.status_code == 400


class TestTrashRoutes:
    def test_soft_delete_workout_not_in_list(self, client) -> None:
        r = client.post("/api/workouts", json={"date": "2024-05-01"})
        wid = r.json["id"]
        client.delete(f"/api/workouts/{wid}")
        workouts = client.get("/api/workouts").json
        assert all(w["id"] != wid for w in workouts)

    def test_deleted_workout_in_trash(self, client) -> None:
        r = client.post("/api/workouts", json={"date": "2024-05-01"})
        wid = r.json["id"]
        client.delete(f"/api/workouts/{wid}")
        trash = client.get("/api/trash").json
        assert any(t["id"] == wid for t in trash["workouts"])

    def test_restore_workout(self, client) -> None:
        r = client.post(
            "/api/workouts", json={"date": "2024-05-01", "title": "Restore"}
        )
        wid = r.json["id"]
        client.delete(f"/api/workouts/{wid}")
        r = client.post("/api/trash/restore", json={"type": "workout", "id": wid})
        assert r.status_code == 200
        workouts = client.get("/api/workouts").json
        assert any(w["id"] == wid for w in workouts)

    def test_purge_trash(self, client) -> None:
        r = client.post("/api/workouts", json={"date": "2024-05-01"})
        wid = r.json["id"]
        client.delete(f"/api/workouts/{wid}")
        r = client.delete("/api/trash")
        assert r.status_code == 200
        trash = client.get("/api/trash").json
        assert trash["workouts"] == []

    def test_soft_delete_exercise(self, client) -> None:
        r = client.post("/api/exercises", json={"name": "OHP"})
        eid = r.json["id"]
        client.delete(f"/api/exercises/{eid}")
        exs = client.get("/api/exercises").json
        assert all(e["id"] != eid for e in exs)
        trash = client.get("/api/trash").json
        assert any(t["id"] == eid for t in trash["exercises"])


class TestBulkEditRoutes:
    def test_bulk_rename(self, client) -> None:
        r1 = client.post("/api/exercises", json={"name": "Bnech Press"})
        r2 = client.post("/api/exercises", json={"name": "Squatt"})
        id1, id2 = r1.json["id"], r2.json["id"]
        r = client.post(
            "/api/exercises/bulk",
            json={
                "action": "rename_batch",
                "renames": {str(id1): "Bench Press", str(id2): "Squat"},
            },
        )
        assert r.status_code == 200
        names = {e["name"] for e in client.get("/api/exercises").json}
        assert "Bench Press" in names
        assert "Squat" in names

    def test_bulk_merge(self, client) -> None:
        r1 = client.post("/api/exercises", json={"name": "Bench"})
        r2 = client.post("/api/exercises", json={"name": "Bench Press"})
        r3 = client.post("/api/exercises", json={"name": "BP"})
        id1, id2, id3 = r1.json["id"], r2.json["id"], r3.json["id"]
        r = client.post(
            "/api/exercises/bulk",
            json={"action": "merge", "source_ids": [id1, id3], "target_id": id2},
        )
        assert r.status_code == 200
        names = {e["name"] for e in client.get("/api/exercises").json}
        assert "Bench Press" in names
        assert "Bench" not in names
        assert "BP" not in names

    def test_bulk_convert_units(self, client) -> None:
        rw = client.post(
            "/api/workouts", json={"date": "2024-05-01", "status": "in_progress"}
        )
        wid = rw.json["id"]
        rs = client.post(
            f"/api/workouts/{wid}/sets",
            json={
                "exercise_name": "Bench Press",
                "actual_weight": 100.0,
                "unit": "lbs",
                "actual_reps": 5,
            },
        )
        sid = rs.json["id"]
        r = client.post(
            "/api/exercises/bulk",
            json={
                "action": "convert_units",
                "set_ids": [sid],
                "from_unit": "lbs",
                "to_unit": "kg",
            },
        )
        assert r.status_code == 200
        # weight should have changed
        w = client.get(f"/api/workouts/{wid}").json
        s = next(s for s in w["sets"] if s["id"] == sid)
        assert s["unit"] == "kg"
        assert abs(s["actual_weight"] - 45.359) < 0.1

    def test_bulk_unknown_action(self, client) -> None:
        r = client.post("/api/exercises/bulk", json={"action": "fly"})
        assert r.status_code == 400
