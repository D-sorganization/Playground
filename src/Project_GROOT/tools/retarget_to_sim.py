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

from Project_GROOT.tools.retarget_config import RobotConfig
from Project_GROOT.tools.retarget_ik import PoseRetargeter, validate_trajectory

try:
    from tqdm import tqdm
except ImportError:

    def tqdm(x, **kwargs) -> Any:
        return x


logger = logging.getLogger(__name__)


def _add_io_args(parser: argparse.ArgumentParser) -> None:
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
    parser = argparse.ArgumentParser(
        description="Retarget human poses to robot joint space",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_io_args(parser)
    _add_algo_args(parser)
    return parser


def _load_pose_file(pose_file: Path) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    data = np.load(pose_file)
    return data["skeleton"], data["club_head"], data["timestamps"]


def _log_file_validation(filename: str, validation: dict[str, Any]) -> None:
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
