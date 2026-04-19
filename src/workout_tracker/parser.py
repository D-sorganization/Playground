"""Parse free-text workout notes into structured sets.

Supported line formats (examples):

    Bench Press 3x5 @ 135           # 3 sets of 5 reps at 135
    Squat 5x5 @ 225 lbs RPE 8       # rpe optional, unit optional
    Deadlift 1x5 @ 315kg
    Pull-ups 3x8                    # bodyweight (no weight)
    Bench Press                     # exercise header...
      135x5                         # ...followed by indented set lines
      155x5
      175x5

Each parsed entry has the shape:
    ParsedEntry(exercise_name=str, sets=[ParsedSet(reps, weight, rpe, unit), ...])
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Regex pieces.
_NUM = r"\d+(?:\.\d+)?"
_UNIT = r"(?:lbs?|kg)"

# Pattern A:  "<sets>x<reps> @ <weight>[unit]"  (e.g. 3x5 @ 135 lbs)
_RE_SETS_REPS_WEIGHT = re.compile(
    rf"(?P<sets>\d+)\s*[x\u00d7]\s*(?P<reps>\d+)"
    rf"(?:\s*@\s*(?P<weight>{_NUM})\s*(?P<unit>{_UNIT})?)?"
    rf"(?:\s*(?:rpe|@rpe)\s*(?P<rpe>{_NUM}))?",
    re.IGNORECASE,
)

# Pattern B:  "<weight>x<reps>"  (e.g. 135x5)  -- weight first, single set
_RE_WEIGHT_X_REPS = re.compile(
    rf"^(?P<weight>{_NUM})\s*[x\u00d7]\s*(?P<reps>\d+)"
    rf"(?:\s*(?P<unit>{_UNIT}))?"
    rf"(?:\s*(?:rpe|@rpe)\s*(?P<rpe>{_NUM}))?$",
    re.IGNORECASE,
)

# Pattern C:  "<reps> @ <weight>[unit]"  (e.g. 5 @ 135)
_RE_REPS_AT_WEIGHT = re.compile(
    rf"^(?P<reps>\d+)\s*@\s*(?P<weight>{_NUM})\s*(?P<unit>{_UNIT})?"
    rf"(?:\s*(?:rpe|@rpe)\s*(?P<rpe>{_NUM}))?$",
    re.IGNORECASE,
)

# Pattern D: "<reps>" alone (e.g. 5) -- 1 set, bodyweight
_RE_REPS_ONLY = re.compile(r"^(?P<reps>\d+)$")


@dataclass
class ParsedSet:
    reps: int
    weight: float | None = None
    rpe: float | None = None
    unit: str = "lbs"


@dataclass
class ParsedEntry:
    exercise_name: str
    sets: list[ParsedSet] = field(default_factory=list)


def _normalize_unit(u: str | None) -> str:
    if not u:
        return "lbs"
    u = u.lower()
    return "kg" if u == "kg" else "lbs"


def _try_parse_set_line(line: str) -> list[ParsedSet] | None:
    """Try to parse a line that consists ONLY of set spec(s)."""
    s = line.strip().rstrip(",")
    # Multiple set specs separated by commas
    pieces = [p.strip() for p in s.split(",") if p.strip()]
    if len(pieces) > 1:
        out: list[ParsedSet] = []
        for p in pieces:
            sub = _try_parse_set_line(p)
            if sub is None:
                return None
            out.extend(sub)
        return out

    m = _RE_WEIGHT_X_REPS.match(s)
    if m:
        return [
            ParsedSet(
                reps=int(m["reps"]),
                weight=float(m["weight"]),
                rpe=float(m["rpe"]) if m["rpe"] else None,
                unit=_normalize_unit(m["unit"]),
            )
        ]
    m = _RE_REPS_AT_WEIGHT.match(s)
    if m:
        return [
            ParsedSet(
                reps=int(m["reps"]),
                weight=float(m["weight"]),
                rpe=float(m["rpe"]) if m["rpe"] else None,
                unit=_normalize_unit(m["unit"]),
            )
        ]
    # 3x5 @ 135  OR  3x5 (bodyweight)
    m = _RE_SETS_REPS_WEIGHT.fullmatch(s)
    if m:
        n_sets = int(m["sets"])
        reps = int(m["reps"])
        weight = float(m["weight"]) if m["weight"] else None
        rpe = float(m["rpe"]) if m["rpe"] else None
        unit = _normalize_unit(m["unit"])
        return [
            ParsedSet(reps=reps, weight=weight, rpe=rpe, unit=unit)
            for _ in range(n_sets)
        ]
    m = _RE_REPS_ONLY.match(s)
    if m:
        return [ParsedSet(reps=int(m["reps"]))]
    return None


_WEIGHT_VS_SETS_THRESHOLD = 15


def _try_parse_full_line(line: str) -> ParsedEntry | None:
    """Parse '<exercise> <NxM> [@ <weight>[unit]] [RPE n]'.

    Disambiguation when there's no explicit weight:
      - NxM with N > threshold  -> weight x reps single set
          e.g. 'Bench Press 135x5'
      - NxM with N <= threshold -> N sets x M reps bodyweight
          e.g. 'Pull-ups 3x8'
    """
    s = line.strip()
    m = _RE_SETS_REPS_WEIGHT.search(s)
    if not m:
        return None
    name = s[: m.start()].strip(" :\t-")
    if not name:
        return None
    n_first = int(m["sets"])
    n_second = int(m["reps"])
    weight = float(m["weight"]) if m["weight"] else None
    rpe = float(m["rpe"]) if m["rpe"] else None
    unit = _normalize_unit(m["unit"])

    if weight is not None:
        # "N sets x M reps @ W"
        sets = [
            ParsedSet(reps=n_second, weight=weight, rpe=rpe, unit=unit)
            for _ in range(n_first)
        ]
    elif n_first > _WEIGHT_VS_SETS_THRESHOLD:
        # "Bench Press 135x5" - single set, weight x reps
        sets = [
            ParsedSet(
                reps=n_second, weight=float(n_first), rpe=rpe, unit=unit
            )
        ]
    else:
        # "Pull-ups 3x8" - N sets x M reps bodyweight
        sets = [
            ParsedSet(reps=n_second, weight=None, rpe=rpe, unit=unit)
            for _ in range(n_first)
        ]
    return ParsedEntry(exercise_name=name, sets=sets)


def parse_notes(text: str) -> list[ParsedEntry]:
    """Parse free-text notes into structured entries.

    Empty lines reset the current exercise context.
    """
    entries: list[ParsedEntry] = []
    current: ParsedEntry | None = None

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        if not line.strip():
            current = None
            continue
        # Strip leading bullets / dashes for ergonomics
        stripped = line.lstrip(" \t-*\u2022")
        # Try set-only line first (will only match if numeric)
        sets = _try_parse_set_line(stripped)
        if sets is not None:
            if current is None:
                # set without exercise context — skip
                continue
            current.sets.extend(sets)
            continue
        # Try full single-line entry
        full = _try_parse_full_line(stripped)
        if full is not None:
            entries.append(full)
            current = full
            continue
        # Otherwise treat as exercise header (name)
        current = ParsedEntry(exercise_name=stripped.rstrip(":").strip())
        entries.append(current)

    # Drop entries with no sets if name also empty (defensive)
    return [e for e in entries if e.exercise_name]
