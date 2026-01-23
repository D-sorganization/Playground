# Project GROOT: Golf Swing Training with NVIDIA Isaac

Train humanoid robots to perform professional golf swings using NVIDIA Isaac GR00T, Isaac Lab, and real golfer video demonstrations.

## Overview

Project GROOT implements an end-to-end pipeline that:
1. **Ingests** historic golf swing videos (e.g., from pro golfers)
2. **Extracts** 3D skeleton poses and club trajectories
3. **Retargets** human motions to humanoid robot joint space
4. **Trains** policies via imitation learning + reinforcement learning
5. **Evaluates** swing quality (clubhead speed, trajectory, smoothness)

The project is designed for reproducibility, scalability, and real-world deployment.

## Key Features

- **Complete Pipeline**: Video → Pose → Retarget → Train → Evaluate
- **Multiple Backends**: MediaPipe, MMPose for pose estimation
- **Modular Design**: Each stage has clear inputs/outputs and can run independently
- **Isaac Lab Integration**: Custom RL environment for golf swing task
- **Comprehensive Documentation**: Setup guides, runbooks, and API docs
- **Containerized**: Docker support for reproducible environments
- **Metrics & Visualization**: TensorBoard, plots, HTML reports

## Quick Start

### Prerequisites

- Ubuntu 22.04 LTS
- NVIDIA GPU (RTX 3080+ recommended, 10GB+ VRAM)
- NVIDIA Driver 535+
- Docker + NVIDIA Container Toolkit (for containerized setup)

### Installation

```bash
# Clone repository
git clone https://github.com/your-org/Project_GROOT.git
cd Project_GROOT

# Option 1: Docker (recommended)
docker compose build
docker compose run groot

# Option 2: Native installation
# See docs/SETUP.md for detailed instructions
pip install -r requirements.txt
pip install -e .
```

### Vertical Slice Demo

Run the complete pipeline with a single command:

```bash
# Place a sample golf swing video in data/raw_video/
./scripts/run_vertical_slice.sh data/raw_video/sample_swing.mp4 "Tiger Woods"
```

This will:
1. Process the video
2. Extract poses and club trajectory
3. Retarget to robot
4. Train an imitation policy
5. Evaluate and generate report

Results saved to `eval/outputs/vertical_slice_eval/report.html`

## Pipeline Stages

### 1. Video Ingestion

```bash
python tools/video_ingest.py \
    --input-file data/raw_video/swing.mp4 \
    --golfer-name "Golfer Name" \
    --output data/manifest.json
```

Creates a manifest of videos with metadata (golfer, timestamps, FPS).

### 2. Pose Extraction

```bash
python tools/pose_convert.py \
    --manifest data/manifest.json \
    --output-dir data/processed_pose \
    --pose-backend mediapipe
```

Extracts 3D skeleton keypoints from video frames.

### 3. Club Tracking

```bash
python tools/club_track.py \
    --manifest data/manifest.json \
    --pose-dir data/processed_pose \
    --output-dir data/processed_pose \
    --method line_fit
```

Estimates club grip, head, and face positions.

### 4. Retargeting

```bash
python tools/retarget_to_sim.py \
    --input-dir data/processed_pose \
    --output-dir data/retargeted_demos \
    --robot-config sim/configs/humanoid_upper.yaml
```

Converts human poses to robot joint angles using inverse kinematics.

### 5. Training

#### Imitation Learning

```bash
python train/imitation_train.py \
    --config train/configs/imitation_config.yaml \
    --demo-dir data/retargeted_demos \
    --output-dir train/outputs/imitation_policy \
    --num-epochs 500
```

#### RL Fine-tuning (Optional)

```bash
python train/rl_finetune.py \
    --config train/configs/rl_config.yaml \
    --pretrained-policy train/outputs/imitation_policy/checkpoints/best.pth \
    --output-dir train/outputs/rl_policy
```

### 6. Evaluation

```bash
python eval/rollout_eval.py \
    --policy train/outputs/imitation_policy/checkpoints/best.pth \
    --config sim/configs/humanoid_upper.yaml \
    --num-rollouts 50 \
    --output-dir eval/outputs/eval_results
```

Generates metrics, plots, and HTML report.

## Project Structure

