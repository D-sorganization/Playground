"""Comprehensive utility tests for Playground with Design-by-Contract coverage.

This module provides 45+ tests covering:
- Data structure operations (creation, access, modification, deletion)
- String/text utilities (parsing, formatting, transformation)
- Numeric utilities (rounding, scaling, validation)
- Collection utilities (filtering, mapping, reducing)
- Input validation and error handling
- Type conversion functions
- Edge cases (empty inputs, boundary values, null/None handling)
- Contracts: Preconditions, Postconditions, Invariants, Property preservation

Test organization follows Design-by-Contract:
- Precondition tests: validate input acceptance/rejection
- Postcondition tests: verify output correctness and type
- Invariant tests: idempotency, property preservation
- Edge case tests: empty, single-element, large scale, null values
"""

from __future__ import annotations

import pytest

from workout_tracker.autocomplete import (
    damerau_levenshtein,
    score,
    suggest,
    trigram_similarity,
)
from workout_tracker.models import Exercise, Workout, WorkoutSet, normalize_name
from workout_tracker.parser import (
    ParsedEntry,
    ParsedSet,
    parse_notes,
)
from workout_tracker.stats import (
    best_1rm_estimate,
    brzycki_1rm,
    epley_1rm,
    exercise_timeseries,
    frequency,
    overview,
    per_exercise_summary,
    personal_records,
    set_volume,
    total_volume,
)

# ============================================================================
# SECTION 1: normalize_name() - String transformation utilities
# ============================================================================


class TestNormalizeName:
    """Postcondition: output is lowercase alphanumeric only.
    Invariant: normalize(normalize(x)) == normalize(x) (idempotency).
    """

    def test_postcondition_lowercase(self) -> None:
        """Postcondition: result is fully lowercase."""
        result = normalize_name("Bench Press")
        assert result == result.lower()
        assert result.islower() or result.isdigit()

    def test_postcondition_alphanumeric_only(self) -> None:
        """Postcondition: result contains only alphanumerics."""
        result = normalize_name("Pull-Ups!")
        assert all(c.isalnum() for c in result)

    def test_invariant_idempotency(self) -> None:
        """Invariant: normalize is idempotent."""
        original = "Bench-Press!"
        once = normalize_name(original)
        twice = normalize_name(once)
        assert once == twice

    def test_edge_case_empty_string(self) -> None:
        """Edge case: empty input."""
        assert normalize_name("") == ""

    def test_edge_case_whitespace_only(self) -> None:
        """Edge case: whitespace gets stripped."""
        assert normalize_name("   ") == ""

    def test_edge_case_numbers_preserved(self) -> None:
        """Postcondition: numbers are preserved."""
        assert normalize_name("Leg Press 45") == "legpress45"

    def test_postcondition_consistency_across_variants(self) -> None:
        """Postcondition: different casings map to same normalized form."""
        variants = ["BENCH PRESS", "bench press", "Bench Press"]
        normalized = [normalize_name(v) for v in variants]
        assert len(set(normalized)) == 1


# ============================================================================
# SECTION 2: ParsedSet & ParsedEntry - Data structure operations
# ============================================================================


class TestParsedSetCreation:
    """Precondition: reps >= 1. Postcondition: all fields initialized correctly."""

    def test_postcondition_default_unit(self) -> None:
        """Postcondition: default unit is 'lbs'."""
        ps = ParsedSet(reps=5)
        assert ps.unit == "lbs"

    def test_postcondition_weight_optional(self) -> None:
        """Postcondition: weight can be None (bodyweight)."""
        ps = ParsedSet(reps=8, weight=None)
        assert ps.weight is None

    def test_postcondition_rpe_optional(self) -> None:
        """Postcondition: rpe can be None."""
        ps = ParsedSet(reps=5, rpe=None)
        assert ps.rpe is None

    def test_postcondition_all_fields_accessible(self) -> None:
        """Postcondition: all fields are accessible."""
        ps = ParsedSet(reps=5, weight=135.0, rpe=8.5, unit="kg")
        assert ps.reps == 5
        assert ps.weight == 135.0
        assert ps.rpe == 8.5
        assert ps.unit == "kg"


