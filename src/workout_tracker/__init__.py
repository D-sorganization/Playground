"""Workout tracker - quick logging, planning, and stats for gym sessions.

`create_app` is exported lazily so that importing pure-Python modules (models,
parser, autocomplete, stats) does not require Flask to be installed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = ["create_app"]

if TYPE_CHECKING:
    from workout_tracker.app import create_app as create_app  # noqa: F401


def __getattr__(name: str) -> Any:
    if name == "create_app":
        from workout_tracker.app import create_app

        return create_app
    raise AttributeError(f"module 'workout_tracker' has no attribute {name!r}")
