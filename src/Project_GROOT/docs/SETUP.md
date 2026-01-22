# Project GROOT Setup Guide

This guide walks you through setting up the complete Project GROOT environment from scratch.

## Prerequisites

### Hardware
- NVIDIA GPU with 10GB+ VRAM (RTX 3080 or better recommended)
- 32GB+ system RAM
- 100GB+ free disk space
- CPU: 8+ cores recommended

### Software
- Ubuntu 22.04 LTS
- NVIDIA Driver 535+ installed
- Git
- Internet connection for downloads

## Quick Start (Docker - Recommended)

```bash
# 1. Clone the repository
cd /path/to/workspace
git clone <your-repo-url> Project_GROOT
cd Project_GROOT

# 2. Build the Docker container
./scripts/docker_build.sh

# 3. Run the container
./scripts/docker_run.sh

# 4. Inside container, verify installation
python tools/smoke_test.py
```

## Detailed Setup (Native Installation)

### Step 1: NVIDIA Driver & CUDA

```bash
# Check current driver version
nvidia-smi

# If driver is older than 535, update it:
# (Only if needed - skip if driver is already installed)
sudo apt update
sudo apt install -y nvidia-driver-535
sudo reboot

# After reboot, verify
nvidia-smi

# Install CUDA Toolkit 12.1
wget https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2204/x86_64/cuda-keyring_1.0-1_all.deb
sudo dpkg -i cuda-keyring_1.0-1_all.deb
sudo apt update
sudo apt install -y cuda-toolkit-12-1

# Add to PATH (add to ~/.bashrc for persistence)
export PATH=/usr/local/cuda-12.1/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda-12.1/lib64:$LD_LIBRARY_PATH

# Verify CUDA
nvcc --version
```

### Step 2: Isaac Sim Installation

