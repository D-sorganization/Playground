#!/usr/bin/env python3
"""
Pose Conversion Tool for Project GROOT

Extracts 3D skeleton poses from golf swing videos using various
pose estimation backends.

Supported backends:
- mediapipe: Fast, CPU-friendly, good for prototyping
- mmpose: More accurate, requires GPU
- openpose: Classic, GPU accelerated

Usage:
    python pose_convert.py --manifest data/manifest.json \
        --output-dir data/processed_pose --pose-backend mediapipe --visualize
        --pose-backend mediapipe --visualize
"""

import argparse
import json
import logging
from pathlib import Path

from Project_GROOT.tools.pose_converter import PoseConverter

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Extract poses from golf swing videos",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument(
        "--manifest",
        type=str,
        required=True,
        help="Input manifest JSON from video_ingest.py",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="data/processed_pose",
        help="Output directory for pose .npz files",
    )
    parser.add_argument(
        "--pose-backend",
        type=str,
        default="mediapipe",
        choices=["mediapipe", "mmpose"],
        help="Pose estimation backend (default: mediapipe)",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=0.5,
        help="Minimum confidence threshold (default: 0.5)",
    )
    parser.add_argument(
        "--visualize",
        action="store_true",
        help="Show pose visualization while processing",
    )
    parser.add_argument(
        "--config",
        type=str,
        help="Config file for MMPose (required for mmpose backend)",
    )
    parser.add_argument(
        "--checkpoint",
        type=str,
        help="Checkpoint file for MMPose (required for mmpose backend)",
    )

    args = parser.parse_args()

    # Load manifest
    with open(args.manifest) as f:
        manifest = json.load(f)

    videos = manifest["videos"]
    logger.info(f"Loaded manifest with {len(videos)} videos")

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Initialize converter
    converter = PoseConverter(
        pose_backend=args.pose_backend,
        confidence_threshold=args.confidence_threshold,
        visualize=args.visualize,
    )

    # Process each video
    all_stats = []
    for video_entry in videos:
        video_id = video_entry["id"]
        output_path = output_dir / f"{video_id}.npz"

        logger.info(f"\nProcessing: {video_id}")

        try:
            stats = converter.process_video(
                video_path=video_entry["video_path"],
                start_frame=video_entry["start_frame"],
                end_frame=video_entry["end_frame"],
                output_path=str(output_path),
            )

            all_stats.append({**video_entry, **stats})

            logger.info(
                f"  ✓ Valid frames: {stats['valid_frames']}/{stats['total_frames']}"
            )
            logger.info(f"  ✓ Avg confidence: {stats['avg_confidence']:.3f}")

        except (OSError, ValueError, KeyError, RuntimeError) as e:
            logger.info(f"  ✗ Error: {e}")
            continue

    # Save processing statistics
    stats_path = output_dir / "processing_stats.json"
    with open(stats_path, "w") as f:
        json.dump({"videos": all_stats}, f, indent=2)

    logger.info(f"\n✓ Processing complete. Stats saved to {stats_path}")
    logger.info(f"  Total videos processed: {len(all_stats)}/{len(videos)}")


if __name__ == "__main__":
    main()
