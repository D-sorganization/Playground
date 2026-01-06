"""
Project GROOT Setup

Install Project GROOT as a Python package.
"""

from setuptools import setup, find_packages
from pathlib import Path

# Read README
readme_file = Path(__file__).parent / "README.md"
long_description = readme_file.read_text() if readme_file.exists() else ""

# Read requirements
requirements_file = Path(__file__).parent / "requirements.txt"
requirements = []
if requirements_file.exists():
    with open(requirements_file) as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

setup(
    name="project-groot",
    version="0.1.0",
    description="Golf swing training with NVIDIA Isaac GR00T",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Project GROOT Team",
    author_email="",
    url="https://github.com/your-org/Project_GROOT",
    packages=find_packages(where="."),
    package_dir={"": "."},
    python_requires=">=3.10",
    install_requires=requirements,
    extras_require={
        "dev": [
            "pytest>=7.4.2",
            "pytest-cov>=4.1.0",
            "black>=23.9.1",
            "flake8>=6.1.0",
            "mypy>=1.5.1",
            "isort>=5.12.0",
        ],
        "mmpose": [
            "openmim",
            "mmengine",
            "mmcv>=2.0.0",
            "mmdet>=3.0.0",
            "mmpose>=1.2.0",
        ],
    },
    entry_points={
        "console_scripts": [
            "groot-ingest=tools.video_ingest:main",
            "groot-pose=tools.pose_convert:main",
            "groot-club=tools.club_track:main",
            "groot-retarget=tools.retarget_to_sim:main",
            "groot-train=train.imitation_train:main",
            "groot-rl=train.rl_finetune:main",
            "groot-eval=eval.rollout_eval:main",
        ],
    },
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Science/Research",
        "Topic :: Scientific/Engineering :: Artificial Intelligence",
        "Topic :: Scientific/Engineering :: Robotics",
        "Programming Language :: Python :: 3.10",
    ],
    keywords="robotics, golf, isaac-sim, isaac-lab, groot, imitation-learning, reinforcement-learning",
)
