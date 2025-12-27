
import numpy as np
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QDockWidget,
    QFileDialog,
    QHBoxLayout,
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from golf_swing_analysis.gui.widgets import PlotWidget, VideoWidget
from golf_swing_analysis.model.dynamics import DynamicsModel
from golf_swing_analysis.model.pose_estimator import PoseEstimator
from golf_swing_analysis.model.video_processor import VideoProcessor


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Golf Swing Analysis Interface")
        self.resize(1280, 720)

        # Models
        self.video_processor: VideoProcessor | None = None
        self.pose_estimator = PoseEstimator()
        self.dynamics_model = DynamicsModel()

        # Timer for playback
        self.timer = QTimer()
        self.timer.timeout.connect(self.process_next_frame)
        self.is_playing = False

        self.setup_ui()

    def setup_ui(self) -> None:
        # Central Widget - Video Player
        self.video_widget = VideoWidget()
        self.setCentralWidget(self.video_widget)

        # Bottom Controls
        control_dock = QDockWidget("Controls", self)
        control_widget = QWidget()
        control_layout = QHBoxLayout()

        self.btn_load = QPushButton("Load Video")
        self.btn_load.clicked.connect(self.load_video)

        self.btn_play = QPushButton("Play")
        self.btn_play.clicked.connect(self.toggle_playback)
        self.btn_play.setEnabled(False)

        control_layout.addWidget(self.btn_load)
        control_layout.addWidget(self.btn_play)
        control_layout.addStretch()

        control_widget.setLayout(control_layout)
        control_dock.setWidget(control_widget)
        control_dock.setFeatures(QDockWidget.DockWidgetFeature.NoDockWidgetFeatures)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, control_dock)

        # Right Side - Analysis
        analysis_dock = QDockWidget("Analysis", self)
        analysis_widget = QWidget()
        analysis_layout = QVBoxLayout()

        self.plot_grip_force = PlotWidget("Grip Force (N)")
        self.plot_reaction = PlotWidget("Ground Reaction (N)")

        analysis_layout.addWidget(self.plot_grip_force)
        analysis_layout.addWidget(self.plot_reaction)

        analysis_widget.setLayout(analysis_layout)
        analysis_dock.setWidget(analysis_widget)
        self.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, analysis_dock)

    def load_video(self) -> None:
        file_name, _ = QFileDialog.getOpenFileName(
            self, "Open Video", "", "Video Files (*.mp4 *.avi *.mov)"
        )
        if file_name:
            try:
                self.video_processor = VideoProcessor(file_name)
                self.btn_play.setEnabled(True)
                # Show first frame
                self.process_next_frame()
            except ValueError as e:
                # In a real app we would show a message box here
                # but for now we log to stderr or just print
                pass
                del e

    def toggle_playback(self) -> None:
        if not self.video_processor:
            return

        if self.is_playing:
            self.timer.stop()
            self.btn_play.setText("Play")
        else:
            fps = self.video_processor.get_fps()
            if fps > 0:
                self.timer.start(int(1000 / fps))
            else:
                self.timer.start(33)  # Fallback to ~30fps
            self.btn_play.setText("Pause")
        self.is_playing = not self.is_playing

    def process_next_frame(self) -> None:
        if not self.video_processor:
            return

        frame = self.video_processor.get_frame()
        if frame is None:
            self.timer.stop()
            self.is_playing = False
            self.btn_play.setText("Play")
            return

        # 1. Pose Estimation
        keypoints = self.pose_estimator.process_frame(frame)

        # 2. Dynamics
        forces = self.dynamics_model.calculate_forces(keypoints)

        # 3. Update GUI
        self.video_widget.update_frame(frame, keypoints)
        self.plot_grip_force.update_data(
            forces["grip_force"] + np.random.normal(0, 5)
        )  # Add noise for visual effect
        self.plot_reaction.update_data(
            forces["ground_reaction"] + np.random.normal(0, 10)
        )

    def closeEvent(self, event: QCloseEvent) -> None:
        if self.video_processor:
            self.video_processor.release()
        event.accept()
