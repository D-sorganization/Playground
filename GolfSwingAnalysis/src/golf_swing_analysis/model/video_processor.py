from typing import Any

import cv2
import numpy as np


class VideoProcessor:
    def __init__(self, video_path: str) -> None:
        self.cap = cv2.VideoCapture(video_path)
        if not self.cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")

    def get_frame(self) -> np.ndarray[Any, Any] | None:
        ret, frame = self.cap.read()
        if not ret:
            return None
        # Convert BGR (OpenCV default) to RGB
        return cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

    def get_frame_count(self) -> int:
        return int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))

    def get_fps(self) -> float:
        return float(self.cap.get(cv2.CAP_PROP_FPS))

    def release(self) -> None:
        self.cap.release()
