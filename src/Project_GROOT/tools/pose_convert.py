import logging
from typing import Any

from numba import jit

logger = logging.getLogger(__name__)

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
import warnings
from pathlib import Path

import numpy as np

try:
    import cv2
except ImportError:
    cv2 = None
    logger.info("Warning: OpenCV not installed")

try:
    from tqdm import tqdm
except ImportError:

    def tqdm(x, **kwargs) -> Any:
        return x  # Fallback


class PoseExtractor:
    """Base class for pose extraction."""

    def __init__(self, confidence_threshold: float = 0.5):
        self.confidence_threshold = confidence_threshold

    def extract(self, frame: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """
        Extract pose from a single frame.

        Args:
            frame: RGB image (H, W, 3)

        Returns:
            keypoints: (num_joints, 3) xyz positions
            confidence: (num_joints,) confidence scores
        """
        raise NotImplementedError

    def get_keypoint_names(self) -> list[str]:
        """Return list of keypoint names in order."""
        raise NotImplementedError


class MediaPipePoseExtractor(PoseExtractor):
    """MediaPipe Pose extractor."""

    def __init__(self, confidence_threshold: float = 0.5):
        super().__init__(confidence_threshold)

        try:
            import mediapipe as mp
        except ImportError:
            raise ImportError(
                "MediaPipe not installed. Install with: pip install mediapipe"
            ) from None

        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=2,
            smooth_landmarks=True,
            min_detection_confidence=confidence_threshold,
            min_tracking_confidence=confidence_threshold,
        )

    def extract(self, frame: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Extract pose using MediaPipe."""
        results = self.pose.process(frame)

        if results.pose_world_landmarks:
            landmarks = results.pose_world_landmarks.landmark
            num_joints = len(landmarks)

            keypoints = np.zeros((num_joints, 3))
            confidence = np.zeros(num_joints)

            for i, lm in enumerate(landmarks):
                keypoints[i] = [lm.x, lm.y, lm.z]
                confidence[i] = lm.visibility

            return keypoints, confidence
        else:
            # Return zeros if no pose detected
            num_joints = 33  # MediaPipe has 33 landmarks
            return np.zeros((num_joints, 3)), np.zeros(num_joints)

    def get_keypoint_names(self) -> list[str]:
        """Return MediaPipe keypoint names."""
        return [
            "nose",
            "left_eye_inner",
            "left_eye",
            "left_eye_outer",
            "right_eye_inner",
            "right_eye",
            "right_eye_outer",
            "left_ear",
            "right_ear",
            "mouth_left",
            "mouth_right",
            "left_shoulder",
            "right_shoulder",
            "left_elbow",
            "right_elbow",
            "left_wrist",
            "right_wrist",
            "left_pinky",
            "right_pinky",
            "left_index",
            "right_index",
            "left_thumb",
            "right_thumb",
            "left_hip",
            "right_hip",
            "left_knee",
            "right_knee",
            "left_ankle",
            "right_ankle",
            "left_heel",
            "right_heel",
            "left_foot_index",
            "right_foot_index",
        ]


class MMPosePoseExtractor(PoseExtractor):
    """MMPose extractor (placeholder - requires full MMPose setup)."""

    def __init__(
        self,
        confidence_threshold: float = 0.5,
        config: str = None,
        checkpoint: str = None,
    ):
        super().__init__(confidence_threshold)
        # DEFERRED: Implement MMPose integration
        # This requires mmpose, mmdet, mmcv installation
        warnings.warn(
            "MMPose backend not fully implemented yet. Use MediaPipe for now.",
            stacklevel=2,
        )

    def extract(self, frame: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        raise NotImplementedError("MMPose backend coming soon")

    def get_keypoint_names(self) -> list[str]:
        raise NotImplementedError


class PoseConverter:
    """Convert videos to pose sequences."""

    def __init__(
        self,
        pose_backend: str = "mediapipe",
        confidence_threshold: float = 0.5,
        visualize: bool = False,
    ):
        self.pose_backend = pose_backend
        self.visualize = visualize

        # Initialize pose extractor
        if pose_backend == "mediapipe":
            self.extractor = MediaPipePoseExtractor(confidence_threshold)
        elif pose_backend == "mmpose":
            self.extractor = MMPosePoseExtractor(confidence_threshold)
        else:
            raise ValueError(f"Unknown pose backend: {pose_backend}")

        logger.info(f"Initialized {pose_backend} pose extractor")

    @jit(nopython=True, fastmath=True)
    def process_video(
        self,
        video_path: str,
        start_frame: int,
        end_frame: int,
        output_path: str,
    ) -> dict:
        """
        Process a single video and extract poses.

        Args:
            video_path: Path to video file
            start_frame: Start frame index
            end_frame: End frame index
            output_path: Output .npz file path

        Returns:
            Statistics dict
        """
        if cv2 is None:
            raise ImportError("OpenCV required for video processing")

        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        # Clamp frame range
        start_frame = max(0, min(start_frame, total_frames - 1))
        end_frame = max(start_frame + 1, min(end_frame, total_frames))
        num_frames = end_frame - start_frame

        # Seek to start frame
        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        # Storage
        num_joints = 33  # MediaPipe standard
        skeletons = np.zeros((num_frames, num_joints, 3))
        confidences = np.zeros((num_frames, num_joints))
        timestamps = np.zeros(num_frames)

        # Process frames
        for i in tqdm(range(num_frames), desc=f"Processing {Path(video_path).name}"):
            ret, frame = cap.read()
            if not ret:
                break

            # Convert BGR to RGB
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

            # Extract pose
            keypoints, confidence = self.extractor.extract(frame_rgb)

            skeletons[i] = keypoints
            confidences[i] = confidence
            timestamps[i] = (start_frame + i) / fps

            # Visualize if requested
            if self.visualize and i % 10 == 0:  # Show every 10th frame
                self._visualize_pose(frame, keypoints, confidence)

        cap.release()
        if self.visualize:
            cv2.destroyAllWindows()

        # Compute swing phases (simple heuristic based on wrist height)
        phase_labels = self._compute_swing_phases(skeletons, confidences)

        # Save to .npz
        np.savez(
            output_path,
            skeleton=skeletons,
            skeleton_confidence=confidences,
            timestamps=timestamps,
            phase_labels=phase_labels,
            keypoint_names=self.extractor.get_keypoint_names(),
            fps=fps,
        )

        # Compute statistics
        valid_frames = (confidences.mean(axis=1) > self.extractor.confidence_threshold).sum()
        stats = {
            "total_frames": num_frames,
            "valid_frames": int(valid_frames),
            "avg_confidence": float(confidences.mean()),
            "output_path": output_path,
        }

        return stats

    def _compute_swing_phases(self, skeletons: np.ndarray, confidences: np.ndarray) -> np.ndarray:
        """
        Compute swing phases based on wrist trajectory.

        Phases:
        0 = address
        1 = backswing
        2 = downswing
        3 = impact
        4 = follow-through

        Args:
            skeletons: (T, num_joints, 3)
            confidences: (T, num_joints)

        Returns:
            phase_labels: (T,) integer phase labels
        """
        T = len(skeletons)
        phase_labels = np.zeros(T, dtype=np.int32)

        # Use right wrist (joint 16 in MediaPipe) as reference
        # DEFERRED: Make this more robust - handle left/right handed
        wrist_idx = 16  # right wrist
        wrist_traj = skeletons[:, wrist_idx, :]

        # Simple heuristic: track vertical position
        wrist_y = wrist_traj[:, 1]  # y coordinate (vertical)

        # Find peaks (top of backswing and follow-through)
        from scipy.signal import find_peaks

        try:
            peaks, _ = find_peaks(wrist_y, distance=10)

            if len(peaks) >= 1:
                backswing_peak = peaks[0]

                # Phases
                phase_labels[:backswing_peak] = 1  # backswing
                phase_labels[backswing_peak:] = 2  # downswing

                # Find impact (lowest point after backswing peak)
                if backswing_peak < T - 1:
                    impact_idx = backswing_peak + np.argmin(wrist_y[backswing_peak:])
                    phase_labels[impact_idx : impact_idx + 3] = 3  # impact (3 frames)
                    phase_labels[impact_idx + 3 :] = 4  # follow-through

                # Address (first few frames)
                phase_labels[:5] = 0

        except ImportError:
            # scipy not available, use simple fallback
            pass

        return phase_labels

    def _visualize_pose(
        self, frame: np.ndarray, keypoints: np.ndarray, confidence: np.ndarray
    ) -> Any:
        """Draw pose on frame for visualization."""
        # Simple visualization: draw keypoints
        h, w = frame.shape[:2]

        for _i, (kp, conf) in enumerate(zip(keypoints, confidence, strict=False)):
            if conf > self.extractor.confidence_threshold:
                # MediaPipe outputs normalized coords, scale to image
                x = int(kp[0] * w)
                y = int(kp[1] * h)
                cv2.circle(frame, (x, y), 3, (0, 255, 0), -1)

        cv2.imshow("Pose", frame)
        cv2.waitKey(1)


def main() -> Any:
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

            logger.info(f"  ✓ Valid frames: {stats['valid_frames']}/{stats['total_frames']}")
            logger.info(f"  ✓ Avg confidence: {stats['avg_confidence']:.3f}")

        except Exception as e:  # noqa: BLE001
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
