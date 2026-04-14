"""Tests for Project_GROOT.tools.video_ingest - decomposed helpers."""

import argparse
import json

import pytest

import src.Project_GROOT.tools.video_ingest as target_module
from src.Project_GROOT.tools.video_ingest import (
    VideoIngester,
    _build_ingest_parser,
    _ingest_from_args,
    _load_existing_manifest,
)


def test_module_syntax_and_import():
    """Verify Project_GROOT.tools.video_ingest can be imported."""
    assert target_module is not None


def test_has_symbol_VideoIngester():
    """Verify VideoIngester exists in module."""
    assert hasattr(target_module, "VideoIngester")


def test_has_symbol_main():
    """Verify main exists in module."""
    assert hasattr(target_module, "main")


# --- _build_ingest_parser tests ---


def test_build_ingest_parser_returns_parser():
    """_build_ingest_parser should return a working ArgumentParser."""
    parser = _build_ingest_parser()
    assert isinstance(parser, argparse.ArgumentParser)


def test_build_ingest_parser_requires_input():
    """Parsing without --input-file or --input-dir should fail."""
    parser = _build_ingest_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_build_ingest_parser_input_file(tmp_path):
    """--input-file argument should be accepted."""
    parser = _build_ingest_parser()
    args = parser.parse_args(["--input-file", "swing.mp4"])
    assert args.input_file == "swing.mp4"
    assert args.input_dir is None


def test_build_ingest_parser_input_dir(tmp_path):
    """--input-dir argument should be accepted."""
    parser = _build_ingest_parser()
    args = parser.parse_args(["--input-dir", str(tmp_path)])
    assert args.input_dir == str(tmp_path)
    assert args.input_file is None


def test_build_ingest_parser_defaults():
    """Default values for optional args."""
    parser = _build_ingest_parser()
    args = parser.parse_args(["--input-file", "v.mp4"])
    assert args.output == "data/manifest.json"
    assert args.golfer_name == "Unknown"
    assert args.swing_type == "driver"
    assert args.recursive is False
    assert args.append is False


def test_build_ingest_parser_mutually_exclusive():
    """--input-file and --input-dir are mutually exclusive."""
    parser = _build_ingest_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(["--input-file", "v.mp4", "--input-dir", "."])


# --- _load_existing_manifest tests ---


def test_load_existing_manifest_loads_videos(tmp_path):
    """_load_existing_manifest loads videos from an existing JSON file."""
    manifest_path = tmp_path / "manifest.json"
    existing = {
        "version": "1.0",
        "num_videos": 2,
        "videos": [{"id": "a"}, {"id": "b"}],
    }
    manifest_path.write_text(json.dumps(existing))

    ingester = VideoIngester.__new__(VideoIngester)
    ingester.videos = []
    ingester.output_path = manifest_path

    _load_existing_manifest(ingester, str(manifest_path))
    assert len(ingester.videos) == 2
    assert ingester.videos[0]["id"] == "a"


def test_load_existing_manifest_no_file(tmp_path):
    """_load_existing_manifest does nothing when file does not exist."""
    ingester = VideoIngester.__new__(VideoIngester)
    ingester.videos = []

    _load_existing_manifest(ingester, str(tmp_path / "nonexistent.json"))
    assert ingester.videos == []


# --- _ingest_from_args tests ---


def test_ingest_from_args_missing_file_raises(tmp_path):
    """_ingest_from_args raises FileNotFoundError for a missing --input-file."""
    ingester = VideoIngester(str(tmp_path / "manifest.json"))
    args = argparse.Namespace(
        input_file=str(tmp_path / "missing.mp4"),
        input_dir=None,
        golfer_name="Test",
        video_source="local",
        start_time=None,
        end_time=None,
        swing_type="driver",
        recursive=False,
    )
    with pytest.raises(FileNotFoundError):
        _ingest_from_args(ingester, args)


def test_ingest_from_args_missing_dir_raises(tmp_path):
    """_ingest_from_args raises FileNotFoundError for a missing --input-dir."""
    ingester = VideoIngester(str(tmp_path / "manifest.json"))
    args = argparse.Namespace(
        input_file=None,
        input_dir=str(tmp_path / "no_such_dir"),
        golfer_name="Test",
        video_source="local",
        start_time=None,
        end_time=None,
        swing_type="driver",
        recursive=False,
    )
    with pytest.raises(FileNotFoundError):
        _ingest_from_args(ingester, args)


def test_ingest_from_args_empty_dir_adds_nothing(tmp_path):
    """_ingest_from_args with an empty directory leaves manifest empty."""
    ingester = VideoIngester(str(tmp_path / "manifest.json"))
    args = argparse.Namespace(
        input_file=None,
        input_dir=str(tmp_path),
        golfer_name="Test",
        video_source="local",
        start_time=None,
        end_time=None,
        swing_type="driver",
        recursive=False,
    )
    _ingest_from_args(ingester, args)
    assert len(ingester.videos) == 0


# --- VideoIngester contract tests ---


def test_add_video_negative_start_time_raises(tmp_path):
    """add_video with negative start_time raises AssertionError."""
    video = tmp_path / "v.mp4"
    video.write_bytes(b"fake")
    ingester = VideoIngester(str(tmp_path / "manifest.json"))
    with pytest.raises(AssertionError, match="start_time"):
        ingester.add_video(str(video), start_time=-1.0)


def test_add_video_end_before_start_raises(tmp_path):
    """add_video with end_time <= start_time raises AssertionError."""
    video = tmp_path / "v.mp4"
    video.write_bytes(b"fake")
    ingester = VideoIngester(str(tmp_path / "manifest.json"))
    with pytest.raises(AssertionError):
        ingester.add_video(str(video), start_time=2.0, end_time=1.0)
