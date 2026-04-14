#!/usr/bin/env python3
"""
Video Ingestion Tool for Project GROOT

Builds a manifest of golf swing videos with metadata for downstream processing.

Usage:
    # Single video
    python video_ingest.py --input-file data/raw_video/swing.mp4 \\
        --output data/manifest.json

    # Directory of videos
    python video_ingest.py --input-dir data/raw_video --output data/manifest.json

    # With metadata
    python video_ingest.py --input-file swing.mp4 --golfer-name "Tiger Woods" \
        --video-source youtube --start-time 0.5 --end-time 3.5
"""

import argparse
import hashlib
import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

try:
    import cv2
except ImportError:
    logger.info(
        "Warning: OpenCV not installed. Install with: pip install opencv-python"
    )
    cv2 = None


def _validate_time_range(start_time: float | None, end_time: float | None) -> None:
    """DbC: assert start/end time arguments are valid (non-negative, ordered)."""
    if start_time is not None:
        msg = "Contract violation: start_time must be non-negative, got " + repr(
            start_time
        )
        assert isinstance(start_time, (int, float)) and start_time >= 0.0, msg
    if end_time is not None:
        msg = "Contract violation: end_time must be positive, got " + repr(end_time)
        assert isinstance(end_time, (int, float)) and end_time > 0.0, msg
    if start_time is not None and end_time is not None:
        msg = (
            f"Contract violation: end_time ({end_time}) must be greater than"
            f" start_time ({start_time})"
        )
        assert end_time > start_time, msg


def _clamp_frame_range(
    start_time: float | None,
    end_time: float | None,
    fps: float,
    total_frames: int,
) -> tuple[int, int]:
    """Convert time bounds to clamped (start_frame, end_frame) indices."""
    start_frame = 0 if start_time is None else int(start_time * fps)
    end_frame = total_frames if end_time is None else int(end_time * fps)
    start_frame = max(0, min(start_frame, total_frames - 1))
    end_frame = max(start_frame + 1, min(end_frame, total_frames))
    return start_frame, end_frame


def _generate_video_id(video_path: Path, start_frame: int, end_frame: int) -> str:
    """Return a unique ID string from path stem, frame range, and path hash."""
    stem = video_path.stem
    path_hash = hashlib.md5(str(video_path).encode()).hexdigest()[:8]  # nosec B324
    return f"{stem}_{start_frame:06d}_{end_frame:06d}_{path_hash}"


