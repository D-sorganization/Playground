"""Statistical analytics over executed workout sets.

Pure functions: take a list of WorkoutSet (with completed_at populated) and
produce dashboards. Trends, PRs, volume, 1RM estimates, frequency, density.
"""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from datetime import datetime
from statistics import mean
from typing import Any

from workout_tracker.models import WorkoutSet


def epley_1rm(weight: float, reps: int) -> float:
    """Epley estimated one-rep max. weight*(1 + reps/30). Reps>=1."""
    if reps <= 0 or weight < 0:
        raise ValueError("reps must be > 0 and weight >= 0")
    if reps == 1:
        return weight
    return weight * (1 + reps / 30)


def brzycki_1rm(weight: float, reps: int) -> float:
    """Brzycki estimated 1RM, more accurate at low reps."""
    if reps <= 0 or weight < 0:
        raise ValueError("reps must be > 0 and weight >= 0")
    if reps >= 37:
        raise ValueError("brzycki diverges at reps>=37")
    return weight * 36 / (37 - reps)


def best_1rm_estimate(weight: float, reps: int) -> float:
    """Average Epley + Brzycki when feasible; fall back to Epley."""
    try:
        return (epley_1rm(weight, reps) + brzycki_1rm(weight, reps)) / 2
    except ValueError:
        return epley_1rm(weight, reps)


def set_volume(s: WorkoutSet) -> float:
    if not s.executed:
        return 0.0
    w = s.actual_weight if s.actual_weight is not None else 0.0
    r = s.actual_reps if s.actual_reps is not None else 0
    return float(w) * float(r)


def total_volume(sets: Iterable[WorkoutSet]) -> float:
    return sum(set_volume(s) for s in sets)


@dataclass
class ExerciseSummary:
    exercise_id: int
    exercise_name: str
    total_sets: int
    total_reps: int
    total_volume: float
    max_weight: float
    max_reps_at_max_weight: int
    best_e1rm: float
    last_performed: str | None
    avg_rpe: float | None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def per_exercise_summary(
    sets: Iterable[WorkoutSet],
) -> list[ExerciseSummary]:
    """Aggregate executed sets by exercise."""
    grouped: dict[int, list[WorkoutSet]] = defaultdict(list)
    for s in sets:
        if s.executed and s.actual_weight is not None and s.actual_reps:
            grouped[s.exercise_id].append(s)

    out: list[ExerciseSummary] = []
    for ex_id, ex_sets in grouped.items():
        max_w = max((s.actual_weight or 0.0) for s in ex_sets)
        # max reps at the single heaviest weight
        reps_at_max = max(
            (s.actual_reps or 0) for s in ex_sets if (s.actual_weight or 0.0) == max_w
        )
        best_e = max(
            best_1rm_estimate(s.actual_weight or 0.0, s.actual_reps or 0)
            for s in ex_sets
        )
        last = max((s.completed_at or "" for s in ex_sets), default=None) or None
        rpes = [s.rpe for s in ex_sets if s.rpe is not None]
        avg_rpe = mean(rpes) if rpes else None
        name = ex_sets[0].exercise_name or f"#{ex_id}"
        out.append(
            ExerciseSummary(
                exercise_id=ex_id,
                exercise_name=name,
                total_sets=len(ex_sets),
                total_reps=sum(s.actual_reps or 0 for s in ex_sets),
                total_volume=sum(set_volume(s) for s in ex_sets),
                max_weight=float(max_w),
                max_reps_at_max_weight=int(reps_at_max),
                best_e1rm=float(best_e),
                last_performed=last,
                avg_rpe=avg_rpe,
            )
        )
    out.sort(key=lambda s: -s.total_volume)
    return out


@dataclass
class TimePoint:
    date: str
    volume: float
    best_e1rm: float
    sets: int


def exercise_timeseries(sets: Iterable[WorkoutSet]) -> list[TimePoint]:
    """Per-day series of volume + best e1RM for one exercise's sets."""
    by_day: dict[str, list[WorkoutSet]] = defaultdict(list)
    for s in sets:
        if not s.executed or not s.completed_at:
            continue
        day = s.completed_at[:10]
        by_day[day].append(s)
    pts: list[TimePoint] = []
    for day in sorted(by_day):
        ds = by_day[day]
        vol = sum(set_volume(s) for s in ds)
        best = max(
            best_1rm_estimate(s.actual_weight or 0.0, s.actual_reps or 0) for s in ds
        )
        pts.append(TimePoint(date=day, volume=vol, best_e1rm=best, sets=len(ds)))
    return pts


