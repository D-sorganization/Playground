"""Tests for Project_GROOT.tools.retarget_to_sim - DbC contracts and behavioral tests.

Issue #275: Add DbC validation and tests for Project_GROOT retargeting input shapes
and timestamp invariants.
"""

import argparse
import json

import numpy as np
import pytest

from src.Project_GROOT.tools.retarget_to_sim import (
    PoseRetargeter,
    _build_retarget_parser,
    _save_retarget_report,
    validate_trajectory,
)

# --- _build_retarget_parser behavioral tests ---


def test_build_retarget_parser_returns_parser():
    """_build_retarget_parser should return a working ArgumentParser."""
    parser = _build_retarget_parser()
    assert isinstance(parser, argparse.ArgumentParser)


def test_build_retarget_parser_requires_args():
    """Parsing without required args should fail."""
    parser = _build_retarget_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_build_retarget_parser_parses_valid_args(tmp_path):
    """Valid required args should parse successfully."""
    parser = _build_retarget_parser()
    args = parser.parse_args(
        [
            "--input-dir",
            str(tmp_path),
            "--output-dir",
            str(tmp_path),
            "--robot-config",
            "cfg.yaml",
        ]
    )
    assert args.input_dir == str(tmp_path)
    assert args.smooth_window == 5  # default
    assert args.ik_solver == "trac_ik"  # default
    assert args.visualize is False


def test_build_retarget_parser_ik_solver_choices():
    """Invalid ik_solver choice should fail."""
    parser = _build_retarget_parser()
    with pytest.raises(SystemExit):
        parser.parse_args(
            [
                "--input-dir",
                ".",
                "--output-dir",
                ".",
                "--robot-config",
                "c.yaml",
                "--ik-solver",
                "invalid_solver",
            ]
        )


# --- _save_retarget_report behavioral tests ---


def test_save_retarget_report_creates_file(tmp_path):
    """_save_retarget_report writes retargeting_report.json."""
    reports = [
        {"file": "a.npz", "valid": True, "warnings": [], "errors": []},
        {"file": "b.npz", "valid": False, "warnings": [], "errors": ["limit"]},
    ]
    _save_retarget_report(reports, tmp_path)
    report_file = tmp_path / "retargeting_report.json"
    assert report_file.exists()


def test_save_retarget_report_content(tmp_path):
    """_save_retarget_report JSON contains the demos list."""
    reports = [{"file": "x.npz", "valid": True, "warnings": [], "errors": []}]
    _save_retarget_report(reports, tmp_path)
    with open(tmp_path / "retargeting_report.json") as f:
        data = json.load(f)
    assert "demos" in data
    assert data["demos"][0]["file"] == "x.npz"


def test_save_retarget_report_empty(tmp_path):
    """_save_retarget_report handles an empty reports list."""
    _save_retarget_report([], tmp_path)
    with open(tmp_path / "retargeting_report.json") as f:
        data = json.load(f)
    assert data["demos"] == []


# --- validate_trajectory behavioral tests ---


def _make_robot_config_stub():
    """Create a minimal RobotConfig-like stub without yaml."""
    from types import SimpleNamespace

    cfg = SimpleNamespace()
    cfg.dof_names = ["dof_0", "dof_1", "dof_2"]
    cfg.num_dofs = 3
    cfg.joint_lower = np.array([-1.0, -1.0, -1.0])
    cfg.joint_upper = np.array([1.0, 1.0, 1.0])
    cfg.velocity_limits = np.array([10.0, 10.0, 10.0])
    cfg.acceleration_limits = np.array([50.0, 50.0, 50.0])
    return cfg


def test_validate_trajectory_valid():
    """validate_trajectory returns valid=True for a well-behaved trajectory."""
    cfg = _make_robot_config_stub()
    T = 10
    q = np.zeros((T, 3))
    qdot = np.zeros((T, 3))
    report = validate_trajectory(q, qdot, cfg)
    assert report["valid"] is True
    assert report["errors"] == []


def test_validate_trajectory_joint_limit_violation():
    """validate_trajectory flags joint limit violations."""
    cfg = _make_robot_config_stub()
    T = 5
    q = np.ones((T, 3)) * 2.0  # exceeds upper limit of 1.0
    qdot = np.zeros((T, 3))
    report = validate_trajectory(q, qdot, cfg)
    assert report["valid"] is False
    assert len(report["errors"]) > 0


def test_validate_trajectory_velocity_warning():
    """validate_trajectory warns when velocity exceeds limits."""
    cfg = _make_robot_config_stub()
    T = 10
    q = np.zeros((T, 3))
    qdot = np.ones((T, 3)) * 20.0  # exceeds velocity_limits of 10.0
    report = validate_trajectory(q, qdot, cfg)
    assert len(report["warnings"]) > 0


# --- PoseRetargeter helpers ---


def _make_retargeter_stub():
    """Build a PoseRetargeter with a stub RobotConfig (no YAML needed)."""
    from types import SimpleNamespace

    cfg = SimpleNamespace()
    cfg.num_dofs = 11
    cfg.dof_names = [f"dof_{i}" for i in range(11)]
    cfg.joint_lower = np.full(11, -np.pi)
    cfg.joint_upper = np.full(11, np.pi)
    cfg.velocity_limits = np.full(11, 10.0)
    cfg.acceleration_limits = np.full(11, 50.0)

    retargeter = PoseRetargeter.__new__(PoseRetargeter)
    retargeter.robot_config = cfg
    retargeter.ik_solver = "simple"
    retargeter.smooth_window = 0  # disable smoothing (no scipy required)
    return retargeter


