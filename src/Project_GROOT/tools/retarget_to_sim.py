import logging

from numba import jit

logger = logging.getLogger(__name__)

#!/usr/bin/env python3
"""
Retargeting Tool for Project GROOT

Retargets human skeleton poses to robot joint space using inverse kinematics.

Converts human golf swing demonstrations into robot-executable trajectories.

Usage:
    python retarget_to_sim.py --input-dir data/processed_pose \
        --output-dir data/retargeted_demos \
        --robot-config sim/configs/humanoid_upper.yaml
"""

import argparse
import json
from pathlib import Path
from typing import Any

import numpy as np
import yaml

try:
    from tqdm import tqdm
except ImportError:

    def tqdm(x, **kwargs):
        return x


try:
    from scipy.interpolate import interp1d
    from scipy.ndimage import gaussian_filter1d
except ImportError:
    logger.info("Warning: scipy not installed. Install with: pip install scipy")
    gaussian_filter1d = None
    interp1d = None


class RobotConfig:
    """Robot configuration for retargeting."""

    def __init__(self, config_path: str):
        """Load robot configuration from YAML."""
        with open(config_path) as f:
            config = yaml.safe_load(f)

        self.name = config.get("name", "humanoid")
        self.dof_names = config["dof_names"]
        self.num_dofs = len(self.dof_names)

        # Joint limits
        self.joint_lower = np.array(config["joint_limits"]["lower"])
        self.joint_upper = np.array(config["joint_limits"]["upper"])

        # Velocity/acceleration limits
        self.velocity_limits = np.array(config.get("velocity_limits", [10.0] * self.num_dofs))
        self.acceleration_limits = np.array(
            config.get("acceleration_limits", [50.0] * self.num_dofs)
        )

        # End-effector mappings
        self.ee_links = config.get("end_effectors", {})

    def clip_joints(self, q: np.ndarray) -> np.ndarray:
        """Clip joint positions to limits."""
        return np.clip(q, self.joint_lower, self.joint_upper)


