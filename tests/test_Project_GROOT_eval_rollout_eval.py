"""Tests for Project_GROOT.eval.rollout_eval - decomposed helpers."""

import pytest

pytest.importorskip("torch")

import src.Project_GROOT.eval.rollout_eval as target_module
from src.Project_GROOT.eval.rollout_eval import (
    PolicyEvaluator,
    _build_arg_parser,
    _build_report_html,
)


def _sample_summary() -> dict:
    return {
        "num_rollouts": 5,
        "clubhead_speed": {
            "max_mean": 39.2,
            "max_std": 2.0,
            "max_min": 35.0,
            "max_max": 43.0,
        },
        "swing_duration": {"mean": 1.42, "std": 0.08},
        "trajectory_smoothness": {"mean": 0.88, "std": 0.04},
        "joint_limit_violations": {"mean": 0.2, "total": 1, "percentage": 20.0},
    }


def test_module_syntax_and_import():
    """Verify Project_GROOT.eval.rollout_eval can be imported."""
    assert target_module is not None


def test_has_symbol_PolicyEvaluator():
    """Verify PolicyEvaluator exists in module."""
    assert hasattr(target_module, "PolicyEvaluator")


def test_has_symbol_main():
    """Verify main exists in module."""
    assert hasattr(target_module, "main")


# --- _build_report_html tests ---


def test_build_report_html_contains_policy_name():
    """Report HTML should include the policy filename."""
    html = _build_report_html("my_policy.pth", _sample_summary())
    assert "my_policy.pth" in html


def test_build_report_html_contains_speed():
    """Report HTML should include the mean speed value."""
    html = _build_report_html("p.pth", _sample_summary())
    assert "39.20 m/s" in html


def test_build_report_html_contains_rollout_count():
    """Report HTML should include rollout count."""
    html = _build_report_html("p.pth", _sample_summary())
    assert "5" in html


def test_build_report_html_is_valid_html():
    """Report HTML should start with DOCTYPE."""
    html = _build_report_html("p.pth", _sample_summary())
    assert html.strip().startswith("<!DOCTYPE html>")


# --- _build_arg_parser tests ---


def test_build_arg_parser_returns_parser():
    """_build_arg_parser should return a working ArgumentParser."""
    import argparse

    parser = _build_arg_parser()
    assert isinstance(parser, argparse.ArgumentParser)


def test_build_arg_parser_required_args():
    """Parsing without required args should fail."""

    parser = _build_arg_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_build_arg_parser_parses_valid_args(tmp_path):
    """Valid args should parse successfully."""
    parser = _build_arg_parser()
    args = parser.parse_args(
        [
            "--policy",
            "p.pth",
            "--config",
            "c.yaml",
            "--output-dir",
            str(tmp_path),
        ]
    )
    assert args.policy == "p.pth"
    assert args.num_rollouts == 50  # default


# --- compute_summary_metrics tests ---


def test_compute_summary_metrics_structure(tmp_path):
    """compute_summary_metrics returns expected keys."""
    import yaml

    config_path = tmp_path / "config.yaml"
    config_path.write_text(yaml.dump({"dummy": True}))
    evaluator = PolicyEvaluator(
        policy_path="dummy.pth",
        config_path=str(config_path),
        output_dir=str(tmp_path),
        device="cpu",
    )
    rollout_stats = [
        {
            "rollout_id": i,
            "max_clubhead_speed": 39.0 + i,
            "swing_duration": 1.4,
            "trajectory_smoothness": 0.9,
            "joint_limit_violations": 0,
        }
        for i in range(3)
    ]
    summary = evaluator.compute_summary_metrics(rollout_stats)
    assert "clubhead_speed" in summary
    assert "swing_duration" in summary
    assert summary["num_rollouts"] == 3
