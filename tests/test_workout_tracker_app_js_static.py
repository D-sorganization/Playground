"""Static checks for browser-only workout tracker behavior."""

from __future__ import annotations

from pathlib import Path

APP_JS = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "workout_tracker"
    / "static"
    / "app.js"
)


def test_recall_cache_key_includes_active_workout_context() -> None:
    source = APP_JS.read_text(encoding="utf-8")

    assert "function recallCacheKey(name)" in source
    assert "state.activeWorkoutId ? String(state.activeWorkoutId) : \"none\"" in source
    assert "_recallCache.set(key, payload)" in source
    assert "key.endsWith(suffix)" in source