class TestParsedEntryCreation:
    """Postcondition: exercise_name set, sets list initialized."""

    def test_postcondition_empty_sets_default(self) -> None:
        """Postcondition: sets defaults to empty list."""
        pe = ParsedEntry(exercise_name="Bench Press")
        assert pe.sets == []
        assert isinstance(pe.sets, list)

    def test_postcondition_sets_preserved(self) -> None:
        """Postcondition: sets list is preserved."""
        sets = [ParsedSet(reps=5, weight=135.0)]
        pe = ParsedEntry(exercise_name="Bench Press", sets=sets)
        assert len(pe.sets) == 1
        assert pe.sets[0].weight == 135.0

    def test_postcondition_immutability_safe(self) -> None:
        """Invariant: entry preserves set data on access."""
        sets = [ParsedSet(reps=5, weight=100.0)]
        pe = ParsedEntry(exercise_name="Test", sets=sets)
        retrieved_sets = pe.sets
        assert len(retrieved_sets) == 1


# ============================================================================
# SECTION 3: parse_notes() - String parsing utilities
# ============================================================================


class TestParseNotes:
    """Postcondition: returns list of ParsedEntry. Invariant: no duplicate parsing."""

    def test_postcondition_returns_list(self) -> None:
        """Postcondition: result is always a list."""
        result = parse_notes("Bench Press 3x5 @ 135")
        assert isinstance(result, list)
        assert len(result) > 0

    def test_postcondition_returns_parsed_entries(self) -> None:
        """Postcondition: each element is ParsedEntry."""
        result = parse_notes("Bench Press 3x5 @ 135")
        assert all(isinstance(e, ParsedEntry) for e in result)

    def test_postcondition_exercise_name_populated(self) -> None:
        """Postcondition: exercise_name is set."""
        result = parse_notes("Bench Press 3x5 @ 135")
        assert result[0].exercise_name == "Bench Press"

    def test_precondition_single_line_format(self) -> None:
        """Precondition acceptance: standard format accepted."""
        result = parse_notes("Bench Press 3x5 @ 135 lbs")
        assert len(result) == 1
        assert len(result[0].sets) == 3

    def test_edge_case_empty_input(self) -> None:
        """Edge case: empty input returns empty list."""
        assert parse_notes("") == []

    def test_edge_case_whitespace_only(self) -> None:
        """Edge case: whitespace returns empty list."""
        assert parse_notes("   \n\n  ") == []

    def test_postcondition_unit_normalization(self) -> None:
        """Postcondition: units are normalized to lbs or kg."""
        result_lbs = parse_notes("Bench 3x5 @ 135 lbs")[0].sets[0].unit
        result_kg = parse_notes("Bench 3x5 @ 100 kg")[0].sets[0].unit
        assert result_lbs == "lbs"
        assert result_kg == "kg"

    def test_postcondition_rpe_extraction(self) -> None:
        """Postcondition: RPE is extracted when present."""
        result = parse_notes("Bench 3x5 @ 135 rpe 8.5")[0].sets[0]
        assert result.rpe == 8.5

    def test_invariant_no_duplicate_entries(self) -> None:
        """Invariant: same input doesn't create duplicates."""
        text = "Bench Press 3x5 @ 135"
        r1 = parse_notes(text)
        r2 = parse_notes(text)
        assert len(r1) == len(r2)
        assert r1[0].exercise_name == r2[0].exercise_name

    def test_postcondition_header_then_sets_format(self) -> None:
        """Postcondition: multi-line header format parsed correctly."""
        text = "Bench Press\n135x5\n155x5"
        result = parse_notes(text)
        assert result[0].exercise_name == "Bench Press"
        assert len(result[0].sets) == 2
        assert result[0].sets[0].weight == 135.0

    def test_edge_case_multiple_exercises(self) -> None:
        """Edge case: multiple exercises in one input."""
        text = "Bench Press 3x5 @ 135\nSquat 5x5 @ 225"
        result = parse_notes(text)
        assert len(result) == 2
        assert result[0].exercise_name == "Bench Press"
        assert result[1].exercise_name == "Squat"

    def test_edge_case_comma_separated_sets(self) -> None:
        """Edge case: comma-separated sets in one line."""
        text = "Bench Press\n135x5, 155x5, 175x3"
        result = parse_notes(text)
        assert len(result[0].sets) == 3

    def test_postcondition_bodyweight_no_weight(self) -> None:
        """Postcondition: bodyweight exercises have weight=None."""
        result = parse_notes("Pull-ups 3x8")[0].sets[0]
        assert result.weight is None
        assert result.reps == 8

    def test_postcondition_weight_x_reps_format(self) -> None:
        """Postcondition: weight-first format (e.g., 135x5) parsed correctly."""
        text = "Bench Press\n135x5"
        result = parse_notes(text)[0].sets[0]
        assert result.weight == 135.0
        assert result.reps == 5


