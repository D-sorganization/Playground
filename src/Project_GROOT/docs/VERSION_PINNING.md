# Version Pinning

This document specifies the exact versions of all dependencies required for reproducible builds and deployments of Project GROOT.

## Core Dependencies

### NVIDIA Isaac Sim
- **Version**: 4.2.0
- **Download**: [NVIDIA Isaac Sim Downloads](https://developer.nvidia.com/isaac-sim)
- **Installation Path**: `/opt/nvidia/isaac-sim` (recommended)
- **Notes**: Requires NVIDIA Omniverse Launcher or standalone installer

### Isaac Lab (formerly Orbit)
- **Repository**: `https://github.com/isaac-sim/IsaacLab.git`
- **Commit/Tag**: `v1.2.0` (or latest stable at time of setup)
- **Branch**: `main`
- **Installation**: Source installation via pip editable mode

### NVIDIA Isaac GR00T
- **Repository**: `https://github.com/NVlabs/isaac-groot.git`
- **Commit**: `HEAD` of `main` (pin to specific commit after initial setup)
- **Notes**: GR00T N1.x models - download pre-trained checkpoints separately

## GPU & Drivers

### NVIDIA Driver
- **Minimum Version**: 535.104.05 or newer
- **Recommended**: Latest production branch driver (545.x or 550.x series)
- **Verify**: `nvidia-smi`

### CUDA Toolkit
- **Version**: 12.1.0 or 12.2.0
- **Download**: [CUDA Toolkit Archive](https://developer.nvidia.com/cuda-toolkit-archive)
- **Notes**: Must be compatible with Isaac Sim and PyTorch versions

### GPU Requirements
- **Minimum**: NVIDIA RTX 3080 (10GB VRAM) or Tesla T4
- **Recommended**: NVIDIA RTX 4090, A6000, or A100
- **VRAM**: Minimum 10GB, recommended 24GB+

## Python Environment

### Python
- **Version**: 3.10.12
- **Notes**: Isaac Sim ships with its own Python; use that for Isaac Sim tasks

### Key Python Packages
```
# Core ML/RL
torch==2.1.0+cu121
torchvision==0.16.0+cu121
numpy==1.24.3
scipy==1.11.2

# Robotics
mediapy==1.1.9
opencv-python==4.8.1.78
pillow==10.0.1

# Pose Estimation (options)
# Choose one based on your pose estimation strategy
mediapipe==0.10.7          # Option 1: MediaPipe
mmpose==1.2.0              # Option 2: MMPose
openpose-python==0.0.1     # Option 3: OpenPose wrapper

# Isaac Lab dependencies (installed via IsaacLab setup)
omni-isaac-lab==1.2.0
gymnasium==0.29.1
stable-baselines3==2.1.0

# Utilities
tqdm==4.66.1
matplotlib==3.8.0
pandas==2.1.1
pyyaml==6.0.1
hydra-core==1.3.2
wandb==0.16.0              # Optional: for experiment tracking

# Development
pytest==7.4.2
black==23.9.1
flake8==6.1.0
mypy==1.5.1
```

## Operating System

### Ubuntu
- **Version**: 22.04 LTS (Jammy Jellyfish)
- **Kernel**: 5.15.0 or newer
- **Notes**: Ubuntu 20.04 may work but is not officially supported

### Docker (for containerized deployment)
- **Docker Engine**: 24.0.5 or newer
- **Docker Compose**: 2.20.0 or newer
- **NVIDIA Container Toolkit**: 1.14.0 or newer
- **Base Image**: `nvcr.io/nvidia/isaac-sim:4.2.0`

## Version Verification Commands

Run these commands to verify your environment:

```bash
# GPU & Driver
nvidia-smi
nvcc --version

# Python
python3 --version
pip --version

# Isaac Sim (from Isaac Sim directory)
./python.sh --version

# Docker (if using containers)
docker --version
docker compose version
nvidia-container-cli --version
```

## Pinning Strategy

### During Development
- Use `requirements.txt` with exact versions (`==`)
- Lock all transitive dependencies with `pip freeze > requirements-lock.txt`
- Commit both files to version control

### For Production/Reproducibility
- Use Docker with multi-stage builds
- Pin base image digest: `nvcr.io/nvidia/isaac-sim:4.2.0@sha256:...`
- Include apt package versions in Dockerfile
- Generate SBOM (Software Bill of Materials)

## Update Policy

### Security Updates
- Apply CUDA/driver security patches immediately
- Update PyTorch/dependencies monthly
- Review NVIDIA security bulletins

### Feature Updates
- Isaac Sim/Lab: Update quarterly after testing
- GR00T models: Update when new checkpoints released
- Python packages: Update minor versions after regression testing

## Known Compatibility Issues

### Isaac Sim 4.2.0
- Incompatible with CUDA 11.x (requires 12.x)
- Requires specific numpy version (<1.25)
- Ubuntu 22.04 required for full RTX support

### PyTorch 2.1.0
- Must use CUDA 12.1 wheels specifically
- Avoid PyTorch 2.2+ until Isaac Lab compatibility confirmed

### MediaPipe
- GPU inference requires additional setup
- CPU-only mode is default and sufficient for preprocessing

## Reproducibility Checklist

- [ ] Driver version recorded: `nvidia-smi | head -n 3 > driver_info.txt`
- [ ] Python packages frozen: `pip freeze > requirements-lock.txt`
- [ ] Isaac Sim version verified: `cat ~/.local/share/ov/pkg/isaac-sim-*/VERSION`
- [ ] GR00T commit hash recorded: `git rev-parse HEAD > groot_commit.txt`
- [ ] CUDA version verified: `nvcc --version > cuda_version.txt`
- [ ] All versions committed to repo under `docs/snapshots/`

## References

- [Isaac Sim Release Notes](https://docs.omniverse.nvidia.com/isaacsim/latest/release_notes.html)
- [Isaac Lab Documentation](https://isaac-sim.github.io/IsaacLab/)
- [NVIDIA Driver Downloads](https://www.nvidia.com/download/index.aspx)
- [PyTorch Version Compatibility](https://pytorch.org/get-started/previous-versions/)
