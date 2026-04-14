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
import logging
from pathlib import Path
from typing import Any

import numpy as np

try:
    import yaml
except ImportError:  # pragma: no cover - exercised implicitly in CI import smoke tests
    yaml = None

logger = logging.getLogger(__name__)

try:
    from tqdm import tqdm
except ImportError:

    def tqdm(x, **kwargs) -> Any:
        return x


logger = logging.getLogger(__name__)

try:
    from scipy.interpolate import interp1d
    from scipy.ndimage import gaussian_filter1d
except ImportError:
    logger.info("Warning: scipy not installed. Install with: pip install scipy")
    gaussian_filter1d = None
    interp1d = None

# MediaPipe landmark indices for key joints
_MP_LEFT_SHOULDER = 11
_MP_RIGHT_SHOULDER = 12
_MP_LEFT_ELBOW = 13
_MP_RIGHT_ELBOW = 14
_MP_LEFT_WRIST = 15
_MP_RIGHT_WRIST = 16


def _vector_angles_batch(v1: np.ndarray, v2: np.ndarray) -> np.ndarray:
    """Compute angles between paired row-vectors (T, 3) -> (T,)."""
    v1_norm = v1 / (np.linalg.norm(v1, axis=1, keepdims=True) + 1e-8)
    v2_norm = v2 / (np.linalg.norm(v2, axis=1, keepdims=True) + 1e-8)
    cos_angles = np.clip(np.sum(v1_norm * v2_norm, axis=1), -1.0, 1.0)
    return np.arccos(cos_angles)


def _extract_arm_joints(skeleton: np.ndarray) -> dict[str, np.ndarray]:
    """Extract arm and shoulder joint arrays from the skeleton.

    Args:
        skeleton: (T, num_joints, 3) skeleton keypoints.

    Returns:
        Dict mapping joint name to (T, 3) array.
    """
    return {
        "left_shoulder": skeleton[:, _MP_LEFT_SHOULDER, :],
        "right_shoulder": skeleton[:, _MP_RIGHT_SHOULDER, :],
        "left_elbow": skeleton[:, _MP_LEFT_ELBOW, :],
        "right_elbow": skeleton[:, _MP_RIGHT_ELBOW, :],
        "left_wrist": skeleton[:, _MP_LEFT_WRIST, :],
        "right_wrist": skeleton[:, _MP_RIGHT_WRIST, :],
    }


def _fill_torso_dofs(
    q: np.ndarray,
    left_shoulder: np.ndarray,
    right_shoulder: np.ndarray,
) -> None:
    """Fill torso DOF (yaw) in-place from the shoulder line.

    Args:
        q: (T, num_dofs) joint array to modify.
        left_shoulder: (T, 3) left shoulder positions.
        right_shoulder: (T, 3) right shoulder positions.
    """
    shoulder_vec = right_shoulder - left_shoulder  # (T, 3)
    q[:, 1] = np.arctan2(shoulder_vec[:, 0], shoulder_vec[:, 2])


def _fill_left_arm_dofs(
    q: np.ndarray,
    shoulder: np.ndarray,
    elbow: np.ndarray,
    wrist: np.ndarray,
) -> None:
    """Fill left arm DOFs (shoulder pitch, elbow flexion) in-place.

    Args:
        q: (T, num_dofs) joint array to modify.
        shoulder: (T, 3) left shoulder positions.
        elbow: (T, 3) left elbow positions.
        wrist: (T, 3) left wrist positions.
    """
    upper = elbow - shoulder  # (T, 3)
    forearm = wrist - elbow  # (T, 3)
    horiz = np.linalg.norm(upper[:, [0, 2]], axis=1)
    q[:, 3] = np.arctan2(-upper[:, 1], horiz)
    q[:, 6] = np.pi - _vector_angles_batch(upper, forearm)


def _fill_right_arm_dofs(
    q: np.ndarray,
    shoulder: np.ndarray,
    elbow: np.ndarray,
    wrist: np.ndarray,
) -> None:
    """Fill right arm DOFs (shoulder pitch, elbow flexion) in-place.

    Args:
        q: (T, num_dofs) joint array to modify.
        shoulder: (T, 3) right shoulder positions.
        elbow: (T, 3) right elbow positions.
        wrist: (T, 3) right wrist positions.
    """
    upper = elbow - shoulder  # (T, 3)
    forearm = wrist - elbow  # (T, 3)
    horiz = np.linalg.norm(upper[:, [0, 2]], axis=1)
    q[:, 7] = np.arctan2(-upper[:, 1], horiz)
    q[:, 10] = np.pi - _vector_angles_batch(upper, forearm)