# ============================================================================
# SECTION 4: Numeric utilities (1RM estimation, volume)
# ============================================================================


class TestEpley1RM:
    """Postcondition: output > weight. Precondition: reps > 0, weight >= 0."""

    def test_precondition_rejects_zero_reps(self) -> None:
        """Precondition: reps must be > 0."""
        with pytest.raises(ValueError):
            epley_1rm(135, 0)

    def test_precondition_rejects_negative_reps(self) -> None:
        """Precondition: reps must be positive."""
        with pytest.raises(ValueError):
            epley_1rm(135, -1)

    def test_precondition_rejects_negative_weight(self) -> None:
        """Precondition: weight must be >= 0."""
        with pytest.raises(ValueError):
            epley_1rm(-10, 5)

    def test_postcondition_single_rep_equals_weight(self) -> None:
        """Postcondition: 1RM at 1 rep = weight."""
        assert epley_1rm(135, 1) == 135.0

    def test_postcondition_more_reps_higher_1rm(self) -> None:
        """Postcondition: more reps = higher estimated 1RM."""
        one_rep = epley_1rm(135, 1)
        five_reps = epley_1rm(135, 5)
        assert five_reps > one_rep

    def test_invariant_formula_consistency(self) -> None:
        """Invariant: formula is weight * (1 + reps/30)."""
        weight, reps = 135, 5
        result = epley_1rm(weight, reps)
        expected = weight * (1 + reps / 30)
        assert result == pytest.approx(expected)


class TestBrzycki1RM:
    """Postcondition: output > weight. Precondition: reps in [1, 36]."""

    def test_precondition_rejects_reps_37(self) -> None:
        """Precondition: Brzycki diverges at reps >= 37."""
        with pytest.raises(ValueError):
            brzycki_1rm(135, 37)

    def test_precondition_rejects_zero_reps(self) -> None:
        """Precondition: reps must be > 0."""
        with pytest.raises(ValueError):
            brzycki_1rm(135, 0)

    def test_precondition_rejects_negative_weight(self) -> None:
        """Precondition: weight >= 0."""
        with pytest.raises(ValueError):
            brzycki_1rm(-10, 5)

    def test_postcondition_single_rep_equals_weight(self) -> None:
        """Postcondition: 1RM at 1 rep ≈ weight."""
        result = brzycki_1rm(135, 1)
        assert result == pytest.approx(135.0, rel=0.01)

    def test_postcondition_valid_reps_36(self) -> None:
        """Postcondition: works at boundary reps=36."""
        result = brzycki_1rm(135, 36)
        assert result > 135.0


class TestBest1RMEstimate:
    """Postcondition: uses both formulas when valid, falls back to Epley."""

    def test_postcondition_combines_both_formulas(self) -> None:
        """Postcondition: averages Epley + Brzycki for valid reps."""
        epley = epley_1rm(135, 5)
        brzycki = brzycki_1rm(135, 5)
        result = best_1rm_estimate(135, 5)
        assert result == pytest.approx((epley + brzycki) / 2)

    def test_postcondition_fallback_to_epley_high_reps(self) -> None:
        """Postcondition: falls back to Epley when Brzycki fails."""
        result = best_1rm_estimate(135, 37)
        expected = epley_1rm(135, 37)
        assert result == pytest.approx(expected)

    def test_postcondition_reasonable_estimate(self) -> None:
        """Postcondition: estimate is >= the weight lifted."""
        assert best_1rm_estimate(135, 5) >= 135


