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


class TestBodyweightPlusAdded:
    def test_bw_x_reps_set_line(self) -> None:
        entries = parse_notes("Pull-ups\nBW+25x5")
        s = entries[0].sets[0]
        assert s.is_bodyweight is True
        assert s.weight == 25.0
        assert s.reps == 5

    def test_bw_no_added_x_reps(self) -> None:
        entries = parse_notes("Dips\nBWx10")
        s = entries[0].sets[0]
        assert s.is_bodyweight is True
        assert s.weight is None
        assert s.reps == 10

    def test_reps_at_bw_added(self) -> None:
        entries = parse_notes("Pull-ups\n8 @ BW+45")
        s = entries[0].sets[0]
        assert s.is_bodyweight is True
        assert s.weight == 45.0
        assert s.reps == 8

    def test_full_line_sets_x_reps_at_bw(self) -> None:
        entries = parse_notes("Weighted Pull-ups 3x5 @ BW+25")
        assert len(entries) == 1
        assert entries[0].exercise_name == "Weighted Pull-ups"
        sets = entries[0].sets
        assert len(sets) == 3
        for s in sets:
            assert s.is_bodyweight is True
            assert s.weight == 25.0
            assert s.reps == 5

    def test_full_line_sets_x_reps_at_bw_no_added(self) -> None:
        entries = parse_notes("Dips 3x12 @ BW")
        sets = entries[0].sets
        assert all(s.is_bodyweight for s in sets)
        assert all(s.weight is None for s in sets)

    def test_bw_with_rpe(self) -> None:
        entries = parse_notes("Pull-ups\nBW+25x5 RPE 8")
        s = entries[0].sets[0]
        assert s.is_bodyweight is True
        assert s.rpe == 8.0

    def test_regular_sets_not_bodyweight(self) -> None:
        entries = parse_notes("Bench Press 3x5 @ 135")
        for s in entries[0].sets:
            assert s.is_bodyweight is False

    def test_bw_plus_weight_x_reps_single_line(self) -> None:
        """'Dips BW+45x10' must parse correctly as bodyweight entry (issue #331)."""
        entries = parse_notes("Dips BW+45x10")
        assert len(entries) == 1
        assert entries[0].exercise_name == "Dips"
        sets = entries[0].sets
        assert len(sets) == 1
        assert sets[0].is_bodyweight is True
        assert sets[0].weight == 45.0
        assert sets[0].reps == 10

    def test_bw_x_reps_single_line_no_added(self) -> None:
        """'Pull-ups BWx8' must parse as bodyweight single-line entry (issue #331)."""
        entries = parse_notes("Pull-ups BWx8")
        assert len(entries) == 1
        assert entries[0].exercise_name == "Pull-ups"
        sets = entries[0].sets
        assert len(sets) == 1
        assert sets[0].is_bodyweight is True
        assert sets[0].weight is None
        assert sets[0].reps == 8


class TestProtocolParsing:
    def test_amrap_suffix(self) -> None:
        entries = parse_notes("Bench Press 1x20 @ 135 AMRAP")
        s = entries[0].sets[0]
        assert s.protocol == "amrap"

    def test_emom_suffix(self) -> None:
        entries = parse_notes("Squat 5x3 @ 225 EMOM")
        for s in entries[0].sets:
            assert s.protocol == "emom"

    def test_drop_set_suffix(self) -> None:
        entries = parse_notes("Bench Press 1x10 @ 135 DROP SET")
        assert entries[0].sets[0].protocol == "drop_set"

    def test_failure_suffix(self) -> None:
        entries = parse_notes("Pull-ups\n3x10 FAILURE")
        assert entries[0].sets[0].protocol == "failure"

    def test_partials_suffix(self) -> None:
        entries = parse_notes("Squat\n225x5 PARTIALS")
        assert entries[0].sets[0].protocol == "partials"

    def test_no_protocol_is_none(self) -> None:
        entries = parse_notes("Bench Press 3x5 @ 135")
        for s in entries[0].sets:
            assert s.protocol is None

    def test_comma_separated_sets_keep_protocol_suffix(self) -> None:
        entries = parse_notes("Bench Press\n135x10, 115x12 DROP SET")

        assert len(entries) == 1
        assert entries[0].exercise_name == "Bench Press"
        sets = entries[0].sets
        assert [(s.weight, s.reps, s.protocol) for s in sets] == [
            (135.0, 10, "drop_set"),
            (115.0, 12, "drop_set"),
        ]
