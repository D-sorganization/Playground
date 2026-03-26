"""
Golf Swing Environment for Isaac Lab

Custom RL environment for training golf swing skills on a humanoid robot.

This environment:
- Loads a humanoid/upper-body robot with golf club
- Tracks swing trajectory and clubhead speed
- Provides rewards for matching demonstration swing
- Logs key performance metrics

Based on Isaac Lab task template.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import omni.isaac.lab.sim as sim_utils
import torch
from omni.isaac.lab.assets import Articulation, ArticulationCfg
from omni.isaac.lab.envs import DirectRLEnv, DirectRLEnvCfg
from omni.isaac.lab.scene import InteractiveSceneCfg
from omni.isaac.lab.sim import SimulationCfg
from omni.isaac.lab.utils import configclass

if TYPE_CHECKING:
    from omni.isaac.lab.envs import DirectRLEnvCfg


@configclass
class GolfSwingEnvCfg(DirectRLEnvCfg):
    """Configuration for the Golf Swing environment."""

    # Environment settings
    episode_length_s: float = 3.0  # Typical swing duration
    decimation: int = 2  # Control frequency decimation
    action_scale: float = 1.0
    action_space_dim: int = 11  # Upper body DOFs (torso + arms)
    observation_space_dim: int = 44  # q (11) + qdot (11) + target (11) + phase (1) + clubhead (10)

    # Simulation settings
    sim: SimulationCfg = SimulationCfg(
        dt=1 / 120,  # 120 Hz physics
        render_interval=decimation,
        gravity=(0.0, 0.0, -9.81),
        physx=sim_utils.PhysxCfg(
            bounce_threshold_velocity=0.2,
            gpu_max_rigid_contact_count=2**20,
        ),
    )

    # Scene settings
    scene: InteractiveSceneCfg = InteractiveSceneCfg(
        num_envs=256,
        env_spacing=4.0,
        replicate_physics=True,
    )

    # Robot configuration
    robot_cfg: ArticulationCfg = None  # Will be set from config file

    # Reward weights
    reward_weights: dict = {
        "tracking": 1.0,  # Match joint trajectory
        "clubhead_speed": 0.5,  # Maximize clubhead speed
        "clubhead_path": 0.3,  # Match clubhead trajectory
        "smoothness": 0.1,  # Penalize jerky motions
        "joint_limits": -0.5,  # Penalize joint limit violations
    }

    # Target clubhead speed (m/s)
    target_clubhead_speed: float = 40.0


class GolfSwingEnv(DirectRLEnv):
    """Golf swing environment for robot learning."""

    cfg: GolfSwingEnvCfg

    def __init__(self, cfg: GolfSwingEnvCfg, render_mode: str | None = None, **kwargs):
        super().__init__(cfg, render_mode, **kwargs)

        # Buffers for tracking
        self.joint_pos_target = torch.zeros(
            self.num_envs, self.cfg.action_space_dim, device=self.device
        )
        self.joint_vel_target = torch.zeros_like(self.joint_pos_target)

        self.clubhead_pos = torch.zeros(self.num_envs, 3, device=self.device)
        self.clubhead_vel = torch.zeros(self.num_envs, 3, device=self.device)
        self.clubhead_pos_target = torch.zeros(self.num_envs, 3, device=self.device)

        self.swing_phase = torch.zeros(self.num_envs, device=self.device)  # 0-1 normalized time

        # Metrics tracking
        self.max_clubhead_speed = torch.zeros(self.num_envs, device=self.device)
        self.episode_swing_count = torch.zeros(self.num_envs, device=self.device)

    def _setup_scene(self):
        """Setup the scene with robot and environment objects."""
        # Create robot articulation
        self.robot = Articulation(self.cfg.robot_cfg)
        self.scene.articulations["robot"] = self.robot

        # Add ground plane
        cfg = sim_utils.GroundPlaneCfg()
        cfg.func("/World/defaultGroundPlane", cfg)

        # Clone environments
        self.scene.clone_environments(copy_from_source=False)

        # Add lights
        cfg = sim_utils.DomeLightCfg(intensity=2000.0, color=(0.75, 0.75, 0.75))
        cfg.func("/World/Light", cfg)

    def _pre_physics_step(self, actions: torch.Tensor):
        """Process actions before physics step."""
        # Scale actions
        self.actions = actions * self.cfg.action_scale

        # Set joint position targets (PD control)
        self.joint_pos_target = self.robot.data.default_joint_pos + self.actions

    def _apply_action(self):
        """Apply actions to the robot."""
        # Apply joint position targets
        self.robot.set_joint_position_target(self.joint_pos_target)

    def _get_observations(self) -> dict:
        """Compute observations."""
        # Current joint states
        joint_pos = self.robot.data.joint_pos[:, : self.cfg.action_space_dim]
        joint_vel = self.robot.data.joint_vel[:, : self.cfg.action_space_dim]

        # Target joint states (from demonstration)
        joint_pos_target = self.joint_pos_target

        # Clubhead state
        clubhead_pos = self.clubhead_pos
        clubhead_vel = self.clubhead_vel
        clubhead_pos_target = self.clubhead_pos_target
        clubhead_speed = torch.norm(clubhead_vel, dim=1, keepdim=True)

        # Swing phase (normalized time in episode)
        phase = self.swing_phase.unsqueeze(1)

        # Concatenate observations
        obs = torch.cat(
            [
                joint_pos,
                joint_vel,
                joint_pos_target,
                phase,
                clubhead_pos,
                clubhead_vel,
                clubhead_pos_target,
                clubhead_speed,
            ],
            dim=1,
        )

        return {"policy": obs}

    def _get_rewards(self) -> torch.Tensor:
        """Compute rewards."""
        total_reward = torch.zeros(self.num_envs, device=self.device)

        # 1. Tracking reward: match joint trajectory
        joint_pos = self.robot.data.joint_pos[:, : self.cfg.action_space_dim]
        tracking_error = torch.sum((joint_pos - self.joint_pos_target) ** 2, dim=1)
        tracking_reward = torch.exp(-tracking_error / 0.25)  # Gaussian reward
        total_reward += self.cfg.reward_weights["tracking"] * tracking_reward

        # 2. Clubhead speed reward
        clubhead_speed = torch.norm(self.clubhead_vel, dim=1)
        speed_reward = torch.clamp(clubhead_speed / self.cfg.target_clubhead_speed, 0, 1)
        total_reward += self.cfg.reward_weights["clubhead_speed"] * speed_reward

        # 3. Clubhead path reward: match target trajectory
        path_error = torch.norm(self.clubhead_pos - self.clubhead_pos_target, dim=1)
        path_reward = torch.exp(-path_error / 0.5)
        total_reward += self.cfg.reward_weights["clubhead_path"] * path_reward

        # 4. Smoothness reward: penalize high accelerations
        joint_vel = self.robot.data.joint_vel[:, : self.cfg.action_space_dim]
        smoothness_penalty = torch.sum(joint_vel**2, dim=1) / self.cfg.action_space_dim
        total_reward += self.cfg.reward_weights["smoothness"] * torch.exp(-smoothness_penalty)

        # 5. Joint limit penalty
        joint_limits_penalty = self._compute_joint_limits_penalty()
        total_reward += self.cfg.reward_weights["joint_limits"] * joint_limits_penalty

        return total_reward

    def _get_dones(self) -> tuple[torch.Tensor, torch.Tensor]:
        """Compute done flags."""
        # Time-based termination
        time_out = self.episode_length_buf >= self.max_episode_length - 1

        # Early termination conditions
        # 1. Robot fell over (root z-position too low)
        root_pos = self.robot.data.root_pos_w[:, 2]
        fallen = root_pos < 0.5

        # 2. Extreme joint limit violations
        joint_pos = self.robot.data.joint_pos
        joint_limits_violated = torch.any(
            (joint_pos < self.robot.data.soft_joint_pos_limits[0])
            | (joint_pos > self.robot.data.soft_joint_pos_limits[1]),
            dim=1,
        )

        # Combine termination conditions
        terminated = fallen | joint_limits_violated
        truncated = time_out

        return terminated, truncated

    def _reset_idx(self, env_ids: torch.Tensor | None):
        """Reset specified environments."""
        if env_ids is None:
            env_ids = torch.arange(self.num_envs, device=self.device)

        # Reset robot to default pose
        default_joint_pos = self.robot.data.default_joint_pos[env_ids]
        default_joint_vel = torch.zeros_like(default_joint_pos)

        self.robot.set_joint_position_target(default_joint_pos, env_ids=env_ids)
        self.robot.write_joint_state_to_sim(default_joint_pos, default_joint_vel, env_ids=env_ids)

        # Reset tracking targets (will be set from demonstration)
        self.joint_pos_target[env_ids] = default_joint_pos

        # Reset swing phase
        self.swing_phase[env_ids] = 0.0

        # Reset metrics
        self.max_clubhead_speed[env_ids] = 0.0

        # Reset buffers
        super()._reset_idx(env_ids)

    def _update_clubhead_state(self):
        """Update clubhead position and velocity from robot state."""
        # Get end-effector (right hand) link state
        # This assumes the club is attached to the right hand
        # DEFERRED: Replace with actual end-effector link index from URDF
        ee_link_idx = -1  # Placeholder

        # For now, use right wrist position as proxy
        # In real implementation, use forward kinematics to club tip
        right_wrist_pos = self.robot.data.body_pos_w[:, ee_link_idx]  # (num_envs, 3)
        right_wrist_vel = self.robot.data.body_vel_w[:, ee_link_idx]  # (num_envs, 6)

        self.clubhead_pos = right_wrist_pos
        self.clubhead_vel = right_wrist_vel[:, :3]  # Linear velocity only

        # Track maximum speed
        current_speed = torch.norm(self.clubhead_vel, dim=1)
        self.max_clubhead_speed = torch.maximum(self.max_clubhead_speed, current_speed)

    def _compute_joint_limits_penalty(self) -> torch.Tensor:
        """Compute penalty for being near joint limits."""
        joint_pos = self.robot.data.joint_pos
        lower_limits = self.robot.data.soft_joint_pos_limits[0]
        upper_limits = self.robot.data.soft_joint_pos_limits[1]

        # Distance to limits (normalized)
        range_size = upper_limits - lower_limits
        dist_to_lower = (joint_pos - lower_limits) / range_size
        dist_to_upper = (upper_limits - joint_pos) / range_size

        # Penalty when within 10% of limits
        penalty = torch.sum(
            torch.clamp(0.1 - dist_to_lower, min=0) + torch.clamp(0.1 - dist_to_upper, min=0),
            dim=1,
        )

        return -penalty

    def step(self, actions: torch.Tensor) -> tuple:
        """Execute one step."""
        # Update swing phase
        self.swing_phase = self.episode_length_buf.float() / self.max_episode_length

        # Update clubhead state
        self._update_clubhead_state()

        # Normal step
        return super().step(actions)


# Register environment
import gymnasium as gym  # noqa: E402

gym.register(
    id="GolfSwing-v0",
    entry_point="sim.golf_swing_env:GolfSwingEnv",
    disable_env_checker=True,
)