class TestSetVolume:
    """Postcondition: volume = weight * reps for executed sets, 0 otherwise."""

    def test_postcondition_executed_set(self) -> None:
        """Postcondition: volume = weight * reps for executed."""
        s = WorkoutSet(
            workout_id=1,
            exercise_id=1,
            actual_reps=5,
            actual_weight=135.0,
            executed=True,
        )
        assert set_volume(s) == 5 * 135.0

    def test_postcondition_not_executed_is_zero(self) -> None:
        """Postcondition: non-executed sets have 0 volume."""
        s = WorkoutSet(
            workout_id=1,
            exercise_id=1,
            actual_reps=5,
            actual_weight=135.0,
            executed=False,
        )
        assert set_volume(s) == 0.0

    def test_edge_case_zero_reps(self) -> None:
        """Edge case: 0 reps -> 0 volume."""
        s = WorkoutSet(
            workout_id=1,
            exercise_id=1,
            actual_reps=0,
            actual_weight=135.0,
            executed=True,
        )
        assert set_volume(s) == 0.0

    def test_edge_case_none_weight(self) -> None:
        """Edge case: None weight treated as 0."""
        s = WorkoutSet(
            workout_id=1,
            exercise_id=1,
            actual_reps=5,
            actual_weight=None,
            executed=True,
        )
        assert set_volume(s) == 0.0


class TestTotalVolume:
    """Postcondition: sum of all set volumes."""

    def test_postcondition_sums_volumes(self) -> None:
        """Postcondition: total = sum of individual volumes."""
        sets = [
            WorkoutSet(
                workout_id=1,
                exercise_id=1,
                actual_reps=5,
                actual_weight=100,
                executed=True,
            ),
            WorkoutSet(
                workout_id=1,
                exercise_id=1,
                actual_reps=3,
                actual_weight=200,
                executed=True,
            ),
        ]
        expected = 5 * 100 + 3 * 200
        assert total_volume(sets) == expected

    def test_edge_case_empty_list(self) -> None:
        """Edge case: empty list -> 0 volume."""
        assert total_volume([]) == 0.0

    def test_edge_case_single_set(self) -> None:
        """Edge case: single set."""
        sets = [
            WorkoutSet(
                workout_id=1,
                exercise_id=1,
                actual_reps=5,
                actual_weight=100,
                executed=True,
            )
        ]
        assert total_volume(sets) == 500.0


# ============================================================================
# SECTION 5: String similarity utilities (fuzzy matching)
# ============================================================================


class TestTrigramSimilarity:
    """Postcondition: result in [0, 1]. Invariant: symmetric."""

    def test_postcondition_range_zero_one(self) -> None:
        """Postcondition: similarity in [0, 1]."""
        result = trigram_similarity("bench", "bench press")
        assert 0 <= result <= 1

    def test_postcondition_identical_strings(self) -> None:
        """Postcondition: identical strings have similarity 1."""
        result = trigram_similarity("bench", "bench")
        assert result == pytest.approx(1.0)

    def test_postcondition_empty_string(self) -> None:
        """Postcondition: empty string has 0 similarity."""
        assert trigram_similarity("", "bench") == 0.0
        assert trigram_similarity("bench", "") == 0.0

    def test_invariant_symmetry(self) -> None:
        """Invariant: similarity(a, b) == similarity(b, a)."""
        a, b = "bench press", "benchpress"
        assert trigram_similarity(a, b) == trigram_similarity(b, a)

    def test_postcondition_similar_strings(self) -> None:
        """Postcondition: similar strings have high similarity."""
        result = trigram_similarity("bench", "benches")
        assert result > 0.5


