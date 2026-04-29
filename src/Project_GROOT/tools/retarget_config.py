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
