# Project GROOT Docker Container
# Based on NVIDIA Isaac Sim base image

# Use NVIDIA Isaac Sim as base
# Note: Adjust version to match VERSION_PINNING.md
FROM nvcr.io/nvidia/isaac-sim:4.2.0

# Metadata
LABEL maintainer="Project GROOT Team"
LABEL description="Golf swing training environment with NVIDIA Isaac GR00T"

# Set environment variables
ENV DEBIAN_FRONTEND=noninteractive
ENV ISAAC_SIM_PATH=/isaac-sim
ENV PROJECT_GROOT_PATH=/workspace/Project_GROOT
ENV PYTHONPATH="${PROJECT_GROOT_PATH}:${PYTHONPATH}"

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    wget \
    curl \
    vim \
    tmux \
    htop \
    build-essential \
    cmake \
    libgl1-mesa-glx \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libglu1-mesa \
    libxi6 \
    libxrandr2 \
    libxcursor1 \
    libxinerama1 \
    && rm -rf /var/lib/apt/lists/*

# Create workspace directory
WORKDIR /workspace

# Clone Isaac Lab (if not mounted)
# RUN git clone https://github.com/isaac-sim/IsaacLab.git /workspace/IsaacLab \
#     && cd /workspace/IsaacLab \
#     && git checkout v1.2.0

# Install Python dependencies
# Copy requirements first for better layer caching
COPY requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Install additional pose estimation backends (optional)
# Uncomment if using MMPose
# RUN pip install openmim && \
#     mim install mmengine && \
#     mim install "mmcv>=2.0.0" && \
#     mim install "mmdet>=3.0.0" && \
#     mim install "mmpose>=1.2.0"

# Copy Project GROOT code
COPY . ${PROJECT_GROOT_PATH}

# Install Project GROOT in editable mode
RUN cd ${PROJECT_GROOT_PATH} && pip install -e .

# Create data directories
RUN mkdir -p ${PROJECT_GROOT_PATH}/data/{raw_video,processed_pose,retargeted_demos} \
    && mkdir -p ${PROJECT_GROOT_PATH}/train/outputs \
    && mkdir -p ${PROJECT_GROOT_PATH}/eval/outputs

# Set working directory
WORKDIR ${PROJECT_GROOT_PATH}

# Expose ports
EXPOSE 8888  # Jupyter
EXPOSE 6006  # TensorBoard
EXPOSE 8080  # Web UI

# Default command
CMD ["/bin/bash"]
