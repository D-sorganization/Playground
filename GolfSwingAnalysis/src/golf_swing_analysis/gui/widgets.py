from typing import Any

import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from matplotlib.lines import Line2D
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget


class VideoWidget(QWidget):
    def __init__(self) -> None:
        super().__init__()
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setMinimumSize(640, 480)
        self.image_label.setStyleSheet("background-color: black;")

        layout = QVBoxLayout()
        layout.addWidget(self.image_label)
        self.setLayout(layout)

        self.current_frame: np.ndarray[Any, Any] | None = None
        self.current_keypoints: dict[int, tuple[float, float, float]] | None = None

    def update_frame(
        self,
        frame: np.ndarray[Any, Any],
        keypoints: dict[int, tuple[float, float, float]] | None = None,
    ) -> None:
        self.current_frame = frame
        self.current_keypoints = keypoints

        h, w, ch = frame.shape
        bytes_per_line = ch * w

        # Convert numpy array to QImage
        qt_image = QImage(
            frame.data, w, h, bytes_per_line, QImage.Format.Format_RGB888
        )

        # Draw keypoints on QPixmap
        pixmap = QPixmap.fromImage(qt_image)

        if keypoints:
            painter = QPainter(pixmap)
            pen = QPen(QColor(0, 255, 0))
            pen.setWidth(3)
            painter.setPen(pen)

            for _, (x, y, conf) in keypoints.items():
                if conf > 0.5:
                    painter.drawPoint(int(x), int(y))
                    painter.drawEllipse(int(x) - 3, int(y) - 3, 6, 6)
            painter.end()

        self.image_label.setPixmap(
            pixmap.scaled(
                self.image_label.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )


class PlotWidget(QWidget):
    def __init__(self, title: str = "Graph") -> None:
        super().__init__()
        layout = QVBoxLayout()
        self.figure = Figure(figsize=(5, 3))
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        self.ax.set_title(title)

        layout.addWidget(self.canvas)
        self.setLayout(layout)

        self.data_buffer: list[float] = []
        self.max_points = 100
        self.line: Line2D | None = None

    def update_data(self, value: float) -> None:
        self.data_buffer.append(value)
        if len(self.data_buffer) > self.max_points:
            self.data_buffer.pop(0)

        if self.line is None:
            (self.line,) = self.ax.plot(self.data_buffer)
        else:
            self.line.set_ydata(self.data_buffer)
            self.line.set_xdata(range(len(self.data_buffer)))
            self.ax.relim()
            self.ax.autoscale_view()

        self.canvas.draw()
