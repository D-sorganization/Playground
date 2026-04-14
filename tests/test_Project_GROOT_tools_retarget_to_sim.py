"""Tests for Project_GROOT.tools.retarget_to_sim - decomposed helpers."""

import argparse
import json

import numpy as np
import pytest

import src.Project_GROOT.tools.retarget_to_sim as target_module
from src.Project_GROOT.tools.retarget_to_sim import (
    _build_retarget_parser,
    _save_retarget_report,
    validate_trajectory,
)


def test_module_syntax_and_import():
    """Verify Project_GROOT.tools.retarget_to_sim can be imported."""
    assert target_module is not None


def test_has_symbol_RobotConfig():
    """Verify RobotConfig exists in module."""
    assert hasattr(target_module, "RobotConfig")


def test_has_symbol_PoseRetargeter():
    """Verify PoseRetargeter exists in module."""
    assert hasattr(target_module, "PoseRetargeter")


def test_has_symbol_validate_trajectory():
    """Verify validate_trajectory exists in module."""
    assert hasattr(target_module, "validate_trajectory")


def test_has_symbol_main():
    """Verify main exists in module."""
    assert hasattr(target_module, "main")


# --- _build_retarget_parser tests ---


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


# --- _save_retarget_report tests ---


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


# --- validate_trajectory tests ---


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
