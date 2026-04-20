"""Tests for workout_tracker.autocomplete."""

from __future__ import annotations

import pytest

from workout_tracker.autocomplete import (
    damerau_levenshtein,
    suggest,
    trigram_similarity,
)
from workout_tracker.models import Exercise


def _ex(name: str, use_count: int = 0, id_: int | None = None) -> Exercise:
    return Exercise(name=name, id=id_, use_count=use_count)


class TestTrigramSimilarity:
    def test_identical(self) -> None:
        assert trigram_similarity("bench", "bench") == pytest.approx(1.0)

    def test_disjoint(self) -> None:
        assert trigram_similarity("abc", "xyz") < 0.2

    def test_partial(self) -> None:
        sim = trigram_similarity("benchpress", "benchpres")
        assert 0.5 < sim < 1.0

    def test_empty_strings(self) -> None:
        assert trigram_similarity("", "x") == 0.0
        assert trigram_similarity("x", "") == 0.0


class TestDamerauLevenshtein:
    def test_identical(self) -> None:
        assert damerau_levenshtein("abc", "abc") == 0

    def test_single_transposition_is_one(self) -> None:
        assert damerau_levenshtein("bench", "benhc") == 1

    def test_single_insertion(self) -> None:
        assert damerau_levenshtein("bench", "benchs") == 1

    def test_empty(self) -> None:
        assert damerau_levenshtein("", "abc") == 3
        assert damerau_levenshtein("abc", "") == 3


class TestSuggest:
    def setup_method(self) -> None:
        self.catalog = [
            _ex("Bench Press", use_count=50, id_=1),
            _ex("Bent-Over Row", use_count=5, id_=2),
            _ex("Barbell Squat", use_count=10, id_=3),
            _ex("Deadlift", use_count=30, id_=4),
            _ex("Pull-Up", use_count=2, id_=5),
        ]

    def test_empty_query_returns_most_used(self) -> None:
        out = suggest("", self.catalog, limit=3)
        assert [e.name for e in out] == ["Bench Press", "Deadlift", "Barbell Squat"]

    def test_prefix_match_ranks_high(self) -> None:
        out = suggest("ben", self.catalog)
        assert out[0].name == "Bench Press"

    def test_substring_match(self) -> None:
        out = suggest("squat", self.catalog)
        assert out[0].name == "Barbell Squat"

    def test_typo_recovery(self) -> None:
        # 'bnech' is a transposition of 'bench'
        out = suggest("bnech", self.catalog)
        assert out and out[0].name == "Bench Press"

    def test_limit_respected(self) -> None:
        out = suggest("e", self.catalog, limit=2)
        assert len(out) <= 2

    def test_use_count_breaks_ties(self) -> None:
        cat = [
            _ex("Lunge", use_count=1, id_=1),
            _ex("Lunge Reverse", use_count=100, id_=2),
        ]
        out = suggest("lu", cat)
        assert out[0].name == "Lunge Reverse" or out[0].use_count == 100


class TestSuggestMultiword:
    def setup_method(self) -> None:
        self.catalog = [
            _ex("Bench Press", use_count=50, id_=1),
            _ex("Incline Bench Press", use_count=10, id_=2),
            _ex("Barbell Squat", use_count=30, id_=3),
            _ex("Deadlift", use_count=20, id_=4),
        ]

    def test_multiword_requires_all_tokens(self) -> None:
        out = suggest("bench press", self.catalog)
        names = [e.name for e in out]
        assert "Bench Press" in names
        assert "Incline Bench Press" in names
        assert "Deadlift" not in names

    def test_multiword_partial_no_match(self) -> None:
        out = suggest("bench deadlift", self.catalog)
        # No exercise has both 'bench' and 'deadlift' in its name
        assert out == []

    def test_single_word_not_affected(self) -> None:
        out = suggest("bench", self.catalog)
        # Should still work normally
        assert len(out) > 0
        assert out[0].name in ("Bench Press", "Incline Bench Press")


class TestSuggestAliasResolver:
    def setup_method(self) -> None:
        self.bp = _ex("Bench Press", use_count=50, id_=1)
        self.squat = _ex("Barbell Squat", use_count=30, id_=2)
        self.catalog = [self.bp, self.squat]

    def test_alias_boost_promotes_exercise(self) -> None:
        def resolver(q: str):
            if q == "bp":
                return self.bp
            return None

        out = suggest("bp", self.catalog, alias_resolver=resolver)
        # "bp" normalized is "bp"; alias resolver returns bench press -> should be ranked first  # noqa: E501
        assert out and out[0].id == self.bp.id

    def test_no_alias_resolver_works_normally(self) -> None:
        out = suggest("bench", self.catalog)
        assert out and out[0].name == "Bench Press"

    def test_alias_resolver_none_query_no_crash(self) -> None:
        def resolver(q: str):
            return None

        out = suggest("bench", self.catalog, alias_resolver=resolver)
        assert out and out[0].name == "Bench Press"
