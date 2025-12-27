from typing import Any

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSlider,
    QVBoxLayout,
    QWidget,
)


class ControlsTab(QWidget):
    def __init__(self, model: Any) -> None:
        super().__init__()
        self.model = model
        self.init_ui()

    def init_ui(self) -> None:
        layout = QVBoxLayout()
        self.setLayout(layout)

        # Shoulder Control
        self.shoulder_group = self.create_control_group(
            "Shoulder Motor", "shoulder_motor", -1.0, 1.0
        )
        layout.addWidget(self.shoulder_group)

        # Elbow Control
        self.elbow_group = self.create_control_group(
            "Elbow Motor", "elbow_motor", -1.0, 1.0
        )
        layout.addWidget(self.elbow_group)

        # Wrist Control
        self.wrist_group = self.create_control_group(
            "Wrist Motor", "wrist_motor", -1.0, 1.0
        )
        layout.addWidget(self.wrist_group)

        layout.addStretch()

    def create_control_group(
        self, title: str, actuator_name: str, min_val: float, max_val: float
    ) -> QGroupBox:
        group = QGroupBox(title)
        layout = QHBoxLayout()
        group.setLayout(layout)

        label = QLabel("0.0")
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(int(min_val * 100))
        slider.setMaximum(int(max_val * 100))
        slider.setValue(0)

        slider.valueChanged.connect(
            lambda val: self.update_control(actuator_name, val / 100.0, label)
        )

        layout.addWidget(slider)
        layout.addWidget(label)

        return group

    def update_control(
        self, actuator_name: str, value: float, label_widget: QLabel
    ) -> None:
        label_widget.setText(f"{value:.2f}")
        self.model.set_control(actuator_name, value)