def _fit_to_dofs(q: np.ndarray, num_dofs: int) -> np.ndarray:
    """Pad or trim q to match the robot's DOF count.

    Args:
        q: (T, M) joint array.
        num_dofs: Target number of DOFs.

    Returns:
        (T, num_dofs) array.
    """
    if q.shape[1] < num_dofs:
        return np.pad(q, ((0, 0), (0, num_dofs - q.shape[1])))
    return q[:, :num_dofs]


def _check_joint_limits(
    q: np.ndarray, robot_config: "RobotConfig"
) -> tuple[list[str], bool]:
    """Return joint-limit violation error messages and overall validity.

    Args:
        q: (T, num_dofs) joint positions.
        robot_config: Robot configuration with joint limits.

    Returns:
        Tuple of (error_messages, is_valid).
    """
    errors: list[str] = []
    below_lower = (q < robot_config.joint_lower).any(axis=0)
    above_upper = (q > robot_config.joint_upper).any(axis=0)
    for i, dof_name in enumerate(robot_config.dof_names):
        if below_lower[i] or above_upper[i]:
            errors.append(f"Joint limit violation: {dof_name}")
    return errors, len(errors) == 0


def _check_velocity_limits(qdot: np.ndarray, robot_config: "RobotConfig") -> list[str]:
    """Return velocity-limit warning messages.

    Args:
        qdot: (T, num_dofs) joint velocities.
        robot_config: Robot configuration with velocity limits.

    Returns:
        List of warning strings.
    """
    warnings: list[str] = []
    max_velocities = np.abs(qdot).max(axis=0)
    for i, (max_vel, limit) in enumerate(
        zip(max_velocities, robot_config.velocity_limits, strict=False)
    ):
        if max_vel > limit:
            warnings.append(
                f"Velocity limit exceeded: {robot_config.dof_names[i]} "
                f"({max_vel:.2f} > {limit:.2f} rad/s)"
            )
    return warnings


def _check_discontinuities(
    q: np.ndarray,
    robot_config: "RobotConfig",
    threshold: float = 0.5,
) -> list[str]:
    """Return discontinuity warning messages for large joint jumps.

    Args:
        q: (T, num_dofs) joint positions.
        robot_config: Robot configuration with DOF names.
        threshold: Jump size (rad) that triggers a warning.

    Returns:
        List of warning strings.
    """
    warnings: list[str] = []
    q_diff = np.abs(np.diff(q, axis=0))
    max_jump = q_diff.max(axis=0)
    for i, jump in enumerate(max_jump):
        if jump > threshold:
            warnings.append(
                f"Large discontinuity in {robot_config.dof_names[i]}: {jump:.3f} rad"
            )
    return warnings


