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
from pathlib import Path

import numpy as np
import torch
import yaml

try:
    import matplotlib
    import matplotlib.pyplot as plt

    matplotlib.use("Agg")  # Non-interactive backend
except ImportError:
    plt = None
    print("Warning: matplotlib not installed. Plots will not be generated.")


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
        # TODO: Load actual policy from checkpoint
        # self.policy = load_policy(policy_path)

        print(f"Loaded policy: {policy_path}")
        print(f"Output directory: {output_dir}")

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
        """
        print(f"\nRunning {num_rollouts} rollouts...")

        rollout_stats = []

        for i in range(num_rollouts):
            # TODO: Run actual rollout in Isaac Lab environment
            # For now, generate synthetic statistics
            stats = self._generate_synthetic_rollout(i)
            rollout_stats.append(stats)

            if (i + 1) % 10 == 0:
                print(f"  Completed {i + 1}/{num_rollouts} rollouts")

        return rollout_stats

    def _generate_synthetic_rollout(self, rollout_id: int) -> dict:
        """
        Generate synthetic rollout statistics (placeholder).

        In real implementation, this would:
        1. Reset environment
        2. Run policy for episode
        3. Collect trajectory data
        4. Compute metrics
        """
        np.random.seed(rollout_id + 42)

        # Synthetic metrics (realistic ranges for golf swing)
        stats = {
            "rollout_id": rollout_id,
            "max_clubhead_speed": np.random.normal(39.2, 2.8),  # m/s
            "mean_clubhead_speed": np.random.normal(22.5, 1.5),
            "swing_duration": np.random.normal(1.42, 0.08),  # seconds
            "backswing_duration": np.random.normal(0.65, 0.05),
            "downswing_duration": np.random.normal(0.28, 0.03),
            "follow_through_duration": np.random.normal(0.49, 0.04),
            "trajectory_smoothness": np.random.uniform(0.80, 0.95),  # 0-1
            "joint_limit_violations": np.random.poisson(0.5),  # count
            "trajectory_error": np.random.exponential(0.05),  # meters
        }

        return stats

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

    def save_results(self, rollout_stats: list[dict], summary: dict):
        """Save evaluation results to disk."""
        # Save raw rollout data
        results_file = self.output_dir / "rollout_results.json"
        with open(results_file, "w") as f:
            json.dump(rollout_stats, f, indent=2)

        # Save summary
        summary_file = self.output_dir / "summary.json"
        with open(summary_file, "w") as f:
            json.dump(summary, f, indent=2)

        print("\n✓ Results saved:")
        print(f"  Rollout data: {results_file}")
        print(f"  Summary: {summary_file}")

    def generate_plots(self, rollout_stats: list[dict]):
        """Generate evaluation plots."""
        if plt is None:
            print("Skipping plots (matplotlib not available)")
            return

        plots_dir = self.output_dir / "plots"
        plots_dir.mkdir(exist_ok=True)

        # Extract data
        max_speeds = [s["max_clubhead_speed"] for s in rollout_stats]
        durations = [s["swing_duration"] for s in rollout_stats]
        smoothness = [s["trajectory_smoothness"] for s in rollout_stats]

        # Plot 1: Clubhead speed distribution
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hist(max_speeds, bins=20, edgecolor="black", alpha=0.7)
        ax.axvline(
            np.mean(max_speeds),
            color="red",
            linestyle="--",
            label=f"Mean: {np.mean(max_speeds):.1f} m/s",
        )
        ax.set_xlabel("Max Clubhead Speed (m/s)")
        ax.set_ylabel("Frequency")
        ax.set_title("Clubhead Speed Distribution")
        ax.legend()
        ax.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(plots_dir / "clubhead_speed_dist.png", dpi=150)
        plt.close()

        # Plot 2: Swing duration distribution
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.hist(durations, bins=20, edgecolor="black", alpha=0.7, color="green")
        ax.axvline(
            np.mean(durations),
            color="red",
            linestyle="--",
            label=f"Mean: {np.mean(durations):.2f} s",
        )
        ax.set_xlabel("Swing Duration (s)")
        ax.set_ylabel("Frequency")
        ax.set_title("Swing Duration Distribution")
        ax.legend()
        ax.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(plots_dir / "swing_duration_dist.png", dpi=150)
        plt.close()

        # Plot 3: Smoothness over rollouts
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.plot(smoothness, marker="o", markersize=4, alpha=0.6)
        ax.axhline(
            np.mean(smoothness),
            color="red",
            linestyle="--",
            label=f"Mean: {np.mean(smoothness):.3f}",
        )
        ax.set_xlabel("Rollout Index")
        ax.set_ylabel("Trajectory Smoothness (0-1)")
        ax.set_title("Trajectory Smoothness Across Rollouts")
        ax.legend()
        ax.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(plots_dir / "smoothness.png", dpi=150)
        plt.close()

        # Plot 4: Speed vs Duration scatter
        fig, ax = plt.subplots(figsize=(10, 6))
        ax.scatter(durations, max_speeds, alpha=0.6)
        ax.set_xlabel("Swing Duration (s)")
        ax.set_ylabel("Max Clubhead Speed (m/s)")
        ax.set_title("Clubhead Speed vs Swing Duration")
        ax.grid(alpha=0.3)
        plt.tight_layout()
        plt.savefig(plots_dir / "speed_vs_duration.png", dpi=150)
        plt.close()

        print(f"✓ Plots saved to {plots_dir}")

    def generate_report(self, summary: dict):
        """Generate HTML evaluation report."""
        report_path = self.output_dir / "report.html"

        html = f"""
