import logging

logger = logging.getLogger(__name__)

#!/usr/bin/env python3
"""
Smoke Test for Project GROOT

Verifies installation and environment setup.

Usage:
    python tools/smoke_test.py --test all
    python tools/smoke_test.py --test gpu
    python tools/smoke_test.py --test isaac_sim
"""

import argparse
import sys
from pathlib import Path


def test_gpu():
    """Test GPU and CUDA availability."""
    logger.info("\n=== GPU Test ===")

    try:
        import torch

        if torch.cuda.is_available():
            logger.info(f"✓ CUDA available: {torch.version.cuda}")
            logger.info(f"✓ GPU: {torch.cuda.get_device_name(0)}")
            print(
                f"✓ GPU memory: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB"  # noqa: E501
            )

            # Simple GPU test
            x = torch.randn(1000, 1000, device="cuda")
            _ = x @ x
            logger.info("✓ GPU computation test passed")

            return True
        else:
            logger.info("✗ CUDA not available")
            return False

    except ImportError:
        logger.info("✗ PyTorch not installed")
        return False
    except Exception as e:  # noqa: BLE001
        logger.info(f"✗ GPU test failed: {e}")
        return False


def test_isaac_sim():
    """Test Isaac Sim installation."""
    logger.info("\n=== Isaac Sim Test ===")

    isaac_sim_path = Path.home() / ".local/share/ov/pkg/isaac-sim-4.2.0"

    if not isaac_sim_path.exists():
        # Try alternative paths
        isaac_sim_path = Path("/isaac-sim")

    if isaac_sim_path.exists():
        logger.info(f"✓ Isaac Sim found at: {isaac_sim_path}")

        # Check Python executable
        python_sh = isaac_sim_path / "python.sh"
        if python_sh.exists():
            logger.info(f"✓ Isaac Sim Python found: {python_sh}")
        else:
            logger.info("⚠ python.sh not found at expected location")

        return True
    else:
        logger.info(f"✗ Isaac Sim not found at: {isaac_sim_path}")
        logger.info("  Install Isaac Sim (see docs/SETUP.md)")
        return False


def test_isaac_lab():
    """Test Isaac Lab installation."""
    logger.info("\n=== Isaac Lab Test ===")

    try:
        import importlib.util

        if importlib.util.find_spec("omni.isaac.lab") is not None:
            logger.info("✓ Isaac Lab imported successfully")
            return True
        else:
            logger.info("✗ Cannot import omni.isaac.lab")
            logger.info("  Install Isaac Lab (see docs/SETUP.md)")
            return False

    except Exception as e:  # noqa: BLE001
        logger.info(f"✗ Isaac Lab test failed: {e}")
        return False


def test_pose_backend():
    """Test pose estimation backend."""
    logger.info("\n=== Pose Estimation Test ===")

    backends = []

    # Test MediaPipe
    try:
        import mediapipe as mp

        logger.info(f"✓ MediaPipe {mp.__version__} installed")
        backends.append("mediapipe")
    except ImportError:
        logger.info("✗ MediaPipe not installed")

    # Test MMPose
    try:
        import mmpose

        logger.info(f"✓ MMPose {mmpose.__version__} installed")
        backends.append("mmpose")
    except ImportError:
        logger.info("⚠ MMPose not installed (optional)")

    if backends:
        logger.info(f"✓ Available backends: {', '.join(backends)}")
        return True
    else:
        logger.info("✗ No pose estimation backends installed")
        return False


def test_dependencies():
    """Test Python dependencies."""
    logger.info("\n=== Dependencies Test ===")

    required = {
        "numpy": "numpy",
        "scipy": "scipy",
        "torch": "torch",
        "cv2": "opencv-python",
        "yaml": "pyyaml",
        "tqdm": "tqdm",
    }

    all_ok = True

    for module, package in required.items():
        try:
            mod = __import__(module)
            version = getattr(mod, "__version__", "unknown")
            logger.info(f"✓ {package}: {version}")
        except ImportError:
            logger.info(f"✗ {package} not installed")
            all_ok = False

    return all_ok


def test_project_structure():
    """Test project directory structure."""
    logger.info("\n=== Project Structure Test ===")

    project_root = Path(__file__).parent.parent
    required_dirs = [
        "data/raw_video",
        "data/processed_pose",
        "data/retargeted_demos",
        "sim/configs",
        "train/configs",
        "eval",
        "tools",
        "docs",
    ]

    all_ok = True

    for dir_path in required_dirs:
        full_path = project_root / dir_path
        if full_path.exists():
            logger.info(f"✓ {dir_path}")
        else:
            logger.info(f"✗ {dir_path} not found")
            all_ok = False

    return all_ok


def test_all():
    """Run all tests."""
    logger.info("=" * 60)
    logger.info("Project GROOT Smoke Test")
    logger.info("=" * 60)

    results = {}

    results["gpu"] = test_gpu()
    results["dependencies"] = test_dependencies()
    results["pose_backend"] = test_pose_backend()
    results["isaac_sim"] = test_isaac_sim()
    # results["isaac_lab"] = test_isaac_lab()  # Skip if not in Isaac env
    results["project_structure"] = test_project_structure()

    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("SUMMARY")
    logger.info("=" * 60)

    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        logger.info(f"{test_name:20s}: {status}")

    all_passed = all(results.values())

    logger.info("=" * 60)

    if all_passed:
        logger.info("✓ All tests passed!")
        return 0
    else:
        logger.info("✗ Some tests failed. See docs/SETUP.md for installation instructions.")
        return 1


def main():
    parser = argparse.ArgumentParser(description="Project GROOT smoke test")

    parser.add_argument(
        "--test",
        type=str,
        default="all",
        choices=["all", "gpu", "isaac_sim", "isaac_lab", "pose", "deps", "structure"],
        help="Test to run (default: all)",
    )

    args = parser.parse_args()

    if args.test == "all":
        return test_all()
    elif args.test == "gpu":
        return 0 if test_gpu() else 1
    elif args.test == "isaac_sim":
        return 0 if test_isaac_sim() else 1
    elif args.test == "isaac_lab":
        return 0 if test_isaac_lab() else 1
    elif args.test == "pose":
        return 0 if test_pose_backend() else 1
    elif args.test == "deps":
        return 0 if test_dependencies() else 1
    elif args.test == "structure":
        return 0 if test_project_structure() else 1


if __name__ == "__main__":
    sys.exit(main())
