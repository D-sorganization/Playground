import pytest
import sys
import os
from unittest.mock import MagicMock, patch

# Add src to path
sys.path.append(os.path.join(os.path.dirname(__file__), "../src"))

from golf_swing_analysis.model.video_processor import VideoProcessor
from golf_swing_analysis.model.pose_estimator import PoseEstimator
from golf_swing_analysis.model.dynamics import DynamicsModel

def test_dynamics_model() -> None:
    model = DynamicsModel()
    forces = model.calculate_forces({})
    assert "grip_force" in forces
    assert "ground_reaction" in forces
    assert forces["grip_force"] == 100.0

def test_pose_estimator() -> None:
    estimator = PoseEstimator()
    # Mock a small frame 10x10
    import numpy as np
    frame = np.zeros((10, 10, 3), dtype=np.uint8)
    keypoints = estimator.process_frame(frame)
    assert len(keypoints) == 25
    assert isinstance(keypoints[0], tuple)
    assert len(keypoints[0]) == 3

@patch('cv2.VideoCapture')
def test_video_processor(mock_capture: MagicMock) -> None:
    mock_instance = mock_capture.return_value
    mock_instance.isOpened.return_value = True

    processor = VideoProcessor("dummy.mp4")
    assert processor.cap == mock_instance
    processor.release()
    mock_instance.release.assert_called_once()
