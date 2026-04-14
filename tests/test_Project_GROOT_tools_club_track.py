"""Tests for Project_GROOT.tools.club_track - decomposed helpers."""

import json

import numpy as np
import pytest

import src.Project_GROOT.tools.club_track as target_module
from src.Project_GROOT.tools.club_track import (
    ClubTracker,
    _build_club_track_parser,
    _save_and_summarize,
)


def test_module_syntax_and_import():
    """Verify Project_GROOT.tools.club_track can be successfully imported and parsed."""
    assert target_module is not None


def test_has_symbol_ClubTracker():
    """Verify ClubTracker exists in module."""
    assert hasattr(target_module, "ClubTracker")


def test_has_symbol_main():
    """Verify main exists in module."""
    assert hasattr(target_module, "main")


def test_has_symbol_visualize_club_stats():
    """Verify visualize_club_stats exists in module."""
    assert hasattr(target_module, "visualize_club_stats")


# --- _build_club_track_parser tests ---


def test_build_club_track_parser_returns_parser():
    """Parser factory returns a working ArgumentParser."""
    import argparse

    parser = _build_club_track_parser()
    assert isinstance(parser, argparse.ArgumentParser)


def test_build_club_track_parser_required_args():
    """Parsing without required args should fail."""
    with pytest.raises(SystemExit):
        _build_club_track_parser().parse_args([])


def test_build_club_track_parser_defaults():
    """Default values are set correctly."""
    args = _build_club_track_parser().parse_args(
        [
            "--manifest",
            "m.json",
            "--pose-dir",
            ".",
            "--output-dir",
            ".",
        ]
    )
    assert args.method == "line_fit"
    assert args.club_length == pytest.approx(1.15)
    assert args.visualize is False


# --- _save_and_summarize tests ---


def test_save_and_summarize_creates_json(tmp_path):
    """_save_and_summarize writes a JSON file to output_dir."""
    stats = [
        {
            "video_id": "v1",
            "golfer": "A",
            "max_clubhead_speed": 38.0,
            "avg_clubhead_speed": 20.0,
            "total_path_length": 5.0,
        },
    ]
    _save_and_summarize(stats, tmp_path)
    out = tmp_path / "club_tracking_stats.json"
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["videos"][0]["video_id"] == "v1"


def test_save_and_summarize_empty_stats(tmp_path):
    """Empty stats list creates an empty JSON without crashing."""
    _save_and_summarize([], tmp_path)
    out = tmp_path / "club_tracking_stats.json"
    assert out.exists()
    data = json.loads(out.read_text())
    assert data["videos"] == []


# --- ClubTracker._track_line_fit tests ---


def _make_skeleton(n_frames: int = 5) -> tuple[np.ndarray, np.ndarray]:
    """Create a simple synthetic skeleton for testing."""
    skeleton = np.zeros((n_frames, 33, 3))
    skeleton[:, 15] = [[0.1, 0.5, 0.0]] * n_frames  # left wrist
    skeleton[:, 16] = [[0.9, 0.5, 0.0]] * n_frames  # right wrist
    confidence = np.ones((n_frames, 33)) * 0.9
    return skeleton, confidence


def test_club_tracker_line_fit_shapes():
    """_track_line_fit returns arrays with correct shapes."""
    tracker = ClubTracker(method="line_fit", club_length=1.15)
    skeleton, confidence = _make_skeleton(10)
    grip, head, face = tracker._track_line_fit(skeleton, confidence)
    assert grip.shape == (10, 3)
    assert head.shape == (10, 3)
    assert face.shape == (10, 3)


def test_club_tracker_line_fit_empty_raises():
    """_track_line_fit raises ValueError on empty skeleton."""
    tracker = ClubTracker()
    with pytest.raises(ValueError, match="frames"):
        tracker._track_line_fit(np.zeros((0, 33, 3)), np.zeros((0, 33)))