@dataclass
class PRRecord:
    exercise_id: int
    exercise_name: str
    metric: str  # "max_weight" | "max_reps" | "best_e1rm"
    value: float
    reps: int
    weight: float
    date: str


def personal_records(sets: Iterable[WorkoutSet]) -> list[PRRecord]:
    """Find the all-time PR for each exercise on three axes."""
    grouped: dict[int, list[WorkoutSet]] = defaultdict(list)
    for s in sets:
        if (
            s.executed
            and s.actual_weight is not None
            and s.actual_reps
            and s.completed_at
        ):
            grouped[s.exercise_id].append(s)

    prs: list[PRRecord] = []
    for ex_id, items in grouped.items():
        name = items[0].exercise_name or f"#{ex_id}"

        top_w = max(items, key=lambda s: s.actual_weight or 0.0)
        prs.append(
            PRRecord(
                exercise_id=ex_id,
                exercise_name=name,
                metric="max_weight",
                value=float(top_w.actual_weight or 0.0),
                reps=int(top_w.actual_reps or 0),
                weight=float(top_w.actual_weight or 0.0),
                date=(top_w.completed_at or "")[:10],
            )
        )

        top_r = max(items, key=lambda s: s.actual_reps or 0)
        prs.append(
            PRRecord(
                exercise_id=ex_id,
                exercise_name=name,
                metric="max_reps",
                value=float(top_r.actual_reps or 0),
                reps=int(top_r.actual_reps or 0),
                weight=float(top_r.actual_weight or 0.0),
                date=(top_r.completed_at or "")[:10],
            )
        )

        top_e = max(
            items,
            key=lambda s: best_1rm_estimate(s.actual_weight or 0.0, s.actual_reps or 0),
        )
        prs.append(
            PRRecord(
                exercise_id=ex_id,
                exercise_name=name,
                metric="best_e1rm",
                value=best_1rm_estimate(
                    top_e.actual_weight or 0.0, top_e.actual_reps or 0
                ),
                reps=int(top_e.actual_reps or 0),
                weight=float(top_e.actual_weight or 0.0),
                date=(top_e.completed_at or "")[:10],
            )
        )
    return prs


@dataclass
class FrequencyStat:
    exercise_id: int
    exercise_name: str
    sessions: int
    days_since_last: int | None


def frequency(
    sets: Iterable[WorkoutSet], today: str | None = None
) -> list[FrequencyStat]:
    """Per-exercise: distinct training days, days since last performed."""
    today_d = (
        datetime.fromisoformat(today).date() if today else datetime.utcnow().date()
    )
    grouped: dict[int, list[WorkoutSet]] = defaultdict(list)
    for s in sets:
        if s.executed and s.completed_at:
            grouped[s.exercise_id].append(s)
    out: list[FrequencyStat] = []
    for ex_id, items in grouped.items():
        days = sorted({s.completed_at[:10] for s in items if s.completed_at})
        if not days:
            continue
        last = days[-1]
        delta = (today_d - datetime.fromisoformat(last).date()).days
        name = items[0].exercise_name or f"#{ex_id}"
        out.append(
            FrequencyStat(
                exercise_id=ex_id,
                exercise_name=name,
                sessions=len(days),
                days_since_last=delta,
            )
        )
    out.sort(key=lambda f: -f.sessions)
    return out


@dataclass
class Overview:
    total_workouts: int
    total_sets: int
    total_volume: float
    distinct_exercises: int
    last_workout_date: str | None


def overview(sets: Iterable[WorkoutSet]) -> Overview:
    sets = list(sets)
    executed = [s for s in sets if s.executed]
    workout_ids = {s.workout_id for s in executed}
    exercise_ids = {s.exercise_id for s in executed}
    last = max((s.completed_at or "" for s in executed), default=None) or None
    return Overview(
        total_workouts=len(workout_ids),
        total_sets=len(executed),
        total_volume=total_volume(executed),
        distinct_exercises=len(exercise_ids),
        last_workout_date=last[:10] if last else None,
    )