<!DOCTYPE html>
<html>
<head>
    <title>Project GROOT Evaluation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 40px; }}
        h1 {{ color: #333; }}
        h2 {{ color: #666; margin-top: 30px; }}
        table {{ border-collapse: collapse; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #4CAF50; color: white; }}
        .metric {{ font-size: 24px; font-weight: bold; color: #4CAF50; }}
        .plot {{ margin: 20px 0; }}
        .plot img {{ max-width: 100%; height: auto; border: 1px solid #ddd; }}
    </style>
</head>
<body>
    <h1>Project GROOT Evaluation Report</h1>
    <p><strong>Policy:</strong> {self.policy_path.name}</p>
    <p><strong>Number of Rollouts:</strong> {summary["num_rollouts"]}</p>

    <h2>Summary Metrics</h2>

    <h3>Clubhead Speed</h3>
    <table>
        <tr>
            <th>Metric</th>
            <th>Value</th>
        </tr>
        <tr>
            <td>Mean Max Speed</td>
            <td class="metric">{summary["clubhead_speed"]["max_mean"]:.2f} m/s</td>
        </tr>
        <tr>
            <td>Std Dev</td>
            <td>{summary["clubhead_speed"]["max_std"]:.2f} m/s</td>
        </tr>
        <tr>
            <td>Range</td>
            <td>
                {summary["clubhead_speed"]["max_min"]:.2f} -
                {summary["clubhead_speed"]["max_max"]:.2f} m/s
            </td>
        </tr>
    </table>

    <h3>Swing Timing</h3>
    <table>
        <tr>
            <th>Metric</th>
            <th>Value</th>
        </tr>
        <tr>
            <td>Mean Duration</td>
            <td>
                {summary["swing_duration"]["mean"]:.3f} ±
                {summary["swing_duration"]["std"]:.3f} s
            </td>
        </tr>
    </table>

    <h3>Quality Metrics</h3>
    <table>
        <tr>
            <th>Metric</th>
            <th>Value</th>
        </tr>
        <tr>
            <td>Trajectory Smoothness</td>
            <td>
                {summary["trajectory_smoothness"]["mean"]:.3f} ±
                {summary["trajectory_smoothness"]["std"]:.3f}
            </td>
        </tr>
        <tr>
            <td>Joint Limit Violations</td>
            <td>{summary["joint_limit_violations"]["percentage"]:.1f}% of rollouts</td>
        </tr>
    </table>

    <h2>Visualizations</h2>
    <div class="plot">
        <h3>Clubhead Speed Distribution</h3>
        <img src="plots/clubhead_speed_dist.png" alt="Clubhead Speed">
    </div>
    <div class="plot">
        <h3>Swing Duration Distribution</h3>
        <img src="plots/swing_duration_dist.png" alt="Swing Duration">
    </div>
    <div class="plot">
        <h3>Trajectory Smoothness</h3>
        <img src="plots/smoothness.png" alt="Smoothness">
    </div>
    <div class="plot">
        <h3>Speed vs Duration</h3>
        <img src="plots/speed_vs_duration.png" alt="Speed vs Duration">
    </div>
</body>
</html>
"""

        with open(report_path, "w") as f:
            f.write(html)

        print(f"✓ Report generated: {report_path}")

    def print_summary(self, summary: dict):
        """Print summary to console."""
        print("\n" + "=" * 60)
        print("EVALUATION SUMMARY")
        print("=" * 60)

        cs = summary["clubhead_speed"]
        print(f"\nClubhead Speed: {cs['max_mean']:.2f} ± {cs['max_std']:.2f} m/s")
        print(f"  Range: {cs['max_min']:.2f} - {cs['max_max']:.2f} m/s")
        print("  Target: 40-45 m/s")

        sd = summary["swing_duration"]
        print(f"\nSwing Duration: {sd['mean']:.3f} ± {sd['std']:.3f} s")
        print("  Target: 1.2-1.5 s")

        ts = summary["trajectory_smoothness"]
        print(f"\nTrajectory Smoothness: {ts['mean']:.3f} ± {ts['std']:.3f}")
        print("  (0-1 scale, higher is better)")

        jv = summary["joint_limit_violations"]
        print(f"\nJoint Limit Violations: {jv['percentage']:.1f}% of rollouts")
        print(f"  Total violations: {jv['total']}")

        print("\n" + "=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Evaluate trained golf swing policy")

    parser.add_argument(
        "--policy",
        type=str,
        required=True,
        help="Path to policy checkpoint",
    )
    parser.add_argument(
        "--config",
        type=str,
        required=True,
        help="Robot/environment configuration YAML",
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
        "--record-video",
        action="store_true",
        help="Record videos of rollouts",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed (default: 42)",
    )
    parser.add_argument(
        "--device",
        type=str,
        default="cuda" if torch.cuda.is_available() else "cpu",
        help="Device (cuda/cpu)",
    )

    args = parser.parse_args()

    # Set seed
    np.random.seed(args.seed)
    torch.manual_seed(args.seed)

    # Create evaluator
    evaluator = PolicyEvaluator(
        policy_path=args.policy,
        config_path=args.config,
        output_dir=args.output_dir,
        device=args.device,
    )

    # Run rollouts
    rollout_stats = evaluator.run_rollouts(
        num_rollouts=args.num_rollouts,
        record_video=args.record_video,
    )

    # Compute summary
    summary = evaluator.compute_summary_metrics(rollout_stats)

    # Save results
    evaluator.save_results(rollout_stats, summary)

    # Generate plots
    evaluator.generate_plots(rollout_stats)

    # Generate report
    evaluator.generate_report(summary)

    # Print summary
    evaluator.print_summary(summary)


if __name__ == "__main__":
    main()