class TestDamerauLevenshtein:
    """Postcondition: distance >= 0.

    Invariant: symmetric, d(a,b) <= max(len(a), len(b)).
    """

    def test_postcondition_identical_strings(self) -> None:
        """Postcondition: identical strings have distance 0."""
        assert damerau_levenshtein("bench", "bench") == 0

    def test_postcondition_empty_strings(self) -> None:
        """Postcondition: empty vs non-empty distance = len(non-empty)."""
        assert damerau_levenshtein("", "bench") == 5
        assert damerau_levenshtein("bench", "") == 5

    def test_postcondition_non_negative(self) -> None:
        """Postcondition: distance is always >= 0."""
        result = damerau_levenshtein("abc", "xyz")
        assert result >= 0

    def test_invariant_symmetry(self) -> None:
        """Invariant: d(a, b) == d(b, a)."""
        a, b = "bench", "benches"
        assert damerau_levenshtein(a, b) == damerau_levenshtein(b, a)

    def test_postcondition_transposition(self) -> None:
        """Postcondition: transposition distance = 1."""
        # 'bnech' -> 'bench' is one transposition
        result = damerau_levenshtein("bnech", "bench")
        assert result == 1


# ============================================================================
# SECTION 6: Exercise model - Data validation
# ============================================================================


class TestExerciseCreation:
    """Precondition: name non-empty. Postcondition: normalized_name auto-populated."""

    def test_precondition_empty_name_rejected(self) -> None:
        """Precondition: empty names are rejected."""
        with pytest.raises(ValueError, match="cannot be empty"):
            Exercise(name="")

    def test_precondition_whitespace_name_rejected(self) -> None:
        """Precondition: whitespace-only names rejected."""
        with pytest.raises(ValueError):
            Exercise(name="   ")

    def test_postcondition_normalized_name_auto_populated(self) -> None:
        """Postcondition: normalized_name is auto-set from name."""
        ex = Exercise(name="Bench Press")
        assert ex.normalized_name == "benchpress"

    def test_postcondition_explicit_normalized_name_preserved(self) -> None:
        """Postcondition: explicit normalized_name is preserved."""
        ex = Exercise(name="Bench Press", normalized_name="custom")
        # normalized_name is frozen, so explicit values are kept
        assert ex.normalized_name == "custom"

    def test_postcondition_to_dict(self) -> None:
        """Postcondition: to_dict() returns dict with all fields."""
        ex = Exercise(name="Bench Press", id=1, use_count=10)
        d = ex.to_dict()
        assert d["name"] == "Bench Press"
        assert d["id"] == 1
        assert d["use_count"] == 10


class TestWorkoutSetValidation:
    """Precondition: unit in {lbs, kg}, rpe in [0, 10], reps/weight >= 0."""

    def test_precondition_invalid_unit_rejected(self) -> None:
        """Precondition: invalid unit rejected."""
        with pytest.raises(ValueError, match="unit must be"):
            WorkoutSet(workout_id=1, exercise_id=1, unit="stones")

    def test_precondition_rpe_out_of_range(self) -> None:
        """Precondition: RPE outside [0, 10] rejected."""
        with pytest.raises(ValueError, match="rpe must be between"):
            WorkoutSet(workout_id=1, exercise_id=1, rpe=11)
        with pytest.raises(ValueError, match="rpe must be between"):
            WorkoutSet(workout_id=1, exercise_id=1, rpe=-1)

    def test_precondition_negative_reps_rejected(self) -> None:
        """Precondition: negative reps rejected."""
        with pytest.raises(ValueError, match="reps must be"):
            WorkoutSet(workout_id=1, exercise_id=1, planned_reps=-5)

    def test_precondition_negative_weight_rejected(self) -> None:
        """Precondition: negative weight rejected."""
        with pytest.raises(ValueError, match="weight must be"):
            WorkoutSet(workout_id=1, exercise_id=1, planned_weight=-10)

    def test_postcondition_valid_unit_accepted(self) -> None:
        """Postcondition: valid units accepted."""
        s1 = WorkoutSet(workout_id=1, exercise_id=1, unit="lbs")
        s2 = WorkoutSet(workout_id=1, exercise_id=1, unit="kg")
        assert s1.unit == "lbs"
        assert s2.unit == "kg"


