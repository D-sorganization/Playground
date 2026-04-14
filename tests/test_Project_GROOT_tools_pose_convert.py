"""Tests for Project_GROOT.tools.pose_convert - decomposed helpers."""

import numpy as np

import src.Project_GROOT.tools.pose_convert as target_module
from src.Project_GROOT.tools.pose_convert import PoseConverter


def test_module_syntax_and_import():
    """Verify Project_GROOT.tools.pose_convert can be imported."""
    assert target_module is not None


def test_has_symbol_PoseExtractor():
    """Verify PoseExtractor exists in module."""
    assert hasattr(target_module, "PoseExtractor")


def test_has_symbol_MediaPipePoseExtractor():
    """Verify MediaPipePoseExtractor exists in module."""
    assert hasattr(target_module, "MediaPipePoseExtractor")


def test_has_symbol_MMPosePoseExtractor():
    """Verify MMPosePoseExtractor exists in module."""
    assert hasattr(target_module, "MMPosePoseExtractor")


def test_has_symbol_PoseConverter():
    """Verify PoseConverter exists in module."""
    assert hasattr(target_module, "PoseConverter")


def test_has_symbol_main():
    """Verify main exists in module."""
    assert hasattr(target_module, "main")


# --- PoseConverter decomposed method tests ---
# These test the new sub-methods without requiring OpenCV or MediaPipe.


class _StubExtractor:
    """Minimal extractor stub for unit testing PoseConverter internals."""

    confidence_threshold = 0.5

    def extract(self, frame):
        kp = np.zeros((33, 3))
        conf = np.ones(33) * 0.9
        return kp, conf

    def get_keypoint_names(self):
        return [f"joint_{i}" for i in range(33)]


def _make_converter() -> PoseConverter:
    """Return a PoseConverter with the extractor patched to the stub."""
    # PoseConverter.__init__ tries to instantiate the real extractor,
    # so we create and patch instead of calling __init__ normally.
    conv = object.__new__(PoseConverter)
    conv.extractor = _StubExtractor()
    conv.visualize = False
    return conv


def test_compute_frame_stats_returns_dict():
    """_compute_frame_stats returns a dict with correct keys."""
    conv = _make_converter()
    confidences = np.ones((10, 33)) * 0.8
    stats = conv._compute_frame_stats(confidences, "output.npz")
    assert stats["total_frames"] == 10
    assert "valid_frames" in stats
    assert "avg_confidence" in stats
    assert stats["output_path"] == "output.npz"


def test_compute_frame_stats_valid_frames_count():
    """Frames with mean confidence >= threshold count as valid."""
    conv = _make_converter()
    # All frames high confidence
    confidences = np.ones((5, 33)) * 0.9
    stats = conv._compute_frame_stats(confidences, "x.npz")
    assert stats["valid_frames"] == 5


def test_compute_frame_stats_low_confidence():
    """Frames with mean confidence below threshold are not counted as valid."""
    conv = _make_converter()
    confidences = np.ones((5, 33)) * 0.1  # all below 0.5 threshold
    stats = conv._compute_frame_stats(confidences, "x.npz")
    assert stats["valid_frames"] == 0


def test_save_pose_data_creates_file(tmp_path):
    """_save_pose_data creates a .npz file at the specified path."""
    conv = _make_converter()
    n = 5
    skeletons = np.zeros((n, 33, 3))
    confidences = np.ones((n, 33)) * 0.9
    timestamps = np.linspace(0, 1, n)
    phase_labels = np.zeros(n, dtype=np.int32)

    out_path = str(tmp_path / "poses.npz")
    conv._save_pose_data(
        out_path, skeletons, confidences, timestamps, phase_labels, 30.0
    )

    assert (tmp_path / "poses.npz").exists()
    data = np.load(out_path)
    assert "skeleton" in data
    assert "timestamps" in data
    assert "fps" in data
