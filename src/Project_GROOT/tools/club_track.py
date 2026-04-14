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


# MediaPipe wrist landmark indices
_MP_LEFT_WRIST = 15
_MP_RIGHT_WRIST = 16


def _compute_grip_and_direction(skeleton: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Return (club_grip, wrist_dir_unit) from skeleton wrist keypoints."""
    left_wrist = skeleton[:, _MP_LEFT_WRIST, :]
    right_wrist = skeleton[:, _MP_RIGHT_WRIST, :]
    club_grip = (left_wrist + right_wrist) / 2
    wrist_dir = right_wrist - left_wrist
    norm = np.clip(np.linalg.norm(wrist_dir, axis=1, keepdims=True), 1e-6, None)
    return club_grip, wrist_dir / norm


def _compute_club_face(wrist_dir_unit: np.ndarray) -> np.ndarray:
    """Return normalised club-face normals perpendicular to wrist direction."""
    vertical = np.array([0, 1, 0])
    club_face = np.cross(wrist_dir_unit, vertical)
    face_norm = np.clip(np.linalg.norm(club_face, axis=1, keepdims=True), 1e-6, None)
    return club_face / face_norm


def _merge_club_arrays(original_data: Any, updates: dict) -> dict:
    """Return a new data dict combining original_data keys with updates."""
    merged = {key: original_data[key] for key in original_data.keys()}
    merged.update(updates)
    return merged


def _save_pose_with_club(
    original_data: Any,
    club_grip: np.ndarray,
    club_head: np.ndarray,
    club_face: np.ndarray,
    club_speed: np.ndarray,
    club_path: np.ndarray,
    output_file: str,
) -> None:
    """Save pose data merged with club-tracking arrays to output_file."""
    new_data = _merge_club_arrays(
        original_data,
        {
            "club_grip": club_grip,
            "club_head": club_head,
            "club_face": club_face,
            "club_speed": club_speed,
            "club_path": club_path,
        },
    )
    np.savez(output_file, **new_data)


def _process_one_video(
    tracker: "ClubTracker",
    video_entry: dict,
    pose_dir: Path,
    output_dir: Path,
    use_video_path: bool,
) -> dict | None:
    """Track clubs for one video entry; return stats dict or None on error."""
    video_id = video_entry["id"]
    pose_file = pose_dir / f"{video_id}.npz"
    if not pose_file.exists():
        logger.info(f"Warning: Pose file not found: {pose_file}")
        return None
    output_file = output_dir / f"{video_id}.npz"
    try:
        video_path = video_entry.get("video_path") if use_video_path else None
        stats = tracker.add_club_to_pose_file(
            pose_file=str(pose_file),
            output_file=str(output_file),
            video_path=video_path,
        )
        logger.info(f"{video_id}: max speed = {stats['max_clubhead_speed']:.1f} m/s")
        return {"video_id": video_id, "golfer": video_entry["golfer"], **stats}
    except (OSError, ValueError, KeyError, RuntimeError) as e:
        logger.info(f"Error processing {video_id}: {e}")
        return None


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
        """Track club trajectory; returns (club_grip, club_head, club_face)."""
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
        """Baseline: fit line through hands, extend to estimate clubhead."""
        if not (len(skeleton) > 0):
            raise ValueError("Skeleton must contain frames")
        club_grip, wrist_dir_unit = _compute_grip_and_direction(skeleton)
        club_head = club_grip + wrist_dir_unit * self.club_length
        club_face = _compute_club_face(wrist_dir_unit)
        return club_grip, club_head, club_face

    def _track_optical_flow(
        self,
        skeleton: np.ndarray,
        confidence: np.ndarray,
        video_path: str,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Track clubhead using optical flow (future implementation)."""
        raise NotImplementedError("Optical flow tracking coming soon")

    def add_club_to_pose_file(
        self,
        pose_file: str,
        output_file: str,
        video_path: str | None = None,
    ) -> dict[str, float]:
        """Add club tracking data to existing pose .npz file."""
        data = np.load(pose_file)
        club_grip, club_head, club_face = self.track(
            data["skeleton"], data["skeleton_confidence"], video_path
        )
        club_speed = self._compute_clubhead_speed(club_head, data["timestamps"])
        club_path = self._compute_club_path(club_head)
        _save_pose_with_club(
            data, club_grip, club_head, club_face, club_speed, club_path, output_file
        )
        return {
            "max_clubhead_speed": float(club_speed.max()),
            "avg_clubhead_speed": float(club_speed.mean()),
            "total_path_length": float(club_path[-1]),
        }

    def _compute_clubhead_speed(
        self, club_head: np.ndarray, timestamps: np.ndarray
    ) -> np.ndarray:
        """Return (T,) instantaneous speed in m/s from club_head positions."""
        if not (len(club_head) > 0):
            raise ValueError("Club head data must contain frames")
        dt = np.clip(np.diff(timestamps), 1e-6, None)
        distance = np.linalg.norm(np.diff(club_head, axis=0), axis=1)
        return np.concatenate([[0], distance / dt])

    def _compute_club_path(self, club_head: np.ndarray) -> np.ndarray:
        """Return (T,) cumulative distance traveled by club head."""
        distance = np.linalg.norm(np.diff(club_head, axis=0), axis=1)
        return np.concatenate([[0], np.cumsum(distance)])


def _add_club_track_required_args(parser: argparse.ArgumentParser) -> None:
    """Add required arguments to the club_track parser."""
    parser.add_argument(
        "--manifest", type=str, required=True, help="Video manifest JSON"
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


def _add_club_track_optional_args(parser: argparse.ArgumentParser) -> None:
    """Add optional arguments to the club_track parser."""
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


def _build_club_track_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser for club_track."""
    parser = argparse.ArgumentParser(
        description="Track golf club trajectory from pose data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    _add_club_track_required_args(parser)
    _add_club_track_optional_args(parser)
    return parser


def _track_videos(
    tracker: ClubTracker,
    videos: list[dict],
    pose_dir: Path,
    output_dir: Path,
    use_video_path: bool,
) -> list[dict]:
    """Process each video entry and return collected club tracking stats."""
    all_stats = []
    for video_entry in tqdm(videos, desc="Tracking clubs"):
        stats = _process_one_video(
            tracker, video_entry, pose_dir, output_dir, use_video_path
        )
        if stats is not None:
            all_stats.append(stats)
    return all_stats


def _save_and_summarize(all_stats: list[dict], output_dir: Path) -> None:
    """Save tracking stats JSON and log a summary."""
    stats_file = output_dir / "club_tracking_stats.json"
    with open(stats_file, "w") as f:
        json.dump({"videos": all_stats}, f, indent=2)
    if all_stats:
        max_speeds = [s["max_clubhead_speed"] for s in all_stats]
        logger.info(f"\n✓ Processed {len(all_stats)} videos")
        logger.info(
            "  Clubhead speed range: %.1f - %.1f m/s", min(max_speeds), max(max_speeds)
        )
        logger.info(f"  Mean max speed: {np.mean(max_speeds):.1f} m/s")
        logger.info(f"  Stats saved to {stats_file}")


def main() -> None:
    args = _build_club_track_parser().parse_args()

    with open(args.manifest) as f:
        manifest = json.load(f)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    tracker = ClubTracker(method=args.method, club_length=args.club_length)
    all_stats = _track_videos(
        tracker=tracker,
        videos=manifest["videos"],
        pose_dir=Path(args.pose_dir),
        output_dir=output_dir,
        use_video_path=(args.method == "optical_flow"),
    )
    _save_and_summarize(all_stats, output_dir)

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
