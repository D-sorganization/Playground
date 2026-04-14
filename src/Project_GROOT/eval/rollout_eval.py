#!/usr/bin/env python3
"""
Rollout Evaluation Script for Project GROOT

Evaluates trained policies by running rollouts and computing performance metrics.

Metrics:
- Clubhead speed (max, mean)
- Swing duration
- Trajectory smoothness
- Joint limit violations

Usage:
    python eval/rollout_eval.py \\
        --policy train/outputs/imitation_policy/checkpoints/best.pth \\
        --config sim/configs/humanoid_upper.yaml --num-rollouts 50 \\
        --output-dir eval/outputs/eval_results
"""

import argparse
import json
import logging
from pathlib import Path

import numpy as np
import torch
import yaml

from src.Project_GROOT.eval.eval_plots import (
    plot_hist_with_mean,
    plot_line_with_mean,
    plot_scatter,
)
from src.Project_GROOT.eval.eval_report import build_report_html

logger = logging.getLogger(__name__)

# Re-export for backwards compatibility
_build_report_html = build_report_html


class PolicyEvaluator:
    """Evaluate trained policy through rollouts."""

    def __init__(
        self,
        policy_path: str,
        config_path: str,
        output_dir: str,
        device: str = "cuda",
    ):
        self.policy_path = Path(policy_path)
        self.config_path = Path(config_path)
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.device = device

        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        logger.info(f"Loaded policy: {policy_path}")
        logger.info(f"Output directory: {output_dir}")

    def run_rollouts(
        self, num_rollouts: int = 50, record_video: bool = False
    ) -> list[dict]:
        """Run multiple policy rollouts and collect metrics.

        Args:
            num_rollouts: Number of rollouts to execute
            record_video: Whether to record videos

        Returns:
            List of rollout statistics

        Raises:
            NotImplementedError: Until Isaac Lab integration is complete.
        """
        msg = f"Contract violation: num_rollouts must be positive, got {num_rollouts}"
        assert num_rollouts > 0, msg
        logger.info(f"\nRunning {num_rollouts} rollouts...")

        rollout_stats = []
        for i in range(num_rollouts):
            stats = self._generate_synthetic_rollout(i)
            rollout_stats.append(stats)
            if (i + 1) % 10 == 0:
                logger.info(f"  Completed {i + 1}/{num_rollouts} rollouts")
        return rollout_stats

    def _generate_synthetic_rollout(self, rollout_id: int) -> dict:
        """Generate rollout statistics by running the policy in the environment.

        NOT IMPLEMENTED: This method is a scaffold pending Isaac Lab integration.

        Raises:
            NotImplementedError: Always raised until Isaac Lab is integrated.
        """
        raise NotImplementedError(
            f"_generate_synthetic_rollout(rollout_id={rollout_id}) is not implemented. "
            "Real rollouts require an Isaac Lab environment. "
            "See Issue #249 for implementation requirements."
        )

    def compute_summary_metrics(self, rollout_stats: list[dict]) -> dict:
        """Compute summary statistics across all rollouts."""
        max_speeds = [s["max_clubhead_speed"] for s in rollout_stats]
        durations = [s["swing_duration"] for s in rollout_stats]
        smoothness = [s["trajectory_smoothness"] for s in rollout_stats]
        violations = [s["joint_limit_violations"] for s in rollout_stats]

        return {
            "num_rollouts": len(rollout_stats),
            "clubhead_speed": {
                "max_mean": float(np.mean(max_speeds)),
                "max_std": float(np.std(max_speeds)),
                "max_min": float(np.min(max_speeds)),
                "max_max": float(np.max(max_speeds)),
            },
            "swing_duration": {
                "mean": float(np.mean(durations)),
                "std": float(np.std(durations)),
            },
            "trajectory_smoothness": {
                "mean": float(np.mean(smoothness)),
                "std": float(np.std(smoothness)),
            },
            "joint_limit_violations": {
                "mean": float(np.mean(violations)),
                "total": int(np.sum(violations)),
                "percentage": 100.0 * float(np.mean([v > 0 for v in violations])),
            },
        }

    def save_results(self, rollout_stats: list[dict], summary: dict) -> None:
        """Save evaluation results to disk."""
        results_file = self.output_dir / "rollout_results.json"
        with open(results_file, "w") as f:
            json.dump(rollout_stats, f, indent=2)
        summary_file = self.output_dir / "summary.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)
        logger.info(f"\n Results saved: {results_file}")
        logger.info(f"  Summary: {summary_file}")

    def generate_plots(self, rollout_stats: list[dict]) -> None:
        """Generate evaluation plots."""
        plots_dir = self.output_dir / "plots"
        plots_dir.mkdir(exist_ok=True)

        max_speeds = [s["max_clubhead_speed"] for s in rollout_stats]
        durations = [s["swing_duration"] for s in rollout_stats]
        smoothness = [s["trajectory_smoothness"] for s in rollout_stats]

        plot_hist_with_mean(
            max_speeds,
            "Max Clubhead Speed (m/s)",
            "Frequency",
            "Clubhead Speed Distribution",
            ".1f",
            " m/s",
            "steelblue",
            plots_dir / "clubhead_speed_dist.png",
        )
        plot_hist_with_mean(
            durations,
            "Swing Duration (s)",
            "Frequency",
            "Swing Duration Distribution",
            ".2f",
            " s",
            "green",
            plots_dir / "swing_duration_dist.png",
        )
        plot_line_with_mean(
            smoothness,
            "Rollout Index",
            "Trajectory Smoothness (0-1)",
            "Trajectory Smoothness Across Rollouts",
            plots_dir / "smoothness.png",
        )
        plot_scatter(
            durations,
            max_speeds,
            "Swing Duration (s)",
            "Max Clubhead Speed (m/s)",
            "Clubhead Speed vs Swing Duration",
            plots_dir / "speed_vs_duration.png",
        )
        logger.info(f" Plots saved to {plots_dir}")

    def generate_report(self, summary: dict) -> None:
        """Generate HTML evaluation report."""
        report_path = self.output_dir / "report.html"
        html = build_report_html(self.policy_path.name, summary)
        with open(report_path, "w") as f:
            f.write(html)
        logger.info(f" Report generated: {report_path}")

    def print_summary(self, summary: dict) -> None:
        """Print summary to console."""
        logger.info("\n" + "=" * 60)
        logger.info("EVALUATION SUMMARY")
        logger.info("=" * 60)
        cs = summary["clubhead_speed"]
        sd = summary["swing_duration"]
        ts = summary["trajectory_smoothness"]
        jv = summary["joint_limit_violations"]
        logger.info(f"\nClubhead Speed: {cs['max_mean']:.2f} ± {cs['max_std']:.2f} m/s")
        logger.info(f"  Range: {cs['max_min']:.2f} - {cs['max_max']:.2f} m/s")
        logger.info(f"\nSwing Duration: {sd['mean']:.3f} ± {sd['std']:.3f} s")
        logger.info(f"\nTrajectory Smoothness: {ts['mean']:.3f} ± {ts['std']:.3f}")
        logger.info(f"\nJoint Limit Violations: {jv['percentage']:.1f}% of rollouts")
        logger.info(f"  Total violations: {jv['total']}")
        logger.info("\n" + "=" * 60)


