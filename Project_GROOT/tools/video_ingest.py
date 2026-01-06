#!/usr/bin/env python3
"""
Video Ingestion Tool for Project GROOT

Builds a manifest of golf swing videos with metadata for downstream processing.

Usage:
    # Single video
    python video_ingest.py --input-file data/raw_video/swing.mp4 --output data/manifest.json

    # Directory of videos
    python video_ingest.py --input-dir data/raw_video --output data/manifest.json

    # With metadata
    python video_ingest.py --input-file swing.mp4 --golfer-name "Tiger Woods" \
        --video-source youtube --start-time 0.5 --end-time 3.5
"""

import argparse
import json
import os
from pathlib import Path
from typing import Dict, List, Optional
import hashlib

try:
    import cv2
except ImportError:
    print("Warning: OpenCV not installed. Install with: pip install opencv-python")
    cv2 = None


class VideoIngester:
    """Ingest golf swing videos and create processing manifest."""

    def __init__(self, output_path: str):
        self.output_path = Path(output_path)
        self.videos: List[Dict] = []

    def add_video(
        self,
        video_path: str,
        golfer_name: str = "Unknown",
        video_source: str = "unknown",
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        swing_type: str = "driver",
        metadata: Optional[Dict] = None,
    ) -> Dict:
        """
        Add a video to the manifest.

        Args:
            video_path: Path to video file
            golfer_name: Name of the golfer
            video_source: Source of video (youtube, local, etc.)
            start_time: Start time in seconds (None = start of video)
            end_time: End time in seconds (None = end of video)
            swing_type: Type of swing (driver, iron, wedge, etc.)
            metadata: Additional metadata dict

        Returns:
            Video entry dict
        """
        video_path = Path(video_path).absolute()

        if not video_path.exists():
            raise FileNotFoundError(f"Video not found: {video_path}")

        # Extract video properties
        props = self._get_video_properties(video_path)

        # Calculate frame indices
        fps = props["fps"]
        total_frames = props["frame_count"]
        duration = props["duration"]

        start_frame = 0 if start_time is None else int(start_time * fps)
        end_frame = total_frames if end_time is None else int(end_time * fps)

        # Clamp to valid range
        start_frame = max(0, min(start_frame, total_frames - 1))
        end_frame = max(start_frame + 1, min(end_frame, total_frames))

        # Generate unique ID
        video_id = self._generate_video_id(video_path, start_frame, end_frame)

        entry = {
            "id": video_id,
            "golfer": golfer_name,
            "video_path": str(video_path),
            "source": video_source,
            "start_frame": start_frame,
            "end_frame": end_frame,
            "fps": fps,
            "duration": (end_frame - start_frame) / fps,
            "swing_type": swing_type,
            "resolution": f"{props['width']}x{props['height']}",
            "metadata": metadata or {},
        }

        self.videos.append(entry)
        print(f"Added: {video_id} ({entry['duration']:.2f}s, {end_frame - start_frame} frames)")

        return entry

    def add_directory(
        self,
        directory: str,
        golfer_name: str = "Unknown",
        video_source: str = "local",
        recursive: bool = False,
        extensions: tuple = (".mp4", ".avi", ".mov", ".MP4", ".AVI", ".MOV"),
    ):
        """
        Add all videos from a directory.

        Args:
            directory: Directory path
            golfer_name: Golfer name for all videos
            video_source: Video source for all videos
            recursive: Search subdirectories
            extensions: Video file extensions to include
        """
        directory = Path(directory)

        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")

        pattern = "**/*" if recursive else "*"
        video_files = []

        for ext in extensions:
            video_files.extend(directory.glob(f"{pattern}{ext}"))

        print(f"Found {len(video_files)} videos in {directory}")

        for video_file in sorted(video_files):
            try:
                self.add_video(
                    video_path=str(video_file),
                    golfer_name=golfer_name,
                    video_source=video_source,
                )
            except Exception as e:
                print(f"Error processing {video_file}: {e}")

    def save(self):
        """Save manifest to JSON file."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)

        manifest = {
            "version": "1.0",
            "num_videos": len(self.videos),
            "videos": self.videos,
        }

        with open(self.output_path, "w") as f:
            json.dump(manifest, f, indent=2)

        print(f"\n✓ Manifest saved: {self.output_path}")
        print(f"  Total videos: {len(self.videos)}")
        print(f"  Total frames: {sum(v['end_frame'] - v['start_frame'] for v in self.videos)}")
        print(f"  Total duration: {sum(v['duration'] for v in self.videos):.2f}s")

    def _get_video_properties(self, video_path: Path) -> Dict:
        """Extract video properties using OpenCV."""
        if cv2 is None:
            # Fallback: return dummy values
            return {
                "fps": 30.0,
                "frame_count": 90,
                "duration": 3.0,
                "width": 1920,
                "height": 1080,
            }

        cap = cv2.VideoCapture(str(video_path))

        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))

        cap.release()

        # Handle edge cases
        if fps <= 0:
            fps = 30.0  # Default
        if frame_count <= 0:
            frame_count = 90  # Default ~3 seconds

        duration = frame_count / fps

        return {
            "fps": fps,
            "frame_count": frame_count,
            "duration": duration,
            "width": width,
            "height": height,
        }

    def _generate_video_id(self, video_path: Path, start_frame: int, end_frame: int) -> str:
        """Generate unique video ID."""
        # Use stem + hash of path + frame range for uniqueness
        stem = video_path.stem
        path_hash = hashlib.md5(str(video_path).encode()).hexdigest()[:8]
        video_id = f"{stem}_{start_frame:06d}_{end_frame:06d}_{path_hash}"
        return video_id


def main():
    parser = argparse.ArgumentParser(
        description="Ingest golf swing videos and create manifest",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument(
        "--input-file",
        type=str,
        help="Single video file path",
    )
    input_group.add_argument(
        "--input-dir",
        type=str,
        help="Directory containing videos",
    )

    # Output
    parser.add_argument(
        "--output",
        type=str,
        default="data/manifest.json",
        help="Output manifest JSON path (default: data/manifest.json)",
    )

    # Metadata
    parser.add_argument(
        "--golfer-name",
        type=str,
        default="Unknown",
        help="Golfer name (default: Unknown)",
    )
    parser.add_argument(
        "--video-source",
        type=str,
        default="unknown",
        help="Video source (youtube, local, etc.) (default: unknown)",
    )
    parser.add_argument(
        "--swing-type",
        type=str,
        default="driver",
        choices=["driver", "iron", "wedge", "putter", "hybrid", "wood"],
        help="Type of swing (default: driver)",
    )

    # Clipping
    parser.add_argument(
        "--start-time",
        type=float,
        help="Start time in seconds (default: start of video)",
    )
    parser.add_argument(
        "--end-time",
        type=float,
        help="End time in seconds (default: end of video)",
    )

    # Directory options
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Search subdirectories when using --input-dir",
    )

    # Processing
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to existing manifest instead of overwriting",
    )

    args = parser.parse_args()

    # Create ingester
    ingester = VideoIngester(args.output)

    # Load existing manifest if appending
    if args.append and Path(args.output).exists():
        with open(args.output) as f:
            existing = json.load(f)
            ingester.videos = existing.get("videos", [])
            print(f"Loaded existing manifest with {len(ingester.videos)} videos")

    # Ingest videos
    if args.input_file:
        ingester.add_video(
            video_path=args.input_file,
            golfer_name=args.golfer_name,
            video_source=args.video_source,
            start_time=args.start_time,
            end_time=args.end_time,
            swing_type=args.swing_type,
        )
    else:
        ingester.add_directory(
            directory=args.input_dir,
            golfer_name=args.golfer_name,
            video_source=args.video_source,
            recursive=args.recursive,
        )

    # Save manifest
    ingester.save()


if __name__ == "__main__":
    main()
