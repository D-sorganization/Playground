"""
Main Window for the Golf Swing Simulator.
"""

import logging

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QDockWidget,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QSlider,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from golf_swing_sim.gui.plotting import SwingAnimationWidget, TimeSeriesPlotWidget
from golf_swing_sim.simulation.model import GolfSwingModel

logger = logging.getLogger(__name__)


class ControlPanel(QWidget):
    """
    Panel for adjusting simulation parameters.
    """

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)

        # Muscle Strength Group
        self.grp_muscle = QGroupBox("Muscle Parameters")
        form_muscle = QFormLayout()

        self.slider_strength = QSlider(Qt.Orientation.Horizontal)
        self.slider_strength.setRange(10, 200)
        self.slider_strength.setValue(50)
        form_muscle.addRow("Shoulder Torque:", self.slider_strength)

        self.grp_muscle.setLayout(form_muscle)
        layout.addWidget(self.grp_muscle)

        # Club Parameters Group
        self.grp_club = QGroupBox("Club Parameters")
        form_club = QFormLayout()

        self.slider_mass = QSlider(Qt.Orientation.Horizontal)
        self.slider_mass.setRange(1, 20)  # 0.1 to 2.0 kg
        self.slider_mass.setValue(4)
        form_club.addRow("Club Mass:", self.slider_mass)

        self.grp_club.setLayout(form_club)
        layout.addWidget(self.grp_club)

        # Simulation Controls
        self.btn_run = QPushButton("Run Simulation")
        layout.addWidget(self.btn_run)

        layout.addStretch()


class GolfSwingMainWindow(QMainWindow):
    """
    Main application window.
    """

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Golf Swing Simulator - OpenSim Interface")
        self.resize(1200, 800)

        # Model
        self.model = GolfSwingModel()

        # UI Setup
        self._setup_ui()

        # Connections
        self.control_panel.btn_run.clicked.connect(self.run_simulation)
        self.control_panel.slider_strength.valueChanged.connect(self._update_params)
        self.control_panel.slider_mass.valueChanged.connect(self._update_params)

    def _setup_ui(self) -> None:
        # Central Widget (Tabs)
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Tab 1: 3D View
        self.tab_3d = QWidget()
        layout_3d = QVBoxLayout(self.tab_3d)
        self.anim_widget = SwingAnimationWidget()
        layout_3d.addWidget(self.anim_widget)

        # Playback controls
        hbox = QHBoxLayout()
        self.btn_play = QPushButton("Play")
        self.btn_pause = QPushButton("Pause")
        self.btn_reset = QPushButton("Reset")

        self.btn_play.clicked.connect(self.anim_widget.play)
        self.btn_pause.clicked.connect(self.anim_widget.pause)
        self.btn_reset.clicked.connect(self.anim_widget.reset)

        hbox.addWidget(self.btn_play)
        hbox.addWidget(self.btn_pause)
        hbox.addWidget(self.btn_reset)
        layout_3d.addLayout(hbox)

        self.tabs.addTab(self.tab_3d, "3D Visualization")

        # Tab 2: Forces
        self.plot_forces = TimeSeriesPlotWidget("Muscle Forces", "Force (N)")
        self.tabs.addTab(self.plot_forces, "Muscle Forces")

        # Tab 3: Controls
        self.plot_controls = TimeSeriesPlotWidget("Control Signals", "Activation (0-1)")
        self.tabs.addTab(self.plot_controls, "Control Signals")

        # Tab 4: Torques
        self.plot_torques = TimeSeriesPlotWidget("Joint Torques", "Torque (Nm)")
        self.tabs.addTab(self.plot_torques, "Joint Torques")

        # Dock Widget (Controls)
        self.dock = QDockWidget("Simulation Controls", self)
        self.control_panel = ControlPanel()
        self.dock.setWidget(self.control_panel)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, self.dock)

    def _update_params(self) -> None:
        """Update model parameters from UI."""
        strength = self.control_panel.slider_strength.value()
        mass = self.control_panel.slider_mass.value() / 10.0

        self.model.shoulder_torque = float(strength)
        self.model.club_mass = float(mass)
        logger.info(f"Updated params: Torque={strength}, Mass={mass}")

    def run_simulation(self) -> None:
        """Run the simulation and update views."""
        logger.info("Starting simulation...")
        result = self.model.run_simulation()

        # Update 3D
        self.anim_widget.load_data(result.marker_positions, dt=self.model.dt)
        self.anim_widget.play()

        # Update Plots
        self.plot_forces.plot(
            result.time, result.muscle_forces, ["Shoulder Force", "Wrist Force"]
        )
        self.plot_controls.plot(
            result.time,
            result.control_signals,
            ["Shoulder Activation", "Wrist Activation"],
        )
        self.plot_torques.plot(
            result.time, result.joint_torques, ["Shoulder Torque", "Wrist Torque"]
        )

        logger.info("Simulation complete.")


def main() -> None:
    """Entry point."""
    import sys

    logging.basicConfig(level=logging.INFO)

    app = QApplication(sys.argv)
    window = GolfSwingMainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