class RobotConfig:
    """Robot configuration for retargeting."""

    def __init__(self, config_path: str):
        """Load robot configuration from YAML."""
        if yaml is None:
            raise ImportError(
                "PyYAML is required to load robot configurations. Install with "
                "'pip install PyYAML'."
            )
        with open(config_path) as f:
            config = yaml.safe_load(f)

        self.name = config.get("name", "humanoid")
        self.dof_names = config["dof_names"]
        self.num_dofs = len(self.dof_names)

        # Joint limits
        self.joint_lower = np.array(config["joint_limits"]["lower"])
        self.joint_upper = np.array(config["joint_limits"]["upper"])

        # Velocity/acceleration limits
        self.velocity_limits = np.array(
            config.get("velocity_limits", [10.0] * self.num_dofs)
        )
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
            Dictionary with q, qdot, qddot, ee_pos, dof_names, timestamps.

        Raises:
            ValueError: if inputs violate shape, size, or timestamp invariants.
        """
        # --- Preconditions (Design by Contract) ---
        if skeleton.ndim != 3 or skeleton.shape[2] != 3:
            msg = f"skeleton must be (T, num_joints, 3), got shape {skeleton.shape}"
            raise ValueError(msg)
        if skeleton.shape[1] < 17:
            msg = (
                f"skeleton needs at least 17 joints (MediaPipe indices 0-16), "
                f"got {skeleton.shape[1]}"
            )
            raise ValueError(msg)
        T = len(skeleton)
        if T < 3:
            msg = f"Need at least 3 frames for central-difference velocity, got {T}"
            raise ValueError(msg)
        if len(club_head) != T:
            msg = f"club_head length {len(club_head)} must match skeleton length {T}"
            raise ValueError(msg)
        if len(timestamps) != T:
            msg = f"timestamps length {len(timestamps)} must match skeleton length {T}"
            raise ValueError(msg)
        if not np.all(np.isfinite(timestamps)):
            raise ValueError("timestamps must be finite (no NaN or inf)")
        if not np.all(np.diff(timestamps) > 0):
            raise ValueError("timestamps must be strictly monotonically increasing")
        # --- End preconditions ---

        q = self._simple_ik_mapping(skeleton, club_head)
        q = self._ik_and_clip(q)
        q = self._smooth_and_reclip(q)
        qdot, qddot = self._compute_derivatives(q, timestamps)
        return {
            "q": q,
            "qdot": qdot,
            "qddot": qddot,
            "ee_pos": club_head.copy(),
            "dof_names": self.robot_config.dof_names,
            "timestamps": timestamps,
        }

    def _ik_and_clip(self, q: np.ndarray) -> np.ndarray:
        """Clip joint positions to robot limits.

        Args:
            q: (T, num_dofs) raw joint positions.

        Returns:
            Clipped (T, num_dofs) joint positions.
        """
        return np.clip(q, self.robot_config.joint_lower, self.robot_config.joint_upper)

    def _smooth_and_reclip(self, q: np.ndarray) -> np.ndarray:
        """Apply Gaussian smoothing per DOF then re-clip to limits.

        Args:
            q: (T, num_dofs) joint positions.

        Returns:
            Smoothed and re-clipped (T, num_dofs) array.
        """
        if self.smooth_window > 0 and gaussian_filter1d is not None:
            for i in range(self.robot_config.num_dofs):
                q[:, i] = gaussian_filter1d(q[:, i], sigma=self.smooth_window)
        return np.clip(q, self.robot_config.joint_lower, self.robot_config.joint_upper)

    def _compute_derivatives(
        self, q: np.ndarray, timestamps: np.ndarray
    ) -> tuple[np.ndarray, np.ndarray]:
        """Compute joint velocities and accelerations via finite differences.

        Args:
            q: (T, num_dofs) joint positions.
            timestamps: (T,) frame timestamps.

        Returns:
            Tuple of (qdot, qddot) each shaped (T, num_dofs).
        """
        dt = np.clip(np.diff(timestamps), 1e-6, None)
        qdot = np.zeros_like(q)
        qdot[1:-1] = (q[2:] - q[:-2]) / (dt[1:, None] + dt[:-1, None])
        qdot[0] = (q[1] - q[0]) / dt[0]
        qdot[-1] = (q[-1] - q[-2]) / dt[-1]
        qddot = np.zeros_like(q)
        qddot[1:-1] = (qdot[2:] - qdot[:-2]) / (dt[1:, None] + dt[:-1, None])
        return qdot, qddot

    def _simple_ik_mapping(
        self, skeleton: np.ndarray, club_head: np.ndarray
    ) -> np.ndarray:
        """Heuristic mapping from human joints to robot DOFs.

        Args:
            skeleton: (T, 33, 3) MediaPipe skeleton.
            club_head: (T, 3) club head trajectory (unused in heuristic).

        Returns:
            q: (T, num_dofs) joint angles, clipped to [-pi, pi].
        """
        T = len(skeleton)
        num_dofs = self.robot_config.num_dofs
        q = np.zeros((T, num_dofs))
        joints = _extract_arm_joints(skeleton)
        _fill_torso_dofs(q, joints["left_shoulder"], joints["right_shoulder"])
        _fill_left_arm_dofs(
            q, joints["left_shoulder"], joints["left_elbow"], joints["left_wrist"]
        )
        _fill_right_arm_dofs(
            q, joints["right_shoulder"], joints["right_elbow"], joints["right_wrist"]
        )
        q = np.clip(q, -np.pi, np.pi)
        return _fit_to_dofs(q, num_dofs)


def validate_trajectory(
    q: np.ndarray,
    qdot: np.ndarray,
    robot_config: RobotConfig,
) -> dict[str, Any]:
    """Validate retargeted trajectory for joint limits and velocity limits.

    Args:
        q: (T, num_dofs) joint positions.
        qdot: (T, num_dofs) joint velocities.
        robot_config: Robot configuration.

    Returns:
        Validation report dict with keys valid, warnings, errors.
    """
    errors, is_valid = _check_joint_limits(q, robot_config)
    warnings = _check_velocity_limits(qdot, robot_config)
    warnings += _check_discontinuities(q, robot_config)
    return {"valid": is_valid, "warnings": warnings, "errors": errors}


def _add_io_args(parser: argparse.ArgumentParser) -> None:
    """Add I/O positional arguments to the parser.

    Args:
        parser: ArgumentParser to extend.
    """
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


def _add_algo_args(parser: argparse.ArgumentParser) -> None:
    """Add algorithm/tuning arguments to the parser.

    Args:
        parser: ArgumentParser to extend.
    """
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


def _build_retarget_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser for retarget_to_sim."""
    parser = argparse.ArgumentParser(
        description="Retarget human poses to robot joint space",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_io_args(parser)
    _add_algo_args(parser)
    return parser


def _load_pose_file(pose_file: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Load skeleton, club_head, and timestamps from a .npz pose file.

    Args:
        pose_file: Path to the .npz file.

    Returns:
        Tuple of (skeleton, club_head, timestamps).
    """
    data = np.load(pose_file)
    return data["skeleton"], data["club_head"], data["timestamps"]


def _log_file_validation(filename: str, validation: dict[str, Any]) -> None:
    """Log validation status, errors, and warnings for a file.

    Args:
        filename: Name of the pose file.
        validation: Validation report dict.
    """
    status = "+" if validation["valid"] else "x"
    logger.info("  %s %s", status, filename)
    for error in validation["errors"]:
        logger.info("      ERROR: %s", error)
    for warning in validation["warnings"][:2]:
        logger.info("      WARNING: %s", warning)


def _retarget_one_file(
    pose_file: Path,
    retargeter: "PoseRetargeter",
    robot_config: "RobotConfig",
    output_dir: Path,
) -> dict[str, Any]:
    """Retarget, validate, and save a single pose .npz file.

    Args:
        pose_file: Path to input .npz file.
        retargeter: Initialised PoseRetargeter instance.
        robot_config: Robot configuration for validation.
        output_dir: Directory to write the retargeted .npz output.

    Returns:
        Report dict with keys: file, valid, warnings, errors.
    """
    skeleton, club_head, timestamps = _load_pose_file(pose_file)
    result = retargeter.retarget(skeleton, club_head, timestamps)
    validation = validate_trajectory(result["q"], result["qdot"], robot_config)
    np.savez(output_dir / pose_file.name, **result)
    _log_file_validation(pose_file.name, validation)
    return {
        "file": pose_file.name,
        "valid": validation["valid"],
        "warnings": validation["warnings"],
        "errors": validation["errors"],
    }


def _save_retarget_report(all_reports: list[dict], output_dir: Path) -> None:
    """Persist the retargeting summary report to JSON and log totals.

    Args:
        all_reports: List of per-file report dicts.
        output_dir: Directory to write retargeting_report.json.
    """
    report_file = output_dir / "retargeting_report.json"
    with open(report_file, "w") as f:
        json.dump({"demos": all_reports}, f, indent=2)

    num_valid = sum(1 for r in all_reports if r["valid"])
    logger.info("\n+ Retargeting complete")
    logger.info("  Valid demos: %d/%d", num_valid, len(all_reports))
    logger.info("  Output: %s", output_dir)
    logger.info("  Report: %s", report_file)


def main() -> None:
    args = _build_retarget_parser().parse_args()

    robot_config = RobotConfig(args.robot_config)
    logger.info("Loaded robot config: %s", robot_config.name)
    logger.info("  DOFs: %d", robot_config.num_dofs)
    logger.info("  DOF names: %s", robot_config.dof_names)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    input_dir = Path(args.input_dir)
    pose_files = sorted(input_dir.glob("*.npz"))

    if not pose_files:
        logger.info("No .npz files found in %s", input_dir)
        return

    logger.info("Found %d pose files", len(pose_files))
    retargeter = PoseRetargeter(
        robot_config=robot_config,
        ik_solver=args.ik_solver,
        smooth_window=args.smooth_window,
    )

    all_reports = []
    for pose_file in tqdm(pose_files, desc="Retargeting"):
        try:
            report = _retarget_one_file(pose_file, retargeter, robot_config, output_dir)
        except (OSError, ValueError, KeyError, RuntimeError) as e:
            logger.info("  x %s: %s", pose_file.name, e)
            report = {"file": pose_file.name, "valid": False, "errors": [str(e)]}
        all_reports.append(report)

    _save_retarget_report(all_reports, output_dir)


if __name__ == "__main__":
    main()
