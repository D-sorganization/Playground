#!/usr/bin/env python3
"""
Club Tracking Tool for Project GROOT

Extracts golf club trajectory (grip, head, face) from pose data.

Methods:
- line_fit: Fit line from hands through club (baseline)
- optical_flow: Track club head using optical flow (future)
- ml_detection: ML-based club detection (future)

Usage:
    python club_track.py --manifest data/manifest.json --pose-dir data/processed_pose \
        --output-dir data/processed_pose --method line_fit
"""

import argparse
import json
import logging
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from tqdm import tqdm
except ImportError:

    def tqdm(x, **kwargs) -> Any:
        return x


class ClubTracker:
    """Track golf club trajectory from pose data."""

    def __init__(self, method: str = "line_fit", club_length: float = 1.15):
        """
        Args:
            method: Tracking method (line_fit, optical_flow, ml_detection)
            club_length: Standard club length in meters (driver ~1.15m)
        """
        self.method = method
        self.club_length = club_length

    def track(
        self,
        skeleton: np.ndarray,
        confidence: np.ndarray,
        video_path: str | None = None,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Track club trajectory.

        Args:
            skeleton: (T, num_joints, 3) skeleton keypoints
            confidence: (T, num_joints) keypoint confidences
            video_path: Optional video path for visual tracking

        Returns:
            club_grip: (T, 3) grip position
            club_head: (T, 3) clubhead position
            club_face: (T, 3) clubface normal vector
        """
        if self.method == "line_fit":
            return self._track_line_fit(skeleton, confidence)
        elif self.method == "optical_flow":
            if video_path is None:
                raise ValueError("video_path required for optical_flow method")
            return self._track_optical_flow(skeleton, confidence, video_path)
        else:
            raise ValueError(f"Unknown method: {self.method}")

    def _track_line_fit(
        self,
        skeleton: np.ndarray,
        confidence: np.ndarray,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Baseline: fit line through hands, extend to estimate clubhead.

        Uses both wrists and projects line assuming standard grip.

        Args:
            skeleton: (T, 33, 3) MediaPipe skeleton
            confidence: (T, 33)

        Returns:
            club_grip, club_head, club_face
        """
        if not (len(skeleton) > 0):
            raise ValueError("Skeleton must contain frames")

        # MediaPipe wrist indices
        left_wrist_idx = 15
        right_wrist_idx = 16

        # Extract wrist positions
        left_wrist = skeleton[:, left_wrist_idx, :]  # (T, 3)
        right_wrist = skeleton[:, right_wrist_idx, :]  # (T, 3)

        # Use average of wrists as grip position
        club_grip = (left_wrist + right_wrist) / 2

        # Direction from one wrist to another
        wrist_direction = right_wrist - left_wrist  # (T, 3)

        # Normalize
        wrist_direction_norm = np.linalg.norm(wrist_direction, axis=1, keepdims=True)
        wrist_direction_norm = np.clip(
            wrist_direction_norm, 1e-6, None
        )  # Avoid div by zero
        wrist_direction_unit = wrist_direction / wrist_direction_norm

        # Extend line from grip through hands to estimate clubhead
        # Assume club extends in direction of wrist line
        club_head = club_grip + wrist_direction_unit * self.club_length

        # Club face: perpendicular to shaft direction (simplified)
        # For driver, face is roughly perpendicular to shaft in swing plane
        # Use cross product with vertical axis as approximation
        vertical = np.array([0, 1, 0])  # y-up
        club_face = np.cross(wrist_direction_unit, vertical)

        # Normalize face normals
        face_norm = np.linalg.norm(club_face, axis=1, keepdims=True)
        face_norm = np.clip(face_norm, 1e-6, None)
        club_face = club_face / face_norm

        return club_grip, club_head, club_face

    def _track_optical_flow(
        self,
        skeleton: np.ndarray,
        confidence: np.ndarray,
        video_path: str,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Track clubhead using optical flow (future implementation).

        Would use Lucas-Kanade or similar to track high-contrast clubhead.
        """
        raise NotImplementedError("Optical flow tracking coming soon")

    def add_club_to_pose_file(
        self,
        pose_file: str,
        output_file: str,
        video_path: str | None = None,
    ) -> dict[str, float]:
        """
        Add club tracking data to existing pose .npz file.

        Args:
            pose_file: Input .npz file with skeleton data
            output_file: Output .npz file (can be same as input)
            video_path: Optional video path for visual tracking
        """
        # Load existing pose data
        data = np.load(pose_file)

        skeleton = data["skeleton"]
        confidence = data["skeleton_confidence"]

        # Track club
        club_grip, club_head, club_face = self.track(skeleton, confidence, video_path)

        # Compute additional metrics
        club_speed = self._compute_clubhead_speed(club_head, data["timestamps"])
        club_path = self._compute_club_path(club_head)

        # Create updated data dict
        new_data = {key: data[key] for key in data.keys()}
        new_data.update(
            {
                "club_grip": club_grip,
                "club_head": club_head,
                "club_face": club_face,
                "club_speed": club_speed,
                "club_path": club_path,
            }
        )

        # Save
        np.savez(output_file, **new_data)

        # Return statistics
        max_speed = club_speed.max()
        avg_speed = club_speed.mean()

        return {
            "max_clubhead_speed": float(max_speed),
            "avg_clubhead_speed": float(avg_speed),
            "total_path_length": float(club_path[-1]),
        }

    def _compute_clubhead_speed(
        self, club_head: np.ndarray, timestamps: np.ndarray
    ) -> np.ndarray:
        """
        Compute clubhead speed from trajectory.

        Args:
            club_head: (T, 3) clubhead positions
            timestamps: (T,) frame timestamps

        Returns:
            speed: (T,) instantaneous speed in m/s
        """
        if not (len(club_head) > 0):
            raise ValueError("Club head data must contain frames")

        # Compute displacement
        displacement = np.diff(club_head, axis=0)  # (T-1, 3)
        distance = np.linalg.norm(displacement, axis=1)  # (T-1,)

        # Compute time delta
        dt = np.diff(timestamps)  # (T-1,)
        dt = np.clip(dt, 1e-6, None)  # Avoid division by zero

        # Speed
        speed = distance / dt  # (T-1,)

        # Pad to match original length
        speed = np.concatenate([[0], speed])  # (T,)

        return speed

    def _compute_club_path(self, club_head: np.ndarray) -> np.ndarray:
        """
        Compute cumulative path length.

        Args:
            club_head: (T, 3)

        Returns:
            path_length: (T,) cumulative distance traveled
        """
        displacement = np.diff(club_head, axis=0)
        distance = np.linalg.norm(displacement, axis=1)
        cumulative = np.concatenate([[0], np.cumsum(distance)])
        return cumulative


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Track golf club trajectory from pose data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--manifest",
        type=str,
        required=True,
        help="Video manifest JSON",
    )
    parser.add_argument(
        "--pose-dir",
        type=str,
        required=True,
        help="Directory with pose .npz files from pose_convert.py",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="Output directory (can be same as pose-dir to update in place)",
    )
    parser.add_argument(
        "--method",
        type=str,
        default="line_fit",
        choices=["line_fit", "optical_flow"],
        help="Club tracking method (default: line_fit)",
    )
    parser.add_argument(
        "--club-length",
        type=float,
        default=1.15,
        help="Club length in meters (default: 1.15m for driver)",
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Visualize club tracking (requires matplotlib)",
    )

    args = parser.parse_args()

    # Load manifest
    with open(args.manifest) as f:
        manifest = json.load(f)

    videos = manifest["videos"]
    pose_dir = Path(args.pose_dir)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize tracker
    tracker = ClubTracker(method=args.method, club_length=args.club_length)

    # Process each video
    all_stats = []
    for video_entry in tqdm(videos, desc="Tracking clubs"):
        video_id = video_entry["id"]
        pose_file = pose_dir / f"{video_id}.npz"

        if not pose_file.exists():
            logger.info(f"Warning: Pose file not found: {pose_file}")
            continue

        output_file = output_dir / f"{video_id}.npz"

        try:
            stats = tracker.add_club_to_pose_file(
                pose_file=str(pose_file),
                output_file=str(output_file),
                video_path=(
                    video_entry.get("video_path")
                    if args.method == "optical_flow"
                    else None
                ),
            )

            all_stats.append(
                {
                    "video_id": video_id,
                    "golfer": video_entry["golfer"],
                    **stats,
                }
            )

            logger.info(
                f"{video_id}: max speed = {stats['max_clubhead_speed']:.1f} m/s"
            )

        except (OSError, ValueError, KeyError, RuntimeError) as e:
            logger.info(f"Error processing {video_id}: {e}")
            continue

    # Save statistics
    stats_file = output_dir / "club_tracking_stats.json"
    with open(stats_file, "w") as f:
        json.dump({"videos": all_stats}, f, indent=2)

    # Summary
    if all_stats:
        max_speeds = [s["max_clubhead_speed"] for s in all_stats]
        logger.info(f"\n✓ Processed {len(all_stats)} videos")
        logger.info(
            "  Clubhead speed range: %.1f - %.1f m/s",
            min(max_speeds),
            max(max_speeds),
        )
        logger.info(f"  Mean max speed: {np.mean(max_speeds):.1f} m/s")
        logger.info(f"  Stats saved to {stats_file}")

    # Visualize if requested
    if args.visualize and all_stats:
        visualize_club_stats(all_stats)


def visualize_club_stats(stats: list[dict[str, object]]) -> None:
    """Visualize club tracking statistics."""
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        logger.info("Matplotlib not installed. Skipping visualization.")
        return

    max_speeds = [s["max_clubhead_speed"] for s in stats]
    golfers = [s["golfer"] for s in stats]

    plt.figure(figsize=(10, 6))
    plt.bar(range(len(max_speeds)), max_speeds)
    plt.xlabel("Video Index")
    plt.ylabel("Max Clubhead Speed (m/s)")
    plt.title("Clubhead Speed by Video")
    plt.xticks(range(len(golfers)), [g[:10] for g in golfers], rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig("club_speeds.png")
    logger.info("✓ Visualization saved to club_speeds.png")
    plt.close()


if __name__ == "__main__":
    main()
