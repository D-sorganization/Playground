from typing import Any

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
from matplotlib.figure import Figure
from PyQt6.QtCore import QTimer
from PyQt6.QtWidgets import QVBoxLayout, QWidget


class AnalysisTab(QWidget):
    def __init__(self, model: Any) -> None:
        super().__init__()
        self.model = model

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Matplotlib Figure
        self.figure = Figure(figsize=(5, 4), dpi=100)
        self.canvas = FigureCanvasQTAgg(self.figure)
        layout.addWidget(self.canvas)

        self.ax = self.figure.add_subplot(111)
        self.ax.set_title("Joint Velocities")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Velocity (rad/s)")

        self.times: list[float] = []
        self.shoulder_vels: list[float] = []

        # Plot update timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_plot)
        self.timer.start(100)  # 10 Hz update for plotting

    def update_plot(self) -> None:
        if self.model.paused:
            return

        t = self.model.get_time()
        v = self.model.get_joint_velocity("shoulder_joint")

        self.times.append(t)
        self.shoulder_vels.append(v)

        # Keep buffer limited
        if len(self.times) > 200:
            self.times.pop(0)
            self.shoulder_vels.pop(0)

        self.ax.clear()
        self.ax.set_title("Joint Velocities")
        self.ax.set_xlabel("Time (s)")
        self.ax.set_ylabel("Velocity (rad/s)")
        self.ax.plot(self.times, self.shoulder_vels, label="Shoulder")
        self.ax.legend(loc="upper right")

        self.canvas.draw()