def _build_entry(
    video_path: Path,
    golfer_name: str,
    video_source: str,
    swing_type: str,
    props: dict,
    start_frame: int,
    end_frame: int,
    metadata: dict | None,
) -> dict:
    """Build and return a video manifest entry dict."""
    fps = props["fps"]
    video_id = _generate_video_id(video_path, start_frame, end_frame)
    return {
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


def _read_raw_cv2_props(cap: "cv2.VideoCapture") -> tuple[float, int, int, int]:
    """Read raw (fps, frame_count, width, height) from an open VideoCapture."""
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    cap.release()
    return fps, frame_count, width, height


def _read_cv2_properties(video_path: Path) -> dict:
    """Read video properties via OpenCV; raises ValueError if unopenable."""
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        raise ValueError(f"Cannot open video: {video_path}")
    fps, frame_count, width, height = _read_raw_cv2_props(cap)
    if fps <= 0:
        fps = 30.0
    if frame_count <= 0:
        frame_count = 90
    assert fps > 0, f"Contract violation: fps must be positive, got {fps}"
    msg = f"Contract violation: frame_count must be positive, got {frame_count}"
    assert frame_count > 0, msg
    return {
        "fps": fps,
        "frame_count": frame_count,
        "duration": frame_count / fps,
        "width": width,
        "height": height,
    }


def _collect_video_files(
    directory: Path,
    recursive: bool,
    extensions: tuple[str, ...],
) -> list[Path]:
    """Return sorted list of video files in directory matching extensions."""
    pattern = "**/*" if recursive else "*"
    video_files: list[Path] = []
    for ext in extensions:
        video_files.extend(directory.glob(f"{pattern}{ext}"))
    return sorted(video_files)


class VideoIngester:
    """Ingest golf swing videos and create processing manifest."""

    def __init__(self, output_path: str):
        self.output_path = Path(output_path)
        self.videos: list[dict] = []

    def _build_video_entry(
        self,
        video_path: Path,
        golfer_name: str,
        video_source: str,
        swing_type: str,
        start_time: float | None,
        end_time: float | None,
        metadata: dict | None,
    ) -> dict:
        """Validate times, compute frames, and build the manifest entry dict."""
        _validate_time_range(start_time, end_time)
        props = self._get_video_properties(video_path)
        start_frame, end_frame = _clamp_frame_range(
            start_time, end_time, props["fps"], props["frame_count"]
        )
        return _build_entry(
            video_path,
            golfer_name,
            video_source,
            swing_type,
            props,
            start_frame,
            end_frame,
            metadata,
        )

    def add_video(
        self,
        video_path: str,
        golfer_name: str = "Unknown",
        video_source: str = "unknown",
        start_time: float | None = None,
        end_time: float | None = None,
        swing_type: str = "driver",
        metadata: dict | None = None,
    ) -> dict:
        """Add a video to the manifest and return the entry dict."""
        vpath = Path(video_path).absolute()
        if not vpath.exists():
            raise FileNotFoundError(f"Video not found: {vpath}")
        entry = self._build_video_entry(
            vpath, golfer_name, video_source, swing_type, start_time, end_time, metadata
        )
        self.videos.append(entry)
        n_frames = entry["end_frame"] - entry["start_frame"]
        logger.info(
            "Added: %s (%.2fs, %d frames)", entry["id"], entry["duration"], n_frames
        )
        return entry

    def add_directory(
        self,
        directory: str,
        golfer_name: str = "Unknown",
        video_source: str = "local",
        recursive: bool = False,
        extensions: tuple[str, ...] = (".mp4", ".avi", ".mov", ".MP4", ".AVI", ".MOV"),
    ) -> None:
        """Add all videos from directory matching extensions."""
        directory = Path(directory)
        if not directory.exists():
            raise FileNotFoundError(f"Directory not found: {directory}")
        video_files = _collect_video_files(directory, recursive, extensions)
        logger.info(f"Found {len(video_files)} videos in {directory}")
        for video_file in video_files:
            try:
                self.add_video(
                    video_path=str(video_file),
                    golfer_name=golfer_name,
                    video_source=video_source,
                )
            except (OSError, ValueError, RuntimeError) as e:
                logger.info(f"Error processing {video_file}: {e}")

    def save(self) -> None:
        """Save manifest to JSON file."""
        self.output_path.parent.mkdir(parents=True, exist_ok=True)
        manifest = {
            "version": "1.0",
            "num_videos": len(self.videos),
            "videos": self.videos,
        }
        with open(self.output_path, "w") as f:
            json.dump(manifest, f, indent=2)
        logger.info(f"\n✓ Manifest saved: {self.output_path}")
        logger.info(f"  Total videos: {len(self.videos)}")
        total_frames = sum(v["end_frame"] - v["start_frame"] for v in self.videos)
        logger.info("  Total frames: %d", total_frames)
        logger.info(f"  Total duration: {sum(v['duration'] for v in self.videos):.2f}s")

    def _get_video_properties(self, video_path: Path) -> dict:
        """Extract video properties using OpenCV (or return fallback defaults)."""
        if cv2 is None:
            return {
                "fps": 30.0,
                "frame_count": 90,
                "duration": 3.0,
                "width": 1920,
                "height": 1080,
            }
        return _read_cv2_properties(video_path)


def _add_input_args(parser: argparse.ArgumentParser) -> None:
    """Add input source arguments to the parser."""
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("--input-file", type=str, help="Single video file path")
    input_group.add_argument(
        "--input-dir", type=str, help="Directory containing videos"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/manifest.json",
        help="Output manifest JSON path (default: data/manifest.json)",
    )


def _add_metadata_args(parser: argparse.ArgumentParser) -> None:
    """Add golfer/source metadata arguments to the parser."""
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


def _add_clip_args(parser: argparse.ArgumentParser) -> None:
    """Add clip/trim and mode arguments to the parser."""
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
    parser.add_argument(
        "--recursive",
        action="store_true",
        help="Search subdirectories when using --input-dir",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append to existing manifest instead of overwriting",
    )


def _build_ingest_parser() -> argparse.ArgumentParser:
    """Build and return the CLI argument parser for video_ingest."""
    parser = argparse.ArgumentParser(
        description="Ingest golf swing videos and create manifest",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    _add_input_args(parser)
    _add_metadata_args(parser)
    _add_clip_args(parser)
    return parser


def _load_existing_manifest(ingester: VideoIngester, output_path: str) -> None:
    """Load existing manifest videos into the ingester if the file exists."""
    if Path(output_path).exists():
        with open(output_path) as f:
            existing = json.load(f)
        ingester.videos = existing.get("videos", [])
        logger.info(f"Loaded existing manifest with {len(ingester.videos)} videos")


def _ingest_from_args(ingester: VideoIngester, args: argparse.Namespace) -> None:
    """Add video(s) to the ingester based on parsed CLI args."""
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


def main() -> None:
    args = _build_ingest_parser().parse_args()
    ingester = VideoIngester(args.output)
    if args.append:
        _load_existing_manifest(ingester, args.output)
    _ingest_from_args(ingester, args)
    ingester.save()


if __name__ == "__main__":
    main()
