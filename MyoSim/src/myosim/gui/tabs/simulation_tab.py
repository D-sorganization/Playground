from typing import Any

from myosim.gui.widgets.mujoco_viewer import MujocoViewer
from PyQt6.QtWidgets import QHBoxLayout, QPushButton, QVBoxLayout, QWidget


class SimulationTab(QWidget):
    def __init__(self, model: Any) -> None:
        super().__init__()
        self.model = model

        layout = QVBoxLayout()
        self.setLayout(layout)

        # Viewer
        self.viewer = MujocoViewer(model)
        layout.addWidget(self.viewer, stretch=1)

        # Playback Controls
        controls_layout = QHBoxLayout()

        self.btn_play = QPushButton("Play")
        self.btn_play.clicked.connect(self.toggle_play)

        self.btn_reset = QPushButton("Reset")
        self.btn_reset.clicked.connect(self.reset_simulation)

        controls_layout.addWidget(self.btn_play)
        controls_layout.addWidget(self.btn_reset)
        controls_layout.addStretch()

        layout.addLayout(controls_layout)

    def toggle_play(self) -> None:
        self.model.paused = not self.model.paused
        if self.model.paused:
            self.btn_play.setText("Play")
        else:
            self.btn_play.setText("Pause")

    def reset_simulation(self) -> None:
        self.model.reset()
        # Ensure we are paused after reset
        self.model.paused = True
        self.btn_play.setText("Play")
        self.viewer.update()