class TestWorkoutValidation:
    """Precondition: date ISO format, status valid. Postcondition: sets initialized."""

    def test_precondition_invalid_date_format_rejected(self) -> None:
        """Precondition: invalid date format rejected."""
        with pytest.raises(ValueError, match="ISO YYYY-MM-DD"):
            Workout(date="2024/05/01")

    def test_precondition_invalid_status_rejected(self) -> None:
        """Precondition: invalid status rejected."""
        with pytest.raises(ValueError, match="status must be"):
            Workout(date="2024-05-01", status="unknown")

    def test_postcondition_sets_defaults_to_empty(self) -> None:
        """Postcondition: sets defaults to empty list."""
        w = Workout(date="2024-05-01")
        assert w.sets == []
        assert isinstance(w.sets, list)

    def test_postcondition_valid_status_accepted(self) -> None:
        """Postcondition: valid statuses accepted."""
        for status in ["planned", "in_progress", "completed"]:
            w = Workout(date="2024-05-01", status=status)
            assert w.status == status


# ============================================================================
# SECTION 7: Aggregation functions (per-exercise summaries, PRs, frequency)
# ============================================================================


class TestPerExerciseSummary:
    """Postcondition: aggregates by exercise_id, sorted by volume desc."""

    def test_postcondition_aggregates_by_exercise(self) -> None:
        """Postcondition: groups sets by exercise_id."""
        sets = [
            WorkoutSet(
                workout_id=1,
                exercise_id=1,
                actual_reps=5,
                actual_weight=100,
                executed=True,
                exercise_name="Bench Press",
            ),
            WorkoutSet(
                workout_id=1,
                exercise_id=1,
                actual_reps=3,
                actual_weight=150,
                executed=True,
                exercise_name="Bench Press",
            ),
        ]
        result = per_exercise_summary(sets)
        assert len(result) == 1
        assert result[0].total_sets == 2

    def test_postcondition_sorted_by_volume(self) -> None:
        """Postcondition: results sorted by volume descending."""
        sets = [
            WorkoutSet(
                workout_id=1,
                exercise_id=1,
                actual_reps=5,
                actual_weight=100,
                executed=True,
                exercise_name="Bench Press",
            ),
            WorkoutSet(
                workout_id=1,
                exercise_id=2,
                actual_reps=10,
                actual_weight=50,
                executed=True,
                exercise_name="Row",
            ),
        ]
        result = per_exercise_summary(sets)
        # Bench: 500, Row: 500, but Bench is first in input
        assert result[0].exercise_name == "Bench Press"

    def test_edge_case_empty_input(self) -> None:
        """Edge case: empty sets list."""
        assert per_exercise_summary([]) == []

    def test_edge_case_unexecuted_sets_ignored(self) -> None:
        """Edge case: unexecuted sets are filtered out."""
        sets = [
            WorkoutSet(
                workout_id=1,
                exercise_id=1,
                actual_reps=5,
                actual_weight=100,
                executed=False,
                exercise_name="Bench Press",
            )
        ]
        assert per_exercise_summary(sets) == []


class TestPersonalRecords:
    """Postcondition: three PRs per exercise (weight, reps, e1rm)."""

    def test_postcondition_three_prs_per_exercise(self) -> None:
        """Postcondition: returns 3 PRs per exercise."""
        sets = [
            WorkoutSet(
                workout_id=1,
                exercise_id=1,
                actual_reps=5,
                actual_weight=100,
                executed=True,
                completed_at="2024-05-01T10:00:00",
                exercise_name="Bench Press",
            )
        ]
        prs = personal_records(sets)
        # 3 metrics: max_weight, max_reps, best_e1rm
        assert len(prs) == 3

    def test_postcondition_pr_metric_names(self) -> None:
        """Postcondition: PR metrics are max_weight, max_reps, best_e1rm."""
        sets = [
            WorkoutSet(
                workout_id=1,
                exercise_id=1,
                actual_reps=5,
                actual_weight=100,
                executed=True,
                completed_at="2024-05-01T10:00:00",
                exercise_name="Bench Press",
            )
        ]
        prs = personal_records(sets)
        metrics = {pr.metric for pr in prs}
        assert metrics == {"max_weight", "max_reps", "best_e1rm"}


