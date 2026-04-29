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

from typing import Any

import numpy as np

try:
    import yaml
except ImportError:  # pragma: no cover - exercised implicitly in CI import smoke tests
    yaml = None

try:
    from scipy.interpolate import interp1d
    from scipy.ndimage import gaussian_filter1d
except ImportError:
    gaussian_filter1d = None
    interp1d = None

from Project_GROOT.tools.retarget_config import RobotConfig
from Project_GROOT.tools.retarget_math import (
    _check_discontinuities,
    _check_joint_limits,
    _check_velocity_limits,
    _extract_arm_joints,
    _fill_left_arm_dofs,
    _fill_right_arm_dofs,
    _fill_torso_dofs,
    _fit_to_dofs,
)


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
