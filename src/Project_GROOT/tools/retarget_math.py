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

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from Project_GROOT.tools.retarget_config import RobotConfig

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