def _build_arg_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser."""
    parser = argparse.ArgumentParser(description="Evaluate trained golf swing policy")
    parser.add_argument(
        "--policy", type=str, required=True, help="Policy checkpoint path"
    )
    parser.add_argument(
        "--config", type=str, required=True, help="Robot/environment config YAML"
    )
    parser.add_argument(
        "--output-dir", type=str, required=True, help="Output directory"
    )
    parser.add_argument(
        "--num-rollouts", type=int, default=50, help="Number of rollouts (default: 50)"
    )
    parser.add_argument(
        "--record-video", action="store_true", help="Record videos of rollouts"
    )
    parser.add_argument(
        "--seed", type=int, default=42, help="Random seed (default: 42)"
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda" if torch.cuda.is_available() else "cpu",
        help="Device (cuda/cpu)",
    )
    return parser


def _run_evaluation(evaluator: "PolicyEvaluator", args: argparse.Namespace) -> None:
    """Execute evaluation pipeline: rollouts → summary → save → plots → report."""
    rollout_stats = evaluator.run_rollouts(
        num_rollouts=args.num_rollouts,
        record_video=args.record_video,
    )
    summary = evaluator.compute_summary_metrics(rollout_stats)
    evaluator.save_results(rollout_stats, summary)
    evaluator.generate_plots(rollout_stats)
    evaluator.generate_report(summary)
    evaluator.print_summary(summary)


def main() -> None:
    """Entry point."""
    args = _build_arg_parser().parse_args()
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)
    evaluator = PolicyEvaluator(
        policy_path=args.policy,
        config_path=args.config,
        output_dir=args.output_dir,
        device=args.device,
    )
    _run_evaluation(evaluator, args)


if __name__ == "__main__":
    main()