class PoseRetargeter:
    """Retarget human poses to robot joint space."""

    def __init__(
        self,
        robot_config: RobotConfig,
        ik_solver: str = "trac_ik",
        smooth_window: int = 5,
    ):
        """
        Args:
            robot_config: Robot configuration
            ik_solver: IK solver to use (trac_ik, lma, etc.)
            smooth_window: Smoothing window size (sigma for Gaussian filter)
        """
        self.robot_config = robot_config
        self.ik_solver = ik_solver
        self.smooth_window = smooth_window

    def retarget(
        self,
        skeleton: np.ndarray,
        club_head: np.ndarray,
        timestamps: np.ndarray,
    ) -> dict[str, np.ndarray]:
        """
        Retarget human pose sequence to robot joint trajectory.

        Args:
            skeleton: (T, num_joints, 3) human skeleton
            club_head: (T, 3) clubhead positions
            timestamps: (T,) frame timestamps

        Returns:
            Dictionary with:
                - q: (T, num_dofs) joint positions
                - qdot: (T, num_dofs) joint velocities
                - qddot: (T, num_dofs) joint accelerations
                - ee_pos: (T, 3) end-effector (club head) position
                - dof_names: List of DOF names
        """
        T = len(skeleton)

        # Initialize joint trajectory
        q = np.zeros((T, self.robot_config.num_dofs))

        # Simplified IK: map key human joints to robot DOFs
        # This is a placeholder - real IK would use proper solver
        q = self._simple_ik_mapping(skeleton, club_head)

        # Clip to joint limits
        q = np.clip(q, self.robot_config.joint_lower, self.robot_config.joint_upper)

        # Smooth trajectory
        if self.smooth_window > 0 and gaussian_filter1d is not None:
            for i in range(self.robot_config.num_dofs):
                q[:, i] = gaussian_filter1d(q[:, i], sigma=self.smooth_window)

        # Re-clip after smoothing
        q = np.clip(q, self.robot_config.joint_lower, self.robot_config.joint_upper)

        # Compute velocities and accelerations
        dt = np.diff(timestamps)
        dt = np.clip(dt, 1e-6, None)  # Avoid division by zero

        # Velocity (central difference)
        qdot = np.zeros_like(q)
        qdot[1:-1] = (q[2:] - q[:-2]) / (dt[1:, None] + dt[:-1, None])
        qdot[0] = (q[1] - q[0]) / dt[0]
        qdot[-1] = (q[-1] - q[-2]) / dt[-1]

        # Acceleration
        qddot = np.zeros_like(q)
        qddot[1:-1] = (qdot[2:] - qdot[:-2]) / (dt[1:, None] + dt[:-1, None])

        # End-effector position (use club head as proxy)
        ee_pos = club_head.copy()

        return {
            "q": q,
            "qdot": qdot,
            "qddot": qddot,
            "ee_pos": ee_pos,
            "dof_names": self.robot_config.dof_names,
            "timestamps": timestamps,
        }

    @jit(nopython=True, fastmath=True)
    def _simple_ik_mapping(self, skeleton: np.ndarray, club_head: np.ndarray) -> np.ndarray:
        """
        Simplified IK: heuristic mapping from human joints to robot DOFs.

        For a full implementation, this would use:
        - TracIK, TRAC-IK, or similar solver
        - Proper robot URDF/kinematic chain
        - Optimization to match end-effector trajectory

        This baseline uses geometric heuristics based on joint angles.

        Args:
            skeleton: (T, 33, 3) MediaPipe skeleton
            club_head: (T, 3) club head trajectory

        Returns:
            q: (T, num_dofs) joint angles
        """
        T = len(skeleton)
        num_dofs = self.robot_config.num_dofs

        # Placeholder: map shoulder/elbow/wrist angles to robot DOFs
        q = np.zeros((T, num_dofs))

        # MediaPipe joint indices
        LEFT_SHOULDER = 11
        RIGHT_SHOULDER = 12
        LEFT_ELBOW = 13
        RIGHT_ELBOW = 14
        LEFT_WRIST = 15
        RIGHT_WRIST = 16

        # Extract key joints
        left_shoulder = skeleton[:, LEFT_SHOULDER, :]
        right_shoulder = skeleton[:, RIGHT_SHOULDER, :]
        left_elbow = skeleton[:, LEFT_ELBOW, :]
        right_elbow = skeleton[:, RIGHT_ELBOW, :]
        left_wrist = skeleton[:, LEFT_WRIST, :]
        right_wrist = skeleton[:, RIGHT_WRIST, :]

        # Compute shoulder angles (simplified)
        # DOF mapping (example for upper body humanoid):
        # 0: torso_pitch
        # 1: torso_yaw
        # 2: torso_roll
        # 3-5: left_shoulder (pitch, roll, yaw)
        # 6: left_elbow
        # 7-9: right_shoulder (pitch, roll, yaw)
        # 10: right_elbow

        for t in range(T):
            # Torso orientation from shoulder line
            shoulder_vec = right_shoulder[t] - left_shoulder[t]
            torso_yaw = np.arctan2(shoulder_vec[0], shoulder_vec[2])
            q[t, 1] = torso_yaw

            # Left arm
            left_upper = left_elbow[t] - left_shoulder[t]
            left_forearm = left_wrist[t] - left_elbow[t]

            # Shoulder pitch (vertical angle)
            q[t, 3] = np.arctan2(-left_upper[1], np.linalg.norm(left_upper[[0, 2]]))

            # Elbow flexion
            elbow_angle = self._vector_angle(left_upper, left_forearm)
            q[t, 6] = np.pi - elbow_angle  # Elbow flexion

            # Right arm (mirror)
            right_upper = right_elbow[t] - right_shoulder[t]
            right_forearm = right_wrist[t] - right_elbow[t]

            q[t, 7] = np.arctan2(-right_upper[1], np.linalg.norm(right_upper[[0, 2]]))
            elbow_angle = self._vector_angle(right_upper, right_forearm)
            q[t, 10] = np.pi - elbow_angle

        # Scale to reasonable ranges (heuristic)
        q = np.clip(q, -np.pi, np.pi)

        # Pad or trim to match robot DOFs
        if q.shape[1] < num_dofs:
            q = np.pad(q, ((0, 0), (0, num_dofs - q.shape[1])))
        else:
            q = q[:, :num_dofs]

        return q

    def _vector_angle(self, v1: np.ndarray, v2: np.ndarray) -> float:
        """Compute angle between two vectors."""
        v1_norm = v1 / (np.linalg.norm(v1) + 1e-8)
        v2_norm = v2 / (np.linalg.norm(v2) + 1e-8)
        cos_angle = np.clip(np.dot(v1_norm, v2_norm), -1.0, 1.0)
        return np.arccos(cos_angle)


