"""Run the pure-logic JS in `static/lib.js` via Node and assert behaviour.

Guards the plate-math / voice-parser / step-weight helpers that back the
in-gym UX features. Browser-API features (Wake Lock, SpeechRecognition) are
smoke-tested manually against a dev server.

All checks run inside a single Node process to keep runtime tight on slow
sandboxes — the Node cold-start is ~1s which would otherwise dominate.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path
from typing import Any

import pytest

LIB = (
    Path(__file__).resolve().parents[1]
    / "src"
    / "workout_tracker"
    / "static"
    / "lib.js"
)

# Each item is (name, JS expression). We pack them all into one node invocation
# and assert on the result map.
CHECKS: list[tuple[str, str]] = [
    # ---- plate calculator ----
    ("plates_225_45_bar", "lib.platesFor(225, 45, lib.DEFAULT_PLATES_LBS)"),
    ("plates_315_45_bar", "lib.platesFor(315, 45)"),
    ("plates_below_bar", "lib.platesFor(30, 45)"),
    ("plates_185_45_bar", "lib.platesFor(185, 45)"),
    ("plates_46_45_bar", "lib.platesFor(46, 45)"),
    ("plates_kg_225_20_bar", "lib.platesFor(225, 20, lib.DEFAULT_PLATES_KG)"),
    (
        "plates_kg_total",
        "(() => { const r = lib.platesFor(225, 20, lib.DEFAULT_PLATES_KG); "
        "return r.perSide.reduce((s,p)=>s+p.plate*p.count,0)*2 + 20; })()",
    ),
    ("fmt_plates_225", "lib.formatPlates(lib.platesFor(225, 45))"),
    ("fmt_plates_bar_only", "lib.formatPlates(lib.platesFor(45, 45))"),
    # ---- step weight ----
    ("step_135_plus_5", "lib.stepWeight(135, 5)"),
    ("step_135_minus_2_5", "lib.stepWeight(135, -2.5)"),
    ("step_clamp_zero", "lib.stepWeight(2.5, -10)"),
    ("step_null_current", "lib.stepWeight(null, 5)"),
    ("step_snap_float", "lib.stepWeight(0.1, 0.2)"),
    # ---- voice parser ----
    ("voice_bench_5_by_135", "lib.parseVoiceCommand('bench 5 by 135')"),
    ("voice_squat_words", "lib.parseVoiceCommand('squat five by 225')"),
    ("voice_deadlift_3x405", "lib.parseVoiceCommand('deadlift 3x405')"),
    (
        "voice_overhead_reps_at",
        "lib.parseVoiceCommand('overhead press 8 reps at 95 lbs')",
    ),
    ("voice_front_squat_kg", "lib.parseVoiceCommand('front squat 5 by 100 kg')"),
    ("voice_gibberish", "lib.parseVoiceCommand('hello world')"),
    ("voice_empty", "lib.parseVoiceCommand('')"),
    # ---- mm:ss formatting ----
    ("mmss_0", "lib.fmtMMSS(0)"),
    ("mmss_59", "lib.fmtMMSS(59)"),
    ("mmss_60", "lib.fmtMMSS(60)"),
    ("mmss_125", "lib.fmtMMSS(125)"),
    ("mmss_negative", "lib.fmtMMSS(-5)"),
    ("mmss_fractional", "lib.fmtMMSS(90.7)"),
    # ---- recall formatting ----
    (
        "recall_basic",
        "lib.formatRecall("
        "[{reps:5,weight:135},{reps:5,weight:145},{reps:5,weight:155}])",
    ),
    ("recall_empty", "lib.formatRecall([])"),
    (
        "recall_actual_fields",
        "lib.formatRecall("
        "[{actual_reps:5,actual_weight:135},{actual_reps:8,actual_weight:95}])",
    ),
]


@pytest.fixture(scope="module")
def results() -> dict[str, Any]:
    node = shutil.which("node")
    if node is None:
        pytest.skip("node not installed — install Node.js to run lib.js tests")
    script_parts = [f"const lib = require({json.dumps(str(LIB))});", "const out = {};"]
    for name, expr in CHECKS:
        script_parts.append(f"out[{json.dumps(name)}] = {expr};")
    script_parts.append("process.stdout.write(JSON.stringify(out));")
    script = "\n".join(script_parts)
    proc = subprocess.run(
        [node, "-e", script],
        capture_output=True,
        text=True,
        timeout=30,
        check=True,
    )
    return json.loads(proc.stdout)


def test_plates_225_on_45_bar_lbs(results: dict[str, Any]) -> None:
    r = results["plates_225_45_bar"]
    assert r["perSide"] == [{"plate": 45, "count": 2}]
    assert r["leftover"] == 0
    assert r["achievable"] == 225


def test_plates_315_on_45_bar(results: dict[str, Any]) -> None:
    r = results["plates_315_45_bar"]
    assert r["perSide"] == [{"plate": 45, "count": 3}]
    assert r["achievable"] == 315


def test_plates_below_bar(results: dict[str, Any]) -> None:
    r = results["plates_below_bar"]
    assert r["perSide"] == []
    assert r.get("warning") == "below_bar"
    assert r["achievable"] == 45


def test_plates_mixed(results: dict[str, Any]) -> None:
    r = results["plates_185_45_bar"]
    side = {p["plate"]: p["count"] for p in r["perSide"]}
    assert side == {45: 1, 25: 1}
    assert r["achievable"] == 185


def test_plates_leftover(results: dict[str, Any]) -> None:
    r = results["plates_46_45_bar"]
    assert r["perSide"] == []
    assert r["leftover"] == 1  # 0.5 per side × 2


def test_plates_kg_valid(results: dict[str, Any]) -> None:
    assert results["plates_kg_total"] == 225


def test_format_plates_readable(results: dict[str, Any]) -> None:
    assert results["fmt_plates_225"] == "2×45 per side"


def test_format_plates_bar_only(results: dict[str, Any]) -> None:
    assert results["fmt_plates_bar_only"] == "Just the bar"


def test_step_plus_5(results: dict[str, Any]) -> None:
    assert results["step_135_plus_5"] == 140


def test_step_minus_2_5(results: dict[str, Any]) -> None:
    assert results["step_135_minus_2_5"] == 132.5


def test_step_clamp(results: dict[str, Any]) -> None:
    assert results["step_clamp_zero"] == 0


def test_step_null(results: dict[str, Any]) -> None:
    assert results["step_null_current"] == 5


def test_step_snap(results: dict[str, Any]) -> None:
    assert results["step_snap_float"] == 0.25


def test_voice_bench(results: dict[str, Any]) -> None:
    assert results["voice_bench_5_by_135"] == {
        "exercise": "Bench",
        "reps": 5,
        "weight": 135,
        "unit": None,
    }


def test_voice_words(results: dict[str, Any]) -> None:
    assert results["voice_squat_words"] == {
        "exercise": "Squat",
        "reps": 5,
        "weight": 225,
        "unit": None,
    }


def test_voice_3x405(results: dict[str, Any]) -> None:
    assert results["voice_deadlift_3x405"] == {
        "exercise": "Deadlift",
        "reps": 3,
        "weight": 405,
        "unit": None,
    }


def test_voice_multiword(results: dict[str, Any]) -> None:
    assert results["voice_overhead_reps_at"] == {
        "exercise": "Overhead Press",
        "reps": 8,
        "weight": 95,
        "unit": "lbs",
    }


def test_voice_kg(results: dict[str, Any]) -> None:
    assert results["voice_front_squat_kg"] == {
        "exercise": "Front Squat",
        "reps": 5,
        "weight": 100,
        "unit": "kg",
    }


def test_voice_gibberish_none(results: dict[str, Any]) -> None:
    assert results["voice_gibberish"] is None


def test_voice_empty_none(results: dict[str, Any]) -> None:
    assert results["voice_empty"] is None


def test_mmss_zero(results: dict[str, Any]) -> None:
    assert results["mmss_0"] == "00:00"


def test_mmss_59(results: dict[str, Any]) -> None:
    assert results["mmss_59"] == "00:59"


def test_mmss_60(results: dict[str, Any]) -> None:
    assert results["mmss_60"] == "01:00"


def test_mmss_125(results: dict[str, Any]) -> None:
    assert results["mmss_125"] == "02:05"


def test_mmss_negative(results: dict[str, Any]) -> None:
    assert results["mmss_negative"] == "00:00"


def test_mmss_fractional(results: dict[str, Any]) -> None:
    # 90.7 → floor → 90 → 01:30
    assert results["mmss_fractional"] == "01:30"


def test_recall_basic(results: dict[str, Any]) -> None:
    assert results["recall_basic"] == "5×135, 5×145, 5×155"


def test_recall_empty(results: dict[str, Any]) -> None:
    assert results["recall_empty"] == ""


def test_recall_actual_fields(results: dict[str, Any]) -> None:
    assert results["recall_actual_fields"] == "5×135, 8×95"
