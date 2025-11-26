# Double Pendulum Model

This folder contains a standalone, driven double pendulum toolkit with both a Tkinter GUI and a browser-based playground. It was separated from the solar system simulator to keep the projects independent.

## Contents
- `double_pendulum_model/physics/double_pendulum.py`: control-affine dynamics, parameter helpers, and safe expression parsing.
- `double_pendulum_model/ui/double_pendulum_gui.py`: desktop GUI for configuring and visualizing the pendulum.
- `double_pendulum_model/visualization/double_pendulum_web/`: HTML/JS playground for browser demos.
- `double_pendulum_model/tests/`: unit tests for the physics utilities.

## Running the GUI
```bash
python -m double_pendulum_model.ui.double_pendulum_gui
```

## Running the tests
```bash
python -m pytest "Double Pendulum Model/double_pendulum_model/tests"
```