def _make_minimal_inputs(T: int = 10, num_joints: int = 33):
    """Return (skeleton, club_head, timestamps) with monotonic timestamps."""
    rng = np.random.default_rng(42)
    skeleton = rng.standard_normal((T, num_joints, 3))
    club_head = rng.standard_normal((T, 3))
    timestamps = np.linspace(0.0, 1.0, T)
    return skeleton, club_head, timestamps


# --- PoseRetargeter.retarget() behavioral tests (issue #275) ---


def test_retarget_returns_expected_keys():
    """retarget() output dict contains q, qdot, qddot, ee_pos, dof_names."""
    retargeter = _make_retargeter_stub()
    skeleton, club_head, timestamps = _make_minimal_inputs()
    result = retargeter.retarget(skeleton, club_head, timestamps)
    for key in ("q", "qdot", "qddot", "ee_pos", "dof_names"):
        assert key in result, f"missing key '{key}'"


def test_retarget_output_shapes():
    """retarget() output arrays have the right shapes."""
    T = 10
    retargeter = _make_retargeter_stub()
    num_dofs = retargeter.robot_config.num_dofs
    skeleton, club_head, timestamps = _make_minimal_inputs(T=T)
    result = retargeter.retarget(skeleton, club_head, timestamps)
    assert result["q"].shape == (T, num_dofs)
    assert result["qdot"].shape == (T, num_dofs)
    assert result["qddot"].shape == (T, num_dofs)
    assert result["ee_pos"].shape == (T, 3)


def test_retarget_joint_limits_respected():
    """retarget() clips output q to robot joint limits."""
    retargeter = _make_retargeter_stub()
    skeleton, club_head, timestamps = _make_minimal_inputs()
    result = retargeter.retarget(skeleton, club_head, timestamps)
    cfg = retargeter.robot_config
    assert np.all(result["q"] >= cfg.joint_lower - 1e-9)
    assert np.all(result["q"] <= cfg.joint_upper + 1e-9)


def test_retarget_dof_names_match_config():
    """retarget() dof_names equals robot_config.dof_names."""
    retargeter = _make_retargeter_stub()
    skeleton, club_head, timestamps = _make_minimal_inputs()
    result = retargeter.retarget(skeleton, club_head, timestamps)
    assert result["dof_names"] == retargeter.robot_config.dof_names


# --- PoseRetargeter.retarget() DbC contract violation tests (issue #275) ---


def test_retarget_raises_on_2d_skeleton():
    """retarget() raises ValueError when skeleton is 2D instead of 3D."""
    retargeter = _make_retargeter_stub()
    T = 10
    bad_skeleton = np.zeros((T, 33))  # missing last dim
    club_head = np.zeros((T, 3))
    timestamps = np.linspace(0.0, 1.0, T)
    with pytest.raises(ValueError, match="skeleton must be"):
        retargeter.retarget(bad_skeleton, club_head, timestamps)


def test_retarget_raises_on_too_few_joints():
    """retarget() raises ValueError when skeleton has fewer than 17 joints."""
    retargeter = _make_retargeter_stub()
    T = 10
    bad_skeleton = np.zeros((T, 10, 3))  # only 10 joints
    club_head = np.zeros((T, 3))
    timestamps = np.linspace(0.0, 1.0, T)
    with pytest.raises(ValueError, match="at least 17 joints"):
        retargeter.retarget(bad_skeleton, club_head, timestamps)


def test_retarget_raises_on_too_few_frames():
    """retarget() raises ValueError when fewer than 3 frames are supplied."""
    retargeter = _make_retargeter_stub()
    skeleton = np.zeros((2, 33, 3))
    club_head = np.zeros((2, 3))
    timestamps = np.array([0.0, 1.0])
    with pytest.raises(ValueError, match="at least 3 frames"):
        retargeter.retarget(skeleton, club_head, timestamps)


def test_retarget_raises_on_mismatched_club_head():
    """retarget() raises ValueError when club_head length != skeleton length."""
    retargeter = _make_retargeter_stub()
    skeleton = np.zeros((10, 33, 3))
    club_head = np.zeros((8, 3))  # wrong length
    timestamps = np.linspace(0.0, 1.0, 10)
    with pytest.raises(ValueError, match="club_head length"):
        retargeter.retarget(skeleton, club_head, timestamps)


def test_retarget_raises_on_mismatched_timestamps():
    """retarget() raises ValueError when timestamps length != skeleton length."""
    retargeter = _make_retargeter_stub()
    skeleton = np.zeros((10, 33, 3))
    club_head = np.zeros((10, 3))
    timestamps = np.linspace(0.0, 1.0, 7)  # wrong length
    with pytest.raises(ValueError, match="timestamps length"):
        retargeter.retarget(skeleton, club_head, timestamps)


def test_retarget_raises_on_nan_timestamps():
    """retarget() raises ValueError when timestamps contain NaN."""
    retargeter = _make_retargeter_stub()
    T = 10
    skeleton = np.zeros((T, 33, 3))
    club_head = np.zeros((T, 3))
    timestamps = np.linspace(0.0, 1.0, T)
    timestamps[5] = float("nan")
    with pytest.raises(ValueError, match="finite"):
        retargeter.retarget(skeleton, club_head, timestamps)


def test_retarget_raises_on_non_monotonic_timestamps():
    """retarget() raises ValueError when timestamps are not monotonically increasing."""
    retargeter = _make_retargeter_stub()
    T = 10
    skeleton = np.zeros((T, 33, 3))
    club_head = np.zeros((T, 3))
    timestamps = np.linspace(1.0, 0.0, T)  # decreasing
    with pytest.raises(ValueError, match="monotonically increasing"):
        retargeter.retarget(skeleton, club_head, timestamps)
