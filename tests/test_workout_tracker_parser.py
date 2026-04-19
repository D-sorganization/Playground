"""Tests for workout_tracker.parser."""

from __future__ import annotations

from workout_tracker.parser import parse_notes


def _names(entries):
    return [e.exercise_name for e in entries]


class TestSingleLineFormat:
    def test_sets_x_reps_at_weight(self) -> None:
        entries = parse_notes("Bench Press 3x5 @ 135")
        assert len(entries) == 1
        e = entries[0]
        assert e.exercise_name == "Bench Press"
        assert len(e.sets) == 3
        for s in e.sets:
            assert s.reps == 5
            assert s.weight == 135.0
            assert s.unit == "lbs"

    def test_with_kg_unit(self) -> None:
        entries = parse_notes("Squat 5x5 @ 100 kg")
        s = entries[0].sets[0]
        assert s.weight == 100.0
        assert s.unit == "kg"

    def test_with_rpe(self) -> None:
        entries = parse_notes("Deadlift 3x3 @ 315 rpe 8.5")
        s = entries[0].sets[0]
        assert s.rpe == 8.5

    def test_bodyweight_no_weight(self) -> None:
        entries = parse_notes("Pull-ups 3x8")
        assert entries[0].exercise_name == "Pull-ups"
        assert all(s.weight is None for s in entries[0].sets)
        assert len(entries[0].sets) == 3


class TestHeaderThenSets:
    def test_weight_x_reps_block(self) -> None:
        text = "Bench Press\n135x5\n155x5\n175x3"
        entries = parse_notes(text)
        assert _names(entries) == ["Bench Press"]
        sets = entries[0].sets
        assert len(sets) == 3
        assert (sets[0].weight, sets[0].reps) == (135.0, 5)
        assert (sets[2].weight, sets[2].reps) == (175.0, 3)

    def test_bullet_dashes_are_stripped(self) -> None:
        text = "Squat\n- 225x5\n- 225x5\n- 245x3"
        sets = parse_notes(text)[0].sets
        assert len(sets) == 3

    def test_empty_line_resets_context(self) -> None:
        text = "Bench Press\n135x5\n\n175x3"  # 175x3 has no exercise context
        entries = parse_notes(text)
        assert len(entries) == 1
        assert len(entries[0].sets) == 1


class TestMultipleExercises:
    def test_multi_entry(self) -> None:
        text = """Bench Press 3x5 @ 135
Squat 5x5 @ 225
Deadlift 1x5 @ 315"""
        entries = parse_notes(text)
        assert _names(entries) == ["Bench Press", "Squat", "Deadlift"]

    def test_mixed_formats(self) -> None:
        text = """Bench Press 3x5 @ 135
Deadlift
315x5
335x3"""
        entries = parse_notes(text)
        assert _names(entries) == ["Bench Press", "Deadlift"]
        assert len(entries[1].sets) == 2
        assert entries[1].sets[1].weight == 335.0


class TestInlineMultipleSets:
    def test_comma_separated_sets(self) -> None:
        # "Squat: 225x5, 245x3, 255x1"
        text = "Squat\n225x5, 245x3, 255x1"
        entries = parse_notes(text)
        assert len(entries[0].sets) == 3
        weights = [s.weight for s in entries[0].sets]
        assert weights == [225.0, 245.0, 255.0]


class TestEmptyInput:
    def test_empty_returns_empty(self) -> None:
        assert parse_notes("") == []
        assert parse_notes("   \n\n  ") == []
