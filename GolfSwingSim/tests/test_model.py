"""
Tests for GolfSwingSim
"""

import numpy as np
import pytest
from golf_swing_sim.simulation.model import GolfSwingModel

def test_model_initialization():
    model = GolfSwingModel()
    assert model.use_opensim is False
    assert model.gravity == -9.81

def test_simulation_run():
    model = GolfSwingModel()
    # Reduced duration for faster test
    model.duration = 0.1
    result = model.run_simulation()

    assert result.time.shape[0] > 0
    assert result.states.shape[1] == 4
    assert "Shoulder" in result.marker_positions
    assert "Hand" in result.marker_positions
    assert "ClubHead" in result.marker_positions

    # Check if ClubHead moves (not all zeros)
    # At t=0 it might be static, but over time it should move?
    # Initial state is backswing.
    assert not np.all(result.marker_positions["ClubHead"] == 0)

def test_parameter_update():
    model = GolfSwingModel()
    original_torque = model.shoulder_torque
    model.shoulder_torque = 100.0
    assert model.shoulder_torque == 100.0
    assert model.shoulder_torque != original_torque
