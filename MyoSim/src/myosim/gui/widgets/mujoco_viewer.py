from typing import Any

import mujoco
import numpy as np
from PyQt6.QtCore import QTimer
from PyQt6.QtGui import QImage, QPainter, QPaintEvent, QResizeEvent
from PyQt6.QtWidgets import QWidget


class MujocoViewer(QWidget):
    """
    A widget to render the MuJoCo simulation.
    """
    def __init__(self, model_wrapper: Any, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.model_wrapper = model_wrapper
        self.model = model_wrapper.model
        self.data = model_wrapper.data

        # Initialize Renderer
        self.renderer = mujoco.Renderer(self.model, height=480, width=640)

        # Timer for simulation loop
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_simulation)
        self.timer.start(16)  # ~60 FPS

        # Camera settings
        self.camera = mujoco.MjvCamera()
        self.camera.type = mujoco.mjtCamera.mjCAMERA_FREE
        self.camera.fixedcamid = -1
        # Set initial camera position
        self.camera.distance = 4.0
        self.camera.azimuth = 90.0
        self.camera.elevation = -10.0
        self.camera.lookat = np.array([0.0, 0.0, 1.0])

    def update_simulation(self) -> None:
        # Step physics
        if not self.model_wrapper.paused:
            self.model_wrapper.step()

        # Trigger repaint
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)

        # Render scene
        self.renderer.update_scene(self.data, camera=self.camera)
        pixels = self.renderer.render()

        # Convert numpy array to QImage
        height, width, channel = pixels.shape
        bytes_per_line = 3 * width
        q_img = QImage(
            pixels.data, width, height, bytes_per_line, QImage.Format.Format_RGB888
        )

        # Draw image scaled to widget size
        painter.drawImage(self.rect(), q_img)

    def resizeEvent(self, event: QResizeEvent) -> None:
        # Update renderer size
        width = event.size().width()
        height = event.size().height()
        # Ensure dimensions are valid (non-zero)
        if width > 0 and height > 0:
            self.renderer = mujoco.Renderer(self.model, height=height, width=width)
        super().resizeEvent(event)