#### Option A: Using Omniverse Launcher (GUI)
1. Download and install [Omniverse Launcher](https://www.nvidia.com/en-us/omniverse/download/)
2. Open Launcher → Exchange → Search "Isaac Sim"
3. Install Isaac Sim 4.2.0
4. Default installation: `~/.local/share/ov/pkg/isaac-sim-4.2.0/`

#### Option B: Standalone Installation (Headless/Server)
```bash
# Download standalone package
wget https://install.launcher.omniverse.nvidia.com/installers/omniverse-launcher-linux.AppImage
chmod +x omniverse-launcher-linux.AppImage

# Or use direct download link (requires NVIDIA developer account)
# Visit: https://developer.nvidia.com/isaac-sim
```

#### Verify Isaac Sim Installation
```bash
# Set Isaac Sim path
export ISAAC_SIM_PATH="${HOME}/.local/share/ov/pkg/isaac-sim-4.2.0"

# Test basic launch (headless)
${ISAAC_SIM_PATH}/python.sh -c "import omni; print('Isaac Sim OK')"
```

### Step 3: Isaac Lab Installation

```bash
# Create workspace directory
mkdir -p ~/isaac_workspace
cd ~/isaac_workspace

# Clone Isaac Lab
git clone https://github.com/isaac-sim/IsaacLab.git
cd IsaacLab

# Checkout specific version
git checkout v1.2.0

# Create symlink to Isaac Sim (adjust path if different)
ln -s ~/.local/share/ov/pkg/isaac-sim-4.2.0 _isaac_sim

# Run Isaac Lab installer
./isaaclab.sh --install

# Verify installation
./isaaclab.sh -p source/standalone/workflows/rl_games/train.py --help
```

### Step 4: Isaac GR00T Installation

```bash
cd ~/isaac_workspace

# Clone GR00T repository
git clone https://github.com/NVlabs/isaac-groot.git
cd isaac-groot

# Record commit for reproducibility
git rev-parse HEAD > ../Project_GROOT/docs/groot_commit.txt

# Install GR00T dependencies
pip install -e .

# Download pretrained models (if available)
# mkdir -p checkpoints
# Follow instructions in GR00T repo for model downloads
```

### Step 5: Project GROOT Environment

```bash
cd ~/isaac_workspace/Project_GROOT

# Create Python virtual environment (optional but recommended)
python3.10 -m venv venv
source venv/bin/activate

# Install Project GROOT dependencies
pip install -r requirements.txt

# Install Project GROOT in editable mode
pip install -e .

# Verify installation
python -c "import project_groot; print('Project GROOT OK')"
```

### Step 6: Pose Estimation Setup

Choose one pose estimation backend:

#### Option A: MediaPipe (Easiest)
```bash
pip install mediapipe==0.10.7
python -c "import mediapipe; print('MediaPipe OK')"
```

#### Option B: MMPose (Most Accurate)
```bash
pip install openmim
mim install mmengine
mim install "mmcv>=2.0.0"
mim install "mmdet>=3.0.0"
mim install "mmpose>=1.2.0"

# Download pretrained model
mkdir -p data/pose_models
cd data/pose_models
wget https://download.openmmlab.com/mmpose/v1/projects/rtmposev1/rtmpose-l_8xb64-270e_coco-wholebody-384x288-eaeb96c8_20231016.pth
cd ../..
```

#### Option C: OpenPose (GPU Accelerated)
```bash
# See OpenPose documentation for installation
# https://github.com/CMU-Perceptual-Computing-Lab/openpose
```

### Step 7: Environment Variables

Add to `~/.bashrc` or create `env.sh`:

```bash
# Isaac Sim
export ISAAC_SIM_PATH="${HOME}/.local/share/ov/pkg/isaac-sim-4.2.0"
export ISAAC_LAB_PATH="${HOME}/isaac_workspace/IsaacLab"

# CUDA
export PATH=/usr/local/cuda-12.1/bin:$PATH
export LD_LIBRARY_PATH=/usr/local/cuda-12.1/lib64:$LD_LIBRARY_PATH

# Project GROOT
export PROJECT_GROOT_PATH="${HOME}/isaac_workspace/Project_GROOT"
export PYTHONPATH="${PROJECT_GROOT_PATH}:${ISAAC_LAB_PATH}/source:${PYTHONPATH}"

# Pose estimation models
export POSE_MODEL_PATH="${PROJECT_GROOT_PATH}/data/pose_models"

# Experiment tracking (optional)
# export WANDB_API_KEY="your_key_here"
```

Source the environment:
```bash
source ~/.bashrc
# or
source env.sh
```

## Smoke Tests

### Test 1: GPU & Driver
```bash
python tools/smoke_test.py --test gpu
```

Expected output:
```
✓ NVIDIA driver detected: 535.104.05
✓ CUDA available: 12.1
✓ GPU: NVIDIA GeForce RTX 4090 (24GB)
✓ GPU test PASSED
```

### Test 2: Isaac Sim
```bash
python tools/smoke_test.py --test isaac_sim
```

Expected output:
```
✓ Isaac Sim found at: /home/user/.local/share/ov/pkg/isaac-sim-4.2.0
✓ Can import omni modules
✓ Isaac Sim test PASSED
```

### Test 3: Isaac Lab
```bash
python tools/smoke_test.py --test isaac_lab
```

Expected output:
```
✓ Isaac Lab found at: /home/user/isaac_workspace/IsaacLab
✓ Can import omni.isaac.lab
✓ Isaac Lab test PASSED
```

### Test 4: Full Pipeline
```bash
python tools/smoke_test.py --test all
```

This runs all tests plus:
- Pose estimation backend
- Data pipeline tools
- Training environment
- Model loading

## Docker Setup (Alternative)

### Build Container

```bash
# From Project_GROOT root
docker build -t project-groot:latest -f .devcontainer/Dockerfile .
```

### Run Container

```bash
# Interactive mode
docker run --gpus all -it \
  -v $(pwd):/workspace/Project_GROOT \
  -v ~/isaac_workspace/IsaacLab:/workspace/IsaacLab \
  -v ~/isaac_workspace/isaac-groot:/workspace/isaac-groot \
  --shm-size=8g \
  project-groot:latest

# With display forwarding (for visualization)
xhost +local:docker
docker run --gpus all -it \
  -v $(pwd):/workspace/Project_GROOT \
  -v /tmp/.X11-unix:/tmp/.X11-unix \
  -e DISPLAY=$DISPLAY \
  --shm-size=8g \
  project-groot:latest
```

### Using Docker Compose

```bash
docker compose up -d
docker compose exec groot bash
```

## Troubleshooting

### Issue: "CUDA out of memory"
**Solution**: Reduce batch size in `train/configs/imitation_config.yaml`
```yaml
train:
  batch_size: 64  # Reduce to 32 or 16
```

### Issue: "Isaac Sim not found"
**Solution**: Verify ISAAC_SIM_PATH is correct
```bash
ls $ISAAC_SIM_PATH/python.sh  # Should exist
```

### Issue: "Module 'omni.isaac.lab' not found"
**Solution**: Check PYTHONPATH includes Isaac Lab
```bash
echo $PYTHONPATH | grep IsaacLab  # Should show path
source env.sh  # Re-source environment
```

### Issue: "Pose estimation fails"
**Solution**: Verify pose backend installation
```bash
python -c "import mediapipe; print(mediapipe.__version__)"
# or
python -c "import mmpose; print(mmpose.__version__)"
```

### Issue: Docker GPU not available
**Solution**: Install NVIDIA Container Toolkit
```bash
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -s -L https://nvidia.github.io/nvidia-docker/gpgkey | sudo apt-key add -
curl -s -L https://nvidia.github.io/nvidia-docker/$distribution/nvidia-docker.list | \
  sudo tee /etc/apt/sources.list.d/nvidia-docker.list

sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker

# Test
docker run --rm --gpus all nvidia/cuda:12.1.0-base-ubuntu22.04 nvidia-smi
```

## Verification Checklist

After completing setup, verify:

- [ ] `nvidia-smi` shows GPU and driver
- [ ] `nvcc --version` shows CUDA 12.1
- [ ] Isaac Sim launches: `$ISAAC_SIM_PATH/python.sh`
- [ ] Isaac Lab imports: `python -c "import omni.isaac.lab"`
- [ ] GR00T imports: `python -c "import isaac_groot"`
- [ ] Pose backend works: `python -c "import mediapipe"` (or mmpose)
- [ ] Smoke tests pass: `python tools/smoke_test.py --test all`
- [ ] Sample data exists: `ls data/raw_video/sample_swing.mp4`

## Next Steps

After successful setup:
1. Review `docs/RUNBOOK.md` for pipeline usage
2. Place sample golf swing video in `data/raw_video/`
3. Run end-to-end pipeline: `./scripts/run_vertical_slice.sh`

## Support

For issues:
1. Check `docs/TROUBLESHOOTING.md`
2. Review Isaac Sim/Lab documentation
3. Open issue in Project GROOT repository
4. NVIDIA Isaac forums: https://forums.developer.nvidia.com/c/isaac
