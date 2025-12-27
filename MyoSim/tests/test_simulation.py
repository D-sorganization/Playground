import os

import pytest
from myosim.simulation.model import MujocoModel


# Fixture to provide the model path
@pytest.fixture
def model_path() -> str:
    # Assuming tests are run from repo root
    return os.path.join(
        os.getcwd(), "MyoSim", "src", "myosim", "assets", "golf_swing.xml"
    )


def test_model_loading(model_path: str) -> None:
    """Test that the MuJoCo model loads without error."""
    try:
        model = MujocoModel(model_path)
    except ImportError:
        pytest.skip("MuJoCo not installed or compatible in this environment")
    except Exception as e:
        pytest.fail(f"Failed to load model: {e}")

    assert model.model is not None
    assert model.data is not None


def test_simulation_step(model_path: str) -> None:
    """Test that the simulation can step forward."""
    try:
        model = MujocoModel(model_path)
    except ImportError:
        pytest.skip("MuJoCo not installed")

    initial_time = model.get_time()
    model.paused = False
    model.step()

    assert model.get_time() > initial_time


def test_actuator_control(model_path: str) -> None:
    """Test setting actuator controls."""
    try:
        model = MujocoModel(model_path)
    except ImportError:
        pytest.skip("MuJoCo not installed")

    try:
        model.set_control("shoulder_motor", 0.5)
    except Exception as e:
        pytest.fail(f"set_control failed: {e}")