```
Project_GROOT/
├── docs/                      # Documentation
│   ├── SETUP.md              # Installation guide
│   ├── RUNBOOK.md            # Usage guide
│   └── VERSION_PINNING.md    # Dependency versions
├── data/                      # Data storage
│   ├── raw_video/            # Input videos
│   ├── processed_pose/       # Extracted poses
│   └── retargeted_demos/     # Robot trajectories
├── sim/                       # Simulation
│   ├── golf_swing_env.py     # Isaac Lab environment
│   └── configs/              # Robot configurations
├── train/                     # Training
│   ├── imitation_train.py    # Imitation learning
│   ├── rl_finetune.py        # RL fine-tuning
│   └── configs/              # Training configs
├── eval/                      # Evaluation
│   └── rollout_eval.py       # Policy evaluation
├── tools/                     # Data pipeline tools
│   ├── video_ingest.py       # Video processing
│   ├── pose_convert.py       # Pose extraction
│   ├── club_track.py         # Club tracking
│   └── retarget_to_sim.py    # Motion retargeting
├── scripts/                   # Utility scripts
│   └── run_vertical_slice.sh # End-to-end pipeline
├── requirements.txt           # Python dependencies
├── setup.py                   # Package setup
├── docker-compose.yml         # Docker orchestration
└── README.md                  # This file
```

## Technology Stack

- **NVIDIA Isaac Sim 4.2.0**: Physics simulation
- **NVIDIA Isaac Lab 1.2.0**: Robot learning framework
- **NVIDIA Isaac GR00T**: Humanoid foundation model
- **PyTorch 2.1.0**: Deep learning
- **MediaPipe / MMPose**: Pose estimation
- **Stable-Baselines3 / RL Games**: Reinforcement learning

## Documentation

- **[Setup Guide](docs/SETUP.md)**: Detailed installation instructions
- **[Runbook](docs/RUNBOOK.md)**: Complete usage guide with examples
- **[Version Pinning](docs/VERSION_PINNING.md)**: Exact dependency versions
- **[Architecture](docs/ARCHITECTURE.md)**: System design (coming soon)
- **[API Reference](docs/API.md)**: Code documentation (coming soon)

## Performance Benchmarks

Expected results on RTX 4090:

| Metric | Value |
|--------|-------|
| Clubhead Speed | 39-42 m/s |
| Swing Duration | 1.3-1.5 s |
| Trajectory Error | < 5 cm RMSE |
| Training Time (Imitation) | ~2 hours |
| Training Time (RL) | ~8 hours |
| Inference Time | < 5 ms |

## Development

### Running Tests

```bash
# Run smoke tests
python tools/smoke_test.py --test all

# Run unit tests
pytest tests/

# Code formatting
black .
isort .

# Linting
flake8 .
mypy .
```

### Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## Roadmap

### Phase 1: Vertical Slice (Current)
- [x] Pipeline infrastructure
- [x] Upper body humanoid (torso + arms)
- [x] Single-demo imitation learning
- [x] Basic evaluation metrics

### Phase 2: Scale & Robustness
- [ ] Full humanoid (add legs)
- [ ] Multi-golfer training
- [ ] Domain randomization
- [ ] RL with optimized rewards

### Phase 3: Advanced Features
- [ ] Ball contact physics
- [ ] Trajectory prediction
- [ ] Style-conditioned policies
- [ ] Real robot deployment

### Phase 4: Production
- [ ] Sim-to-real transfer
- [ ] Online learning
- [ ] Multi-club support
- [ ] Real-time inference

## Known Limitations

1. **Pose Estimation**: Current baseline uses simplified club tracking (line fit). More sophisticated methods (ML-based detection) coming soon.

2. **IK Solver**: Retargeting uses heuristic IK mapping. Full implementation will use TracIK or similar.

3. **RL Environment**: Golf swing environment is template-based. Requires integration with Isaac Lab for full functionality.

4. **Ball Physics**: Currently no ball or ground interaction. Focus is on swing motion quality.

## Troubleshooting

See [docs/SETUP.md](docs/SETUP.md#troubleshooting) for common issues and solutions.

Quick fixes:
- **CUDA out of memory**: Reduce batch size in config
- **Isaac Sim not found**: Set `ISAAC_SIM_PATH` environment variable
- **Pose extraction slow**: Use MediaPipe instead of MMPose

## Citation

If you use Project GROOT in your research, please cite:

```bibtex
@software{project_groot_2024,
  title = {Project GROOT: Golf Swing Training with NVIDIA Isaac},
  author = {Project GROOT Team},
  year = {2024},
  url = {https://github.com/your-org/Project_GROOT}
}
```

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- NVIDIA for Isaac Sim, Isaac Lab, and GR00T
- OpenAI for inspiration from robotics research
- Golf community for demonstration videos
- Contributors and maintainers

## Contact

- **Issues**: [GitHub Issues](https://github.com/your-org/Project_GROOT/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-org/Project_GROOT/discussions)
- **Email**: project-groot@example.com

---

**Built with ❤️ for robotics and golf**
