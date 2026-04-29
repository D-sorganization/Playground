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

import logging
from pathlib import Path
from typing import Any

import numpy as np

from Project_GROOT.tools.pose_extractors import (
    MediaPipePoseExtractor,
    MMPosePoseExtractor,
)

logger = logging.getLogger(__name__)

try:
    import cv2
except ImportError:
    cv2 = None

try:
    from tqdm import tqdm
except ImportError:

    def tqdm(x, **kwargs) -> Any:
        return x  # Fallback


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

    def process_video(
        self,
        video_path: str,
        start_frame: int,
        end_frame: int,
        output_path: str,
    ) -> dict:
        """Process a single video and extract poses.

        Orchestrates frame extraction, pose estimation, phase computation,
        and saving to .npz.

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

        skeletons, confidences, timestamps, fps = self._extract_frames(
            video_path, start_frame, end_frame
        )
        phase_labels = self._compute_swing_phases(skeletons, confidences)
        self._save_pose_data(
            output_path, skeletons, confidences, timestamps, phase_labels, fps
        )
        return self._compute_frame_stats(confidences, output_path)

    def _extract_frames(
        self,
        video_path: str,
        start_frame: int,
        end_frame: int,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray, float]:
        """Open video and extract per-frame pose data.

        Args:
            video_path: Path to video file.
            start_frame: Start frame index.
            end_frame: End frame index.

        Returns:
            Tuple of (skeletons, confidences, timestamps, fps).
        """
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Cannot open video: {video_path}")

        fps = cap.get(cv2.CAP_PROP_FPS)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

        start_frame = max(0, min(start_frame, total_frames - 1))
        end_frame = max(start_frame + 1, min(end_frame, total_frames))
        num_frames = end_frame - start_frame

        cap.set(cv2.CAP_PROP_POS_FRAMES, start_frame)

        num_joints = 33  # MediaPipe standard
        skeletons = np.zeros((num_frames, num_joints, 3))
        confidences = np.zeros((num_frames, num_joints))
        timestamps = np.zeros(num_frames)

        for i in tqdm(range(num_frames), desc=f"Processing {Path(video_path).name}"):
            ret, frame = cap.read()
            if not ret:
                break
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            keypoints, confidence = self.extractor.extract(frame_rgb)
            skeletons[i] = keypoints
            confidences[i] = confidence
            timestamps[i] = (start_frame + i) / fps
            if self.visualize and i % 10 == 0:
                self._visualize_pose(frame, keypoints, confidence)

        cap.release()
        if self.visualize:
            cv2.destroyAllWindows()

        return skeletons, confidences, timestamps, fps

    def _save_pose_data(
        self,
        output_path: str,
        skeletons: np.ndarray,
        confidences: np.ndarray,
        timestamps: np.ndarray,
        phase_labels: np.ndarray,
        fps: float,
    ) -> None:
        """Save extracted pose data to a .npz archive."""
        np.savez(
            output_path,
            skeleton=skeletons,
            skeleton_confidence=confidences,
            timestamps=timestamps,
            phase_labels=phase_labels,
            keypoint_names=self.extractor.get_keypoint_names(),
            fps=fps,
        )

    def _compute_frame_stats(self, confidences: np.ndarray, output_path: str) -> dict:
        """Compute and return frame-level statistics dict."""
        num_frames = len(confidences)
        valid_frames = (
            confidences.mean(axis=1) > self.extractor.confidence_threshold
        ).sum()
        return {
            "total_frames": num_frames,
            "valid_frames": int(valid_frames),
            "avg_confidence": float(confidences.mean()),
            "output_path": output_path,
        }

    def _compute_swing_phases(
        self, skeletons: np.ndarray, confidences: np.ndarray
    ) -> np.ndarray:
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
    ) -> None:
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
