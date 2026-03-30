import sys
from unittest.mock import MagicMock

try:
    pass
except ImportError:
    # Mock omni and its submodules
    omni_mock = MagicMock()
    sys.modules["omni"] = omni_mock
    sys.modules["omni.isaac"] = omni_mock.isaac
    sys.modules["omni.isaac.lab"] = omni_mock.isaac.lab
    sys.modules["omni.isaac.lab.sim"] = omni_mock.isaac.lab.sim
    sys.modules["omni.isaac.lab.envs"] = omni_mock.isaac.lab.envs
    sys.modules["omni.isaac.lab.scene"] = omni_mock.isaac.lab.scene
    sys.modules["omni.isaac.lab.assets"] = omni_mock.isaac.lab.assets
    sys.modules["omni.isaac.lab.utils"] = omni_mock.isaac.lab.utils

    # Also mock configclass decorator so it doesn't fail when called
    def mock_configclass(cls):
        return cls

    sys.modules["omni.isaac.lab.utils"].configclass = mock_configclass

try:
    pass
except ImportError:
    sys.modules["gymnasium"] = MagicMock()
    sys.modules["gym"] = MagicMock()

try:
    pass
except ImportError:
    sys.modules["cv2"] = MagicMock()
