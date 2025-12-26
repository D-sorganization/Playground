import logging
import os
import sys

from PyQt6.QtWidgets import QMainWindow, QTabWidget, QVBoxLayout, QWidget

from myosim.gui.tabs.analysis_tab import AnalysisTab
from myosim.gui.tabs.controls_tab import ControlsTab
from myosim.gui.tabs.simulation_tab import SimulationTab
from myosim.simulation.model import MujocoModel

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("MyoSim - Golf Swing Analysis")
        self.resize(1200, 800)

        # Initialize Simulation Model
        # Assuming asset path relative to this file or root
        current_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up two levels to src/myosim then to assets
        asset_path = os.path.join(
            os.path.dirname(os.path.dirname(current_dir)),
            "myosim",
            "assets",
            "golf_swing.xml",
        )

        logger.info(f"Loading model from: {asset_path}")

        try:
            self.model = MujocoModel(asset_path)
        except Exception as e:
            logger.critical(f"Could not load model: {e}")
            sys.exit(1)

        # Main Layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        # Tab Widget
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs)

        # Create Tabs
        self.simulation_tab = SimulationTab(self.model)
        self.controls_tab = ControlsTab(self.model)
        self.analysis_tab = AnalysisTab(self.model)

        # Add Tabs
        self.tabs.addTab(self.simulation_tab, "Simulation")
        self.tabs.addTab(self.controls_tab, "Controls")
        self.tabs.addTab(self.analysis_tab, "Analysis")
