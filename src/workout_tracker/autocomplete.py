"""Fuzzy autocomplete for exercise names.

Pure functions - no DB. Caller passes in the catalog of known exercises.

Ranking signals (combined into a single score):
1. Exact normalized match    -> +5000
2. Normalized prefix match   -> +1500
3. Substring match           -> +700
4. Trigram similarity (Dice) -> +600 * sim
5. Damerau-Levenshtein dist  -> +400 * (1 - d/maxlen)
6. Use-count popularity      -> + min(use_count, 100)

Empty/whitespace queries fall back to a popularity-ranked top-N.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable

from workout_tracker.models import Exercise, normalize_name


def _trigrams(s: str) -> set[str]:
    s = f"  {s}  "
    return {s[i : i + 3] for i in range(len(s) - 2)}


def trigram_similarity(a: str, b: str) -> float:
    """Sorensen-Dice coefficient on character trigrams. Range [0, 1]."""
    if not a or not b:
        return 0.0
    ta, tb = _trigrams(a), _trigrams(b)
    if not ta or not tb:
        return 0.0
    inter = len(ta & tb)
    return 2 * inter / (len(ta) + len(tb))


def damerau_levenshtein(a: str, b: str) -> int:
    """Edit distance with adjacent transpositions. Optimal for catching typos
    like 'bnech' -> 'bench'."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    la, lb = len(a), len(b)
    # 2D dp
    d = [[0] * (lb + 1) for _ in range(la + 1)]
    for i in range(la + 1):
        d[i][0] = i
    for j in range(lb + 1):
        d[0][j] = j
    for i in range(1, la + 1):
        for j in range(1, lb + 1):
            cost = 0 if a[i - 1] == b[j - 1] else 1
            d[i][j] = min(
                d[i - 1][j] + 1,
                d[i][j - 1] + 1,
                d[i - 1][j - 1] + cost,
            )
            if i > 1 and j > 1 and a[i - 1] == b[j - 2] and a[i - 2] == b[j - 1]:
                d[i][j] = min(d[i][j], d[i - 2][j - 2] + cost)
    return d[la][lb]


def score(query_norm: str, exercise: Exercise) -> float:
    n = exercise.normalized_name
    if not n:
        return 0.0
    s = 0.0
    if n == query_norm:
        s += 5000
    if n.startswith(query_norm):
        s += 1500
    elif query_norm in n:
        s += 700
    s += 600 * trigram_similarity(query_norm, n)
    maxlen = max(len(query_norm), len(n))
    if maxlen:
        d = damerau_levenshtein(query_norm, n)
        # Only credit if the edit distance is small relative to the lengths
        if d <= max(2, maxlen // 3):
            s += 400 * (1 - d / maxlen)
    s += min(exercise.use_count, 100)
    return s


def suggest(
    query: str,
    catalog: Iterable[Exercise],
    limit: int = 8,
    min_score: float = 50.0,
    alias_resolver: Callable[[str], Exercise | None] | None = None,
) -> list[Exercise]:
    """Return ranked suggestions. Empty query returns most-used exercises."""
    catalog_list = list(catalog)
    q = normalize_name(query)
    if not q:
        return sorted(catalog_list, key=lambda e: -e.use_count)[:limit]

    # Detect multi-word queries
    tokens_raw = query.strip().split()
    is_multiword = len(tokens_raw) > 1

    if is_multiword:
        tokens = [normalize_name(t) for t in tokens_raw if normalize_name(t)]
        scored: list[tuple[float, Exercise]] = []
        for ex in catalog_list:
            if all(t in ex.normalized_name for t in tokens):
                sc = min(ex.use_count, 100) + 100.0  # base score for multiword matches
                scored.append((sc, ex))
        scored.sort(key=lambda p: (-p[0], p[1].name.lower()))
        return [ex for _, ex in scored[:limit]]

    # Check alias resolver before main loop
    alias_boost_id: int | None = None
    if alias_resolver and q:
        resolved = alias_resolver(q)
        if resolved is not None:
            alias_boost_id = resolved.id

    scored2: list[tuple[float, Exercise]] = []
    for ex in catalog_list:
        sc = score(q, ex)
        if alias_boost_id is not None and ex.id == alias_boost_id:
            sc += 6000
        if sc >= min_score:
            scored2.append((sc, ex))
    scored2.sort(key=lambda p: (-p[0], p[1].name.lower()))
    return [ex for _, ex in scored2[:limit]]
