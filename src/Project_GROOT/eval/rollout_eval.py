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
    python eval/rollout_eval.py \
        --policy train/outputs/imitation_policy/checkpoints/best.pth \
        --config sim/configs/humanoid_upper.yaml --num-rollouts 50 \
        --output-dir eval/outputs/eval_results
"""

import argparse
import json
import logging
from pathlib import Path

import numpy as np
import torch
import yaml

logger = logging.getLogger(__name__)

try:
    import matplotlib
    import matplotlib.pyplot as plt

    matplotlib.use("Agg")  # Non-interactive backend
except ImportError:
    plt = None
    logger.info("Warning: matplotlib not installed. Plots will not be generated.")

_HTML_CSS = """
    body { font-family: Arial, sans-serif; margin: 40px; }
    h1 { color: #333; }
    h2 { color: #666; margin-top: 30px; }
    table { border-collapse: collapse; margin: 20px 0; }
    th, td { border: 1px solid #ddd; padding: 12px; text-align: left; }
    th { background-color: #4CAF50; color: white; }
    .metric { font-size: 24px; font-weight: bold; color: #4CAF50; }
    .plot { margin: 20px 0; }
    .plot img { max-width: 100%; height: auto; border: 1px solid #ddd; }
"""


def _build_report_html(policy_name: str, summary: dict) -> str:
    """Build HTML evaluation report string from summary metrics.

    Args:
        policy_name: Name of the evaluated policy checkpoint.
        summary: Summary dict produced by compute_summary_metrics().

    Returns:
        Complete HTML report as a string.
    """
    cs = summary["clubhead_speed"]
    sd = summary["swing_duration"]
    ts = summary["trajectory_smoothness"]
    jv = summary["joint_limit_violations"]

    speed_range = f"{cs['max_min']:.2f} - {cs['max_max']:.2f} m/s"
    duration_cell = f"{sd['mean']:.3f} &plusmn; {sd['std']:.3f} s"
    smoothness_cell = f"{ts['mean']:.3f} &plusmn; {ts['std']:.3f}"

    return f"""<!DOCTYPE html>
<html>
<head>
    <title>Project GROOT Evaluation Report</title>
    <style>{_HTML_CSS}    </style>
</head>
<body>
    <h1>Project GROOT Evaluation Report</h1>
    <p><strong>Policy:</strong> {policy_name}</p>
    <p><strong>Number of Rollouts:</strong> {summary["num_rollouts"]}</p>
    <h2>Summary Metrics</h2>
    <h3>Clubhead Speed</h3>
    <table>
        <tr><th>Metric</th><th>Value</th></tr>
        <tr><td>Mean Max Speed</td>
            <td class="metric">{cs["max_mean"]:.2f} m/s</td></tr>
        <tr><td>Std Dev</td><td>{cs["max_std"]:.2f} m/s</td></tr>
        <tr><td>Range</td><td>{speed_range}</td></tr>
    </table>
    <h3>Swing Timing</h3>
    <table>
        <tr><th>Metric</th><th>Value</th></tr>
        <tr><td>Mean Duration</td><td>{duration_cell}</td></tr>
    </table>
    <h3>Quality Metrics</h3>
    <table>
        <tr><th>Metric</th><th>Value</th></tr>
        <tr><td>Trajectory Smoothness</td><td>{smoothness_cell}</td></tr>
        <tr><td>Joint Limit Violations</td>
            <td>{jv["percentage"]:.1f}% of rollouts</td></tr>
    </table>
    <h2>Visualizations</h2>
    <div class="plot"><h3>Clubhead Speed Distribution</h3>
        <img src="plots/clubhead_speed_dist.png" alt="Clubhead Speed"></div>
    <div class="plot"><h3>Swing Duration Distribution</h3>
        <img src="plots/swing_duration_dist.png" alt="Swing Duration"></div>
    <div class="plot"><h3>Trajectory Smoothness</h3>
        <img src="plots/smoothness.png" alt="Smoothness"></div>
    <div class="plot"><h3>Speed vs Duration</h3>
        <img src="plots/speed_vs_duration.png" alt="Speed vs Duration"></div>
</body>
</html>
"""


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

        # Load configuration
        with open(config_path) as f:
            self.config = yaml.safe_load(f)

        # Load policy
        # DEFERRED: Load actual policy from checkpoint
        # self.policy = load_policy(policy_path)

        logger.info(f"Loaded policy: {policy_path}")
        logger.info(f"Output directory: {output_dir}")

    def run_rollouts(
        self, num_rollouts: int = 50, record_video: bool = False
    ) -> list[dict]:
        """
        Run multiple policy rollouts and collect metrics.

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
        It must run actual policy rollouts, not generate synthetic data.

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
        # Extract metrics
        max_speeds = [s["max_clubhead_speed"] for s in rollout_stats]
        durations = [s["swing_duration"] for s in rollout_stats]
        smoothness = [s["trajectory_smoothness"] for s in rollout_stats]
        violations = [s["joint_limit_violations"] for s in rollout_stats]

        summary = {
            "num_rollouts": len(rollout_stats),
            "clubhead_speed": {
                "max_mean": np.mean(max_speeds),
                "max_std": np.std(max_speeds),
                "max_min": np.min(max_speeds),
                "max_max": np.max(max_speeds),
            },
            "swing_duration": {
                "mean": np.mean(durations),
                "std": np.std(durations),
            },
            "trajectory_smoothness": {
                "mean": np.mean(smoothness),
                "std": np.std(smoothness),
            },
            "joint_limit_violations": {
                "mean": np.mean(violations),
                "total": np.sum(violations),
                "percentage": 100 * np.mean([v > 0 for v in violations]),
            },
        }

        return summary

    def save_results(self, rollout_stats: list[dict], summary: dict) -> None:
        """Save evaluation results to disk."""
        # Save raw rollout data
        results_file = self.output_dir / "rollout_results.json"
        with open(results_file, "w") as f:
            json.dump(rollout_stats, f, indent=2)

        # Save summary
        summary_file = self.output_dir / "summary.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)

        logger.info("\n✓ Results saved:")
        logger.info(f"  Rollout data: {results_file}")
        logger.info(f"  Summary: {summary_file}")

    def generate_plots(self, rollout_stats: list[dict]) -> None:
        """Generate evaluation plots."""
        if plt is None:
            logger.info("Skipping plots (matplotlib not available)")
            return

        plots_dir = self.output_dir / "plots"
        plots_dir.mkdir(exist_ok=True)

        max_speeds = [s["max_clubhead_speed"] for s in rollout_stats]
        durations = [s["swing_duration"] for s in rollout_stats]
        smoothness = [s["trajectory_smoothness"] for s in rollout_stats]

        self._plot_hist_with_mean(
            max_speeds,
            xlabel="Max Clubhead Speed (m/s)",
            ylabel="Frequency",
            title="Clubhead Speed Distribution",
            mean_fmt=".1f",
            mean_unit=" m/s",
            color="steelblue",
            path=plots_dir / "clubhead_speed_dist.png",
        )
        self._plot_hist_with_mean(
            durations,
            xlabel="Swing Duration (s)",
            ylabel="Frequency",
            title="Swing Duration Distribution",
            mean_fmt=".2f",
            mean_unit=" s",
            color="green",
            path=plots_dir / "swing_duration_dist.png",
        )
        self._plot_line_with_mean(
            smoothness,
            xlabel="Rollout Index",
            ylabel="Trajectory Smoothness (0-1)",
            title="Trajectory Smoothness Across Rollouts",
            path=plots_dir / "smoothness.png",
        )
        self._plot_scatter(
            x=durations,
            y=max_speeds,
            xlabel="Swing Duration (s)",
            ylabel="Max Clubhead Speed (m/s)",
            title="Clubhead Speed vs Swing Duration",
            path=plots_dir / "speed_vs_duration.png",
        )

        logger.info(f"✓ Plots saved to {plots_dir}")

    def _plot_hist_with_mean(
        self,
        data: list[float],
        xlabel: str,
        ylabel: str,
        title: str,
        mean_fmt: str,
        mean_unit: str,
        color: str,
        path: object,
    ) -> None:
        """Save a histogram with a mean reference line."""
        mean_val = np.mean(data)
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hist(data, bins=20, edgecolor="black", alpha=0.7, color=color)
        ax.axvline(
            mean_val,
            color="red",
            linestyle="--",
            label=f"Mean: {mean_val:{mean_fmt}}{mean_unit}",
        )
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.legend()
        ax.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(path, dpi=150)
        plt.close()

    def _plot_line_with_mean(
        self,
        data: list[float],
        xlabel: str,
        ylabel: str,
        title: str,
        path: object,
    ) -> None:
        """Save a line plot with a mean reference line."""
        mean_val = np.mean(data)
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(data, marker="o", markersize=4, alpha=0.6)
        ax.axhline(
            mean_val,
            color="red",
            linestyle="--",
            label=f"Mean: {mean_val:.3f}",
        )
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.legend()
        ax.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(path, dpi=150)
        plt.close()

    def _plot_scatter(
        self,
        x: list[float],
        y: list[float],
        xlabel: str,
        ylabel: str,
        title: str,
        path: object,
    ) -> None:
        """Save a scatter plot."""
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.scatter(x, y, alpha=0.6)
        ax.set_xlabel(xlabel)
        ax.set_ylabel(ylabel)
        ax.set_title(title)
        ax.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(path, dpi=150)
        plt.close()

    def generate_report(self, summary: dict) -> None:
        """Generate HTML evaluation report."""
        report_path = self.output_dir / "report.html"
        html = _build_report_html(self.policy_path.name, summary)
        with open(report_path, "w") as f:
            f.write(html)
        logger.info(f"✓ Report generated: {report_path}")

    def print_summary(self, summary: dict) -> None:
        """Print summary to console."""
        logger.info("\n" + "=" * 60)
        logger.info("EVALUATION SUMMARY")
        logger.info("=" * 60)

        cs = summary["clubhead_speed"]
        logger.info(f"\nClubhead Speed: {cs['max_mean']:.2f} ± {cs['max_std']:.2f} m/s")
        logger.info(f"  Range: {cs['max_min']:.2f} - {cs['max_max']:.2f} m/s")
        logger.info("  Target: 40-45 m/s")

        sd = summary["swing_duration"]
        logger.info(f"\nSwing Duration: {sd['mean']:.3f} ± {sd['std']:.3f} s")
        logger.info("  Target: 1.2-1.5 s")

        ts = summary["trajectory_smoothness"]
        logger.info(f"\nTrajectory Smoothness: {ts['mean']:.3f} ± {ts['std']:.3f}")
        logger.info("  (0-1 scale, higher is better)")

        jv = summary["joint_limit_violations"]
        logger.info(f"\nJoint Limit Violations: {jv['percentage']:.1f}% of rollouts")
        logger.info(f"  Total violations: {jv['total']}")

        logger.info("\n" + "=" * 60)


def _build_arg_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser."""
    parser = argparse.ArgumentParser(description="Evaluate trained golf swing policy")
    parser.add_argument(
        "--policy", type=str, required=True, help="Path to policy checkpoint"
    )
    parser.add_argument(
        "--config", type=str, required=True, help="Robot/environment configuration YAML"
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="Output directory for evaluation results",
    )
    parser.add_argument(
        "--num-rollouts",
        type=int,
        default=50,
        help="Number of evaluation rollouts (default: 50)",
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
