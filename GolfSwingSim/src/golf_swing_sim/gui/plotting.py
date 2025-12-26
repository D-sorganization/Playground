"""
Plotting and Visualization widgets for the Golf Swing Simulator.
"""

import logging
from typing import Any

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QVBoxLayout, QWidget

logger = logging.getLogger(__name__)


class TimeSeriesPlotWidget(QWidget):
    """
    Widget for plotting time-series data (Forces, Controls, Torques).
    """

    def __init__(self, title: str, ylabel: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.layout_ = QVBoxLayout(self)
        self.layout_.setContentsMargins(0, 0, 0, 0)

        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.layout_.addWidget(self.canvas)

        self.ax = self.figure.add_subplot(111)
        self.ax.set_title(title)
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel(ylabel)
        self.ax.grid(True)

        self.figure.tight_layout()

    def plot(
        self, time: np.ndarray, data: np.ndarray, labels: list[str] | None = None
    ) -> None:
        """
        Update the plot with new data.

        Args:
            time: Time array.
            data: Data array of shape (N_steps, N_lines).
            labels: List of labels for the legend.
        """
        self.ax.clear()
        self.ax.grid(True)
        self.ax.set_xlabel("Time (s)")

        # Handle 1D or 2D data
        if data.ndim == 1:
            data = data[:, np.newaxis]

        n_lines = data.shape[1]
        for i in range(n_lines):
            label = labels[i] if labels and i < len(labels) else f"Series {i + 1}"
            self.ax.plot(time, data[:, i], label=label)

        if labels:
            self.ax.legend()

        self.canvas.draw()


class SwingAnimationWidget(QWidget):
    """
    Widget for 3D visualization of the golf swing.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.layout_ = QVBoxLayout(self)

        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvasQTAgg(self.figure)
        self.layout_.addWidget(self.canvas)

        # Add 3D axes
        self.ax = self.figure.add_subplot(111, projection="3d")
        self.ax.set_title("3D Swing Visualization")

        self._data: Any = None
        self._frame_idx = 0
        self._timer = QTimer()
        self._timer.timeout.connect(self._update_frame)
        self._is_playing = False

        # Cache for plot objects
        self._lines: dict[str, Any] = {}

    def load_data(
        self, marker_positions: dict[str, np.ndarray], dt: float = 0.01
    ) -> None:
        """Load simulation data for playback."""
        self._data = marker_positions
        self._frame_idx = 0
        # Set timer interval (ms)
        self._timer.setInterval(int(dt * 1000))

        # Initial draw
        self._draw_frame(0)

    def play(self) -> None:
        if self._data and not self._is_playing:
            self._timer.start()
            self._is_playing = True

    def pause(self) -> None:
        self._timer.stop()
        self._is_playing = False

    def reset(self) -> None:
        self.pause()
        self._frame_idx = 0
        self._draw_frame(0)

    def _update_frame(self) -> None:
        """Advance animation by one frame."""
        if not self._data:
            return

        n_frames = len(next(iter(self._data.values())))
        self._frame_idx += 10  # Speed up playback (skip frames)

        if self._frame_idx >= n_frames:
            self._frame_idx = 0

        self._draw_frame(self._frame_idx)

    def _draw_frame(self, idx: int) -> None:
        """Draw a specific frame."""
        self.ax.clear()

        # Set fixed limits to avoid camera jumping
        self.ax.set_xlim(-1.5, 1.5)
        self.ax.set_ylim(0, 3.0)
        self.ax.set_zlim(-1.5, 1.5)

        self.ax.set_xlabel("X")
        self.ax.set_ylabel("Y (Height)")
        self.ax.set_zlabel("Z")

        # Extract points
        # Assuming we have Shoulder, Hand, ClubHead
        s = self._data["Shoulder"][idx]
        h = self._data["Hand"][idx]
        c = self._data["ClubHead"][idx]

        # Draw Arm (Shoulder -> Hand)
        self.ax.plot(
            [s[0], h[0]], [s[1], h[1]], [s[2], h[2]], "b-", linewidth=4, label="Arm"
        )

        # Draw Club (Hand -> ClubHead)
        self.ax.plot(
            [h[0], c[0]], [h[1], c[1]], [h[2], c[2]], "k-", linewidth=3, label="Club"
        )

        # Draw Joints
        self.ax.scatter(
            [s[0], h[0], c[0]], [s[1], h[1], c[1]], [s[2], h[2], c[2]], c="r", s=50
        )

        # Ground plane
        xx, zz = np.meshgrid(np.linspace(-1, 1, 2), np.linspace(-1, 1, 2))
        yy = xx * 0
        self.ax.plot_surface(xx, yy, zz, alpha=0.2, color="green")

        self.canvas.draw()