def validate_trajectory(
    q: np.ndarray,
    qdot: np.ndarray,
    robot_config: RobotConfig,
) -> dict[str, Any]:
    """
    Validate retargeted trajectory for joint limits, velocity, etc.

    Args:
        q: (T, num_dofs) joint positions
        qdot: (T, num_dofs) joint velocities
        robot_config: Robot configuration

    Returns:
        Validation report dict
    """
    report = {
        "valid": True,
        "warnings": [],
        "errors": [],
    }

    # Check joint limits
    below_lower = (q < robot_config.joint_lower).any(axis=0)
    above_upper = (q > robot_config.joint_upper).any(axis=0)

    for i, dof_name in enumerate(robot_config.dof_names):
        if below_lower[i] or above_upper[i]:
            report["errors"].append(f"Joint limit violation: {dof_name}")
            report["valid"] = False

    # Check velocity limits
    max_velocities = np.abs(qdot).max(axis=0)
    for i, (max_vel, limit) in enumerate(
        zip(max_velocities, robot_config.velocity_limits, strict=False)
    ):
        if max_vel > limit:
            report["warnings"].append(
                f"Velocity limit exceeded: {robot_config.dof_names[i]} "
                f"({max_vel:.2f} > {limit:.2f} rad/s)"
            )

    # Check for discontinuities
    q_diff = np.abs(np.diff(q, axis=0))
    max_jump = q_diff.max(axis=0)

    for i, jump in enumerate(max_jump):
        if jump > 0.5:  # 0.5 rad jump threshold
            report["warnings"].append(
                f"Large discontinuity in {robot_config.dof_names[i]}: {jump:.3f} rad"
            )

    return report


def main():
    parser = argparse.ArgumentParser(
        description="Retarget human poses to robot joint space",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--input-dir",
        type=str,
        required=True,
        help="Input directory with processed pose .npz files",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="Output directory for retargeted demos",
    )
    parser.add_argument(
        "--robot-config",
        type=str,
        required=True,
        help="Robot configuration YAML file",
    )
    parser.add_argument(
        "--ik-solver",
        type=str,
        default="trac_ik",
        choices=["trac_ik", "lma", "simple"],
        help="IK solver (default: trac_ik)",
    )
    parser.add_argument(
        "--smooth-window",
        type=int,
        default=5,
        help="Smoothing window size (default: 5)",
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Visualize retargeted trajectories",
    )

    args = parser.parse_args()

    # Load robot config
    robot_config = RobotConfig(args.robot_config)
    logger.info(f"Loaded robot config: {robot_config.name}")
    logger.info(f"  DOFs: {robot_config.num_dofs}")
    logger.info(f"  DOF names: {robot_config.dof_names}")

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Find all pose files
    input_dir = Path(args.input_dir)
    pose_files = sorted(input_dir.glob("*.npz"))

    if not pose_files:
        logger.info(f"No .npz files found in {input_dir}")
        return

    logger.info(f"Found {len(pose_files)} pose files")

    # Initialize retargeter
    retargeter = PoseRetargeter(
        robot_config=robot_config,
        ik_solver=args.ik_solver,
        smooth_window=args.smooth_window,
    )

    # Process each file
    all_reports = []
    for pose_file in tqdm(pose_files, desc="Retargeting"):
        try:
            # Load pose data
            data = np.load(pose_file)
            skeleton = data["skeleton"]
            club_head = data["club_head"]
            timestamps = data["timestamps"]

            # Retarget
            result = retargeter.retarget(skeleton, club_head, timestamps)

            # Validate
            validation = validate_trajectory(
                result["q"],
                result["qdot"],
                robot_config,
            )

            # Save
            output_file = output_dir / pose_file.name
            np.savez(output_file, **result)

            # Report
            report = {
                "file": pose_file.name,
                "valid": validation["valid"],
                "warnings": validation["warnings"],
                "errors": validation["errors"],
            }
            all_reports.append(report)

            # Print status
            status = "✓" if validation["valid"] else "✗"
            logger.info(f"  {status} {pose_file.name}")
            if validation["errors"]:
                for error in validation["errors"]:
                    logger.info(f"      ERROR: {error}")
            if validation["warnings"]:
                for warning in validation["warnings"][:2]:  # Show first 2
                    logger.info(f"      WARNING: {warning}")

        except Exception as e:  # noqa: BLE001
            logger.info(f"  ✗ {pose_file.name}: {e}")
            all_reports.append(
                {
                    "file": pose_file.name,
                    "valid": False,
                    "errors": [str(e)],
                }
            )

    # Save validation report
    report_file = output_dir / "retargeting_report.json"
    with open(report_file, "w") as f:
        json.dump({"demos": all_reports}, f, indent=2)

    # Summary
    num_valid = sum(1 for r in all_reports if r["valid"])
    logger.info("\n✓ Retargeting complete")
    logger.info(f"  Valid demos: {num_valid}/{len(all_reports)}")
    logger.info(f"  Output: {output_dir}")
    logger.info(f"  Report: {report_file}")


if __name__ == "__main__":
    main()
