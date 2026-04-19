"""Domain models for workout tracker.

Frozen dataclasses for value-like records (Exercise) and mutable for entities
that are updated frequently during a session (Workout, WorkoutSet).
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from datetime import date as date_t
from typing import Any

VALID_STATUSES = ("planned", "in_progress", "completed")
VALID_UNITS = ("lbs", "kg")

_NORMALIZE_RE = re.compile(r"[^a-z0-9]+")


def normalize_name(name: str) -> str:
    """Lowercase, strip non-alphanumerics. Used for matching across typos.

    >>> normalize_name("Bench Press")
    'benchpress'
    >>> normalize_name("Pull-Ups!")
    'pullups'
    """
    return _NORMALIZE_RE.sub("", name.lower()).strip()


@dataclass(frozen=True)
class Exercise:
    name: str
    normalized_name: str = ""
    id: int | None = None
    use_count: int = 0
    last_used_at: str | None = None
    created_at: str | None = None

    def __post_init__(self) -> None:
        if not self.name or not self.name.strip():
            raise ValueError("Exercise name cannot be empty")
        if not self.normalized_name:
            object.__setattr__(self, "normalized_name", normalize_name(self.name))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class WorkoutSet:
    workout_id: int
    exercise_id: int
    position: int | None = None  # None or negative => repo auto-assigns
    id: int | None = None
    planned_reps: int | None = None
    planned_weight: float | None = None
    actual_reps: int | None = None
    actual_weight: float | None = None
    rpe: float | None = None
    unit: str = "lbs"
    executed: bool = False
    notes: str | None = None
    completed_at: str | None = None
    exercise_name: str | None = None  # joined for display, not persisted

    def __post_init__(self) -> None:
        if self.unit not in VALID_UNITS:
            raise ValueError(f"unit must be one of {VALID_UNITS}")
        if self.rpe is not None and not (0 <= self.rpe <= 10):
            raise ValueError("rpe must be between 0 and 10")
        for field_name in ("planned_reps", "actual_reps"):
            v = getattr(self, field_name)
            if v is not None and v < 0:
                raise ValueError(f"{field_name} must be >= 0")
        for field_name in ("planned_weight", "actual_weight"):
            v = getattr(self, field_name)
            if v is not None and v < 0:
                raise ValueError(f"{field_name} must be >= 0")

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["executed"] = bool(self.executed)
        return d


@dataclass
class Workout:
    date: str
    id: int | None = None
    title: str | None = None
    notes: str | None = None
    status: str = "planned"
    created_at: str | None = None
    updated_at: str | None = None
    sets: list[WorkoutSet] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise ValueError(f"status must be one of {VALID_STATUSES}")
        # Validate ISO date format
        try:
            date_t.fromisoformat(self.date)
        except ValueError as e:
            raise ValueError(f"date must be ISO YYYY-MM-DD: {self.date}") from e

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["sets"] = [s.to_dict() for s in self.sets]
        return d
