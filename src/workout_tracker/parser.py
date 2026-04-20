"""Parse free-text workout notes into structured sets.

Supported line formats (examples):

    Bench Press 3x5 @ 135           # 3 sets of 5 reps at 135
    Squat 5x5 @ 225 lbs RPE 8       # rpe optional, unit optional
    Deadlift 1x5 @ 315kg
    Pull-ups 3x8                    # bodyweight (no weight)
    Weighted Pull-ups 3x5 @ BW+25   # bodyweight + 25 lbs added
    Dips BW+45x10                   # bodyweight + 45 lbs, 10 reps
    Bench Press 3x5 @ 135 AMRAP     # protocol keyword
    Bench Press                     # exercise header...
      135x5                         # ...followed by indented set lines
      155x5
      175x5

Each parsed entry has the shape:
    ParsedEntry(exercise_name=str, sets=[ParsedSet(...), ...])
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# Regex pieces.
_NUM = r"\d+(?:\.\d+)?"
_UNIT = r"(?:lbs?|kg)"

# Protocol keywords at end of set spec.
_PROTOCOL_KW = r"(?:amrap|emom|drop[\s_]?set|failure|partials)"
_PROTOCOL_RE = re.compile(rf"\b({_PROTOCOL_KW})\s*$", re.IGNORECASE)

# BW weight token: "BW" or "BW+25" or "bodyweight+25"
_BW_TOKEN = rf"(?:bw|bodyweight)(?:\s*\+\s*(?P<bw_added>{_NUM}))?"
_BW_TOKEN_RE = re.compile(rf"^{_BW_TOKEN}$", re.IGNORECASE)

# Pattern A:  "<sets>x<reps> @ <weight>[unit]"  (e.g. 3x5 @ 135 lbs)
_RE_SETS_REPS_WEIGHT = re.compile(
    rf"(?P<sets>\d+)\s*[x\u00d7]\s*(?P<reps>\d+)"
    rf"(?:\s*@\s*(?P<weight>{_NUM})\s*(?P<unit>{_UNIT})?)?"
    rf"(?:\s*(?:rpe|@rpe)\s*(?P<rpe>{_NUM}))?",
    re.IGNORECASE,
)

# Pattern A-BW: "<sets>x<reps> @ BW[+N][unit]"
_RE_SETS_REPS_AT_BW = re.compile(
    rf"(?P<sets>\d+)\s*[x\u00d7]\s*(?P<reps>\d+)"
    rf"\s*@\s*(?:bw|bodyweight)(?:\s*\+\s*(?P<bw_added>{_NUM}))?"
    rf"\s*(?:{_UNIT})?"
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

# Pattern B-BW: "BW[+N]x<reps>"  (e.g. BW+25x8)
_RE_BW_X_REPS = re.compile(
    rf"^(?:bw|bodyweight)(?:\s*\+\s*(?P<bw_added>{_NUM}))?\s*[x\u00d7]\s*(?P<reps>\d+)"
    rf"(?:\s*(?:{_UNIT}))?"
    rf"(?:\s*(?:rpe|@rpe)\s*(?P<rpe>{_NUM}))?$",
    re.IGNORECASE,
)

# Pattern C:  "<reps> @ <weight>[unit]"  (e.g. 5 @ 135)
_RE_REPS_AT_WEIGHT = re.compile(
    rf"^(?P<reps>\d+)\s*@\s*(?P<weight>{_NUM})\s*(?P<unit>{_UNIT})?"
    rf"(?:\s*(?:rpe|@rpe)\s*(?P<rpe>{_NUM}))?$",
    re.IGNORECASE,
)

# Pattern C-BW: "<reps> @ BW[+N]"
_RE_REPS_AT_BW = re.compile(
    rf"^(?P<reps>\d+)\s*@\s*(?:bw|bodyweight)(?:\s*\+\s*(?P<bw_added>{_NUM}))?"
    rf"\s*(?:{_UNIT})?"
    rf"(?:\s*(?:rpe|@rpe)\s*(?P<rpe>{_NUM}))?$",
    re.IGNORECASE,
)

# Pattern D: "<reps>" alone (e.g. 5) -- 1 set, bodyweight
_RE_REPS_ONLY = re.compile(r"^(?P<reps>\d+)$")

_PROTOCOL_MAP = {
    "amrap": "amrap",
    "emom": "emom",
    "dropset": "drop_set",
    "drop set": "drop_set",
    "drop_set": "drop_set",
    "failure": "failure",
    "partials": "partials",
}


def _extract_protocol(s: str) -> tuple[str, str | None]:
    """Strip trailing protocol keyword from s, return (remainder, protocol)."""
    m = _PROTOCOL_RE.search(s)
    if not m:
        return s, None
    kw = re.sub(r"\s+", "", m.group(1).lower())  # normalise spaces
    protocol = _PROTOCOL_MAP.get(kw) or _PROTOCOL_MAP.get(m.group(1).lower())
    return s[: m.start()].rstrip(), protocol


@dataclass
class ParsedSet:
    reps: int
    weight: float | None = None
    rpe: float | None = None
    unit: str = "lbs"
    is_bodyweight: bool = False
    protocol: str | None = None


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
    s, protocol = _extract_protocol(s)

    # Multiple set specs separated by commas
    if not protocol:
        pieces = [p.strip() for p in s.split(",") if p.strip()]
        if len(pieces) > 1:
            out: list[ParsedSet] = []
            for p in pieces:
                sub = _try_parse_set_line(p)
                if sub is None:
                    return None
                out.extend(sub)
            return out

    # BW+N x reps
    m = _RE_BW_X_REPS.match(s)
    if m:
        return [
            ParsedSet(
                reps=int(m["reps"]),
                weight=float(m["bw_added"]) if m["bw_added"] else None,
                rpe=float(m["rpe"]) if m["rpe"] else None,
                unit="lbs",
                is_bodyweight=True,
                protocol=protocol,
            )
        ]

    # reps @ BW[+N]
    m = _RE_REPS_AT_BW.match(s)
    if m:
        return [
            ParsedSet(
                reps=int(m["reps"]),
                weight=float(m["bw_added"]) if m["bw_added"] else None,
                rpe=float(m["rpe"]) if m["rpe"] else None,
                unit="lbs",
                is_bodyweight=True,
                protocol=protocol,
            )
        ]

    m = _RE_WEIGHT_X_REPS.match(s)
    if m:
        return [
            ParsedSet(
                reps=int(m["reps"]),
                weight=float(m["weight"]),
                rpe=float(m["rpe"]) if m["rpe"] else None,
                unit=_normalize_unit(m["unit"]),
                protocol=protocol,
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
                protocol=protocol,
            )
        ]
    # 3x5 @ 135  OR  3x5 (bodyweight)
    m = _RE_SETS_REPS_AT_BW.fullmatch(s)
    if m:
        n_sets = int(m["sets"])
        reps = int(m["reps"])
        bw_added = float(m["bw_added"]) if m["bw_added"] else None
        rpe = float(m["rpe"]) if m["rpe"] else None
        return [
            ParsedSet(
                reps=reps,
                weight=bw_added,
                rpe=rpe,
                unit="lbs",
                is_bodyweight=True,
                protocol=protocol,
            )
            for _ in range(n_sets)
        ]
    m = _RE_SETS_REPS_WEIGHT.fullmatch(s)
    if m:
        n_sets = int(m["sets"])
        reps = int(m["reps"])
        weight = float(m["weight"]) if m["weight"] else None
        rpe = float(m["rpe"]) if m["rpe"] else None
        unit = _normalize_unit(m["unit"])
        return [
            ParsedSet(reps=reps, weight=weight, rpe=rpe, unit=unit, protocol=protocol)
            for _ in range(n_sets)
        ]
    m = _RE_REPS_ONLY.match(s)
    if m:
        return [ParsedSet(reps=int(m["reps"]), protocol=protocol)]
    return None


_WEIGHT_VS_SETS_THRESHOLD = 15


def _try_parse_full_line(line: str) -> ParsedEntry | None:
    """Parse '<exercise> <NxM> [@ <weight>[unit]] [RPE n] [protocol]'.

    Disambiguation when there's no explicit weight:
      - NxM with N > threshold  -> weight x reps single set
          e.g. 'Bench Press 135x5'
      - NxM with N <= threshold -> N sets x M reps bodyweight
          e.g. 'Pull-ups 3x8'
    """
    s = line.strip()
    s, protocol = _extract_protocol(s)

    # Try BW @ weight pattern first
    m = _RE_SETS_REPS_AT_BW.search(s)
    if m:
        name = s[: m.start()].strip(" :\t-")
        if name:
            n_sets = int(m["sets"])
            reps = int(m["reps"])
            bw_added = float(m["bw_added"]) if m["bw_added"] else None
            rpe = float(m["rpe"]) if m["rpe"] else None
            sets = [
                ParsedSet(
                    reps=reps,
                    weight=bw_added,
                    rpe=rpe,
                    unit="lbs",
                    is_bodyweight=True,
                    protocol=protocol,
                )
                for _ in range(n_sets)
            ]
            return ParsedEntry(exercise_name=name, sets=sets)

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
            ParsedSet(
                reps=n_second, weight=weight, rpe=rpe, unit=unit, protocol=protocol
            )
            for _ in range(n_first)
        ]
    elif n_first > _WEIGHT_VS_SETS_THRESHOLD:
        # "Bench Press 135x5" - single set, weight x reps
        sets = [
            ParsedSet(
                reps=n_second,
                weight=float(n_first),
                rpe=rpe,
                unit=unit,
                protocol=protocol,
            )
        ]
    else:
        # "Pull-ups 3x8" - N sets x M reps bodyweight
        sets = [
            ParsedSet(reps=n_second, weight=None, rpe=rpe, unit=unit, protocol=protocol)
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
        # Try set-only line first (will only match if numeric or BW)
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