class TestFrequency:
    """Postcondition: counts distinct days per exercise, computes days_since_last."""

    def test_postcondition_counts_distinct_days(self) -> None:
        """Postcondition: counts distinct training days."""
        sets = [
            WorkoutSet(
                workout_id=1,
                exercise_id=1,
                executed=True,
                completed_at="2024-05-01T10:00:00",
                exercise_name="Bench Press",
            ),
            WorkoutSet(
                workout_id=2,
                exercise_id=1,
                executed=True,
                completed_at="2024-05-02T10:00:00",
                exercise_name="Bench Press",
            ),
        ]
        freq = frequency(sets, today="2024-05-05")
        assert freq[0].sessions == 2

    def test_postcondition_days_since_last(self) -> None:
        """Postcondition: computes days since last performed."""
        sets = [
            WorkoutSet(
                workout_id=1,
                exercise_id=1,
                executed=True,
                completed_at="2024-05-01T10:00:00",
                exercise_name="Bench Press",
            )
        ]
        freq = frequency(sets, today="2024-05-06")
        assert freq[0].days_since_last == 5

    def test_edge_case_empty_sets(self) -> None:
        """Edge case: empty sets."""
        assert frequency([]) == []


class TestOverview:
    """Postcondition: counts workouts, sets, volume, exercises, last date."""

    def test_postcondition_counts_workouts(self) -> None:
        """Postcondition: distinct workout count."""
        sets = [
            WorkoutSet(
                workout_id=1,
                exercise_id=1,
                actual_reps=5,
                actual_weight=100,
                executed=True,
                completed_at="2024-05-01T10:00:00",
            ),
            WorkoutSet(
                workout_id=2,
                exercise_id=1,
                actual_reps=5,
                actual_weight=100,
                executed=True,
                completed_at="2024-05-02T10:00:00",
            ),
        ]
        ov = overview(sets)
        assert ov.total_workouts == 2

    def test_postcondition_counts_sets(self) -> None:
        """Postcondition: executed set count."""
        sets = [
            WorkoutSet(
                workout_id=1,
                exercise_id=1,
                actual_reps=5,
                actual_weight=100,
                executed=True,
            ),
            WorkoutSet(
                workout_id=1,
                exercise_id=1,
                actual_reps=5,
                actual_weight=100,
                executed=False,
            ),
        ]
        ov = overview(sets)
        assert ov.total_sets == 1  # unexecuted filtered

    def test_postcondition_counts_distinct_exercises(self) -> None:
        """Postcondition: distinct exercise count."""
        sets = [
            WorkoutSet(
                workout_id=1,
                exercise_id=1,
                actual_reps=5,
                actual_weight=100,
                executed=True,
            ),
            WorkoutSet(
                workout_id=1,
                exercise_id=2,
                actual_reps=5,
                actual_weight=100,
                executed=True,
            ),
        ]
        ov = overview(sets)
        assert ov.distinct_exercises == 2

    def test_edge_case_empty_sets(self) -> None:
        """Edge case: empty sets list."""
        ov = overview([])
        assert ov.total_workouts == 0
        assert ov.total_sets == 0
        assert ov.total_volume == 0.0

    def test_postcondition_last_workout_date(self) -> None:
        """Postcondition: last_workout_date is set correctly."""
        sets = [
            WorkoutSet(
                workout_id=1,
                exercise_id=1,
                actual_reps=5,
                actual_weight=100,
                executed=True,
                completed_at="2024-05-01T10:00:00",
            ),
            WorkoutSet(
                workout_id=1,
                exercise_id=1,
                actual_reps=5,
                actual_weight=100,
                executed=True,
                completed_at="2024-05-05T10:00:00",
            ),
        ]
        ov = overview(sets)
        assert ov.last_workout_date == "2024-05-05"


class TestAutocompleteScoring:
    """Test the scoring function for exercise autocomplete."""

    def test_postcondition_exact_match_bonus(self) -> None:
        """Postcondition: exact matches get high score."""
        ex = Exercise(name="Bench Press")
        from workout_tracker.models import normalize_name

        query = normalize_name("Bench Press")
        s = score(query, ex)
        assert s >= 5000

    def test_postcondition_prefix_match_bonus(self) -> None:
        """Postcondition: prefix matches get bonus."""
        ex = Exercise(name="Bench Press")
        from workout_tracker.models import normalize_name

        query = normalize_name("Bench")
        s = score(query, ex)
        assert s >= 1500

    def test_postcondition_substring_bonus(self) -> None:
        """Postcondition: substring matches get moderate bonus."""
        ex = Exercise(name="Bench Press")
        from workout_tracker.models import normalize_name

        query = normalize_name("ench")
        s = score(query, ex)
        assert s > 0

    def test_postcondition_use_count_contributes(self) -> None:
        """Postcondition: use_count contributes to score."""
        ex1 = Exercise(name="Bench Press", use_count=0)
        ex2 = Exercise(name="Bench Press", use_count=100)
        from workout_tracker.models import normalize_name

        query = normalize_name("test")
        s1 = score(query, ex1)
        s2 = score(query, ex2)
        assert s2 > s1


class TestSuggest:
    """Test the suggest function for autocomplete."""

    def test_postcondition_returns_list(self) -> None:
        """Postcondition: suggest returns a list."""
        exercises = [
            Exercise(name="Bench Press"),
            Exercise(name="Squat"),
        ]
        result = suggest("bench", exercises)
        assert isinstance(result, list)

    def test_postcondition_respects_limit(self) -> None:
        """Postcondition: respects the limit parameter."""
        exercises = [
            Exercise(name="Bench Press"),
            Exercise(name="Incline Press"),
            Exercise(name="Dumbbell Press"),
        ]
        result = suggest("press", exercises, limit=2)
        assert len(result) <= 2

    def test_postcondition_empty_query_returns_by_popularity(self) -> None:
        """Postcondition: empty query returns most-used exercises."""
        exercises = [
            Exercise(name="Bench Press", use_count=100),
            Exercise(name="Squat", use_count=50),
        ]
        result = suggest("", exercises, limit=10)
        # Should be sorted by use_count descending
        assert result[0].name == "Bench Press"

    def test_postcondition_min_score_filtering(self) -> None:
        """Postcondition: respects min_score parameter."""
        exercises = [
            Exercise(name="xyz"),  # Low similarity to query
        ]
        result = suggest("abc", exercises, min_score=1000.0)
        # Should filter out low-scoring exercises
        assert len(result) == 0

    def test_edge_case_empty_catalog(self) -> None:
        """Edge case: empty exercise catalog."""
        result = suggest("bench", [], limit=10)
        assert result == []


class TestExerciseTimeseries:
    """Test the exercise_timeseries function."""

    def test_postcondition_returns_list(self) -> None:
        """Postcondition: returns list of TimePoint."""
        sets = [
            WorkoutSet(
                workout_id=1,
                exercise_id=1,
                actual_reps=5,
                actual_weight=100,
                executed=True,
                completed_at="2024-05-01T10:00:00",
            )
        ]
        result = exercise_timeseries(sets)
        assert isinstance(result, list)

    def test_postcondition_sorted_by_date(self) -> None:
        """Postcondition: results are sorted by date."""
        sets = [
            WorkoutSet(
                workout_id=1,
                exercise_id=1,
                actual_reps=5,
                actual_weight=100,
                executed=True,
                completed_at="2024-05-03T10:00:00",
            ),
            WorkoutSet(
                workout_id=1,
                exercise_id=1,
                actual_reps=5,
                actual_weight=100,
                executed=True,
                completed_at="2024-05-01T10:00:00",
            ),
        ]
        result = exercise_timeseries(sets)
        assert result[0].date == "2024-05-01"
        assert result[1].date == "2024-05-03"

    def test_edge_case_no_completed_at(self) -> None:
        """Edge case: sets without completed_at are skipped."""
        sets = [
            WorkoutSet(
                workout_id=1,
                exercise_id=1,
                actual_reps=5,
                actual_weight=100,
                executed=True,
                completed_at=None,
            )
        ]
        result = exercise_timeseries(sets)
        assert result == []
