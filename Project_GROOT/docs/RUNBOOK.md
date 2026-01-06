# Project GROOT Runbook

This runbook provides step-by-step instructions for running the complete Project GROOT pipeline from raw video to trained golf swing policy.

## Overview

The pipeline consists of 5 main stages:
1. **Data Ingestion**: Process raw golf swing videos
2. **Pose Extraction**: Extract skeleton keypoints and club tracking
3. **Retargeting**: Map human poses to robot joint space
4. **Training**: Learn policy via imitation (+ optional RL)
5. **Evaluation**: Rollout policy and measure performance

## Prerequisites

- Completed setup from `docs/SETUP.md`
- All smoke tests passing
- At least one sample golf swing video in `data/raw_video/`

## Quick Start: Vertical Slice

Run the entire pipeline with a single command:

```bash
# From Project_GROOT root
./scripts/run_vertical_slice.sh

# Or with specific video
./scripts/run_vertical_slice.sh data/raw_video/sample_swing.mp4
```

This script executes all stages sequentially and produces a trained policy.

## Stage-by-Stage Execution

### Stage 1: Data Ingestion

**Purpose**: Create a manifest of video clips with metadata.

**Input**: Raw video files in `data/raw_video/`

**Output**: `data/manifest.json` with video metadata

```bash
# Create manifest from all videos in raw_video/
python tools/video_ingest.py \
  --input-dir data/raw_video \
  --output data/manifest.json \
  --golfer-name "Tiger Woods" \
  --video-source "youtube" \
  --fps 30

# Or specify clip timestamps for specific swing
python tools/video_ingest.py \
  --input-file data/raw_video/sample_swing.mp4 \
  --output data/manifest.json \
  --golfer-name "Sample Golfer" \
  --start-time 0.0 \
  --end-time 3.0 \
  --fps 30

# Verify manifest
cat data/manifest.json | jq .
```

**Expected output**:
```json
{
  "videos": [
    {
      "id": "sample_swing_001",
      "golfer": "Tiger Woods",
      "video_path": "data/raw_video/sample_swing.mp4",
      "source": "youtube",
      "start_frame": 0,
      "end_frame": 90,
      "fps": 30,
      "duration": 3.0,
      "swing_type": "driver",
      "metadata": {}
    }
  ]
}
```

### Stage 2: Pose Extraction & Club Tracking

**Purpose**: Extract 3D skeleton poses and club trajectory from videos.

**Input**: `data/manifest.json`, videos in `data/raw_video/`

**Output**: `data/processed_pose/*.npz` files with skeleton + club data

```bash
# Extract poses using MediaPipe (default)
python tools/pose_convert.py \
  --manifest data/manifest.json \
  --output-dir data/processed_pose \
  --pose-backend mediapipe \
  --confidence-threshold 0.5 \
  --visualize

# Or use MMPose for better accuracy
python tools/pose_convert.py \
  --manifest data/manifest.json \
  --output-dir data/processed_pose \
  --pose-backend mmpose \
  --config configs/mmpose_wholebody.py \
  --checkpoint data/pose_models/rtmpose-l_8xb64-270e_coco-wholebody-384x288-eaeb96c8_20231016.pth

# Verify output
python -c "
import numpy as np
data = np.load('data/processed_pose/sample_swing_001.npz')
print('Keys:', list(data.keys()))
print('Skeleton shape:', data['skeleton'].shape)  # (T, num_joints, 3)
print('Club shape:', data['club'].shape)  # (T, 2, 3) - grip + head
"
```

**Extract club trajectory**:
```bash
# Basic club tracking (baseline)
python tools/club_track.py \
  --manifest data/manifest.json \
  --pose-dir data/processed_pose \
  --output-dir data/processed_pose \
  --method line_fit \
  --visualize

# Verify club data added
python -c "
import numpy as np
data = np.load('data/processed_pose/sample_swing_001.npz')
print('Club head positions:', data['club_head'][:5])  # First 5 frames
print('Club face normals:', data['club_face'][:5])
"
```

**Data format** (`data/processed_pose/sample_swing_001.npz`):
- `skeleton`: (T, 33, 3) - xyz positions of body keypoints
- `skeleton_confidence`: (T, 33) - detection confidence per joint
- `club_grip`: (T, 3) - club grip position
- `club_head`: (T, 3) - clubhead position
- `club_face`: (T, 3) - clubface normal vector
- `timestamps`: (T,) - frame timestamps
- `phase_labels`: (T,) - swing phase: 0=address, 1=backswing, 2=downswing, 3=impact, 4=follow-through

### Stage 3: Retargeting to Robot

**Purpose**: Convert human skeleton poses to robot joint angles.

**Input**: `data/processed_pose/*.npz`

**Output**: `data/retargeted_demos/*.npz` with joint trajectories

```bash
# Retarget to Isaac humanoid (upper body focus)
python tools/retarget_to_sim.py \
  --input-dir data/processed_pose \
  --output-dir data/retargeted_demos \
  --robot-config sim/configs/humanoid_upper.yaml \
  --ik-solver trac_ik \
  --smooth-window 5 \
  --visualize

# Verify retargeting
python -c "
import numpy as np
data = np.load('data/retargeted_demos/sample_swing_001.npz')
print('Joint positions:', data['q'].shape)  # (T, num_dofs)
print('Joint velocities:', data['qdot'].shape)  # (T, num_dofs)
print('End-effector:', data['ee_pos'].shape)  # (T, 3) - club head in sim
print('DOF names:', data['dof_names'])
"

# Check for joint limit violations
python tools/validate_retarget.py \
  --input-dir data/retargeted_demos \
  --robot-config sim/configs/humanoid_upper.yaml
```

**Expected output**:
```
Processing: sample_swing_001.npz
✓ No joint limit violations
✓ Velocity limits OK (max: 4.2 rad/s)
✓ Acceleration OK (max: 15.3 rad/s²)
✓ No discontinuities detected
⚠ Warning: Clubhead speed 42.1 m/s (high but acceptable)
```

### Stage 4: Training

#### 4a. Imitation Learning

**Purpose**: Learn policy to reproduce retargeted demonstrations.

**Input**: `data/retargeted_demos/*.npz`

**Output**: Trained policy in `train/outputs/imitation_policy/`

```bash
# Train with default config
python train/imitation_train.py \
  --config train/configs/imitation_config.yaml \
  --demo-dir data/retargeted_demos \
  --output-dir train/outputs/imitation_policy \
  --num-epochs 500 \
  --batch-size 64 \
  --seed 42

# Monitor training (in separate terminal)
tensorboard --logdir train/outputs/imitation_policy/logs

# Training with Weights & Biases
python train/imitation_train.py \
  --config train/configs/imitation_config.yaml \
  --demo-dir data/retargeted_demos \
  --output-dir train/outputs/imitation_policy \
  --use-wandb \
  --wandb-project groot-golf \
  --wandb-run-name swing-imitation-v1
```

**Expected training logs**:
```
Epoch 1/500: loss=0.245, mse=0.189, kl_div=0.056
Epoch 50/500: loss=0.082, mse=0.071, kl_div=0.011
Epoch 100/500: loss=0.045, mse=0.041, kl_div=0.004
...
Epoch 500/500: loss=0.012, mse=0.011, kl_div=0.001
✓ Training complete. Best model: epoch_423.pth
```

**Resume training**:
```bash
python train/imitation_train.py \
  --config train/configs/imitation_config.yaml \
  --demo-dir data/retargeted_demos \
  --output-dir train/outputs/imitation_policy \
  --resume train/outputs/imitation_policy/checkpoints/latest.pth
```

#### 4b. RL Fine-tuning (Optional)

**Purpose**: Refine policy with reinforcement learning for better clubhead speed/accuracy.

**Input**: Pre-trained imitation policy

**Output**: Fine-tuned policy in `train/outputs/rl_policy/`

```bash
# RL fine-tuning with PPO
python train/rl_finetune.py \
  --config train/configs/rl_config.yaml \
  --pretrained-policy train/outputs/imitation_policy/checkpoints/best.pth \
  --output-dir train/outputs/rl_policy \
  --num-envs 256 \
  --num-steps 10000000 \
  --seed 42

# Monitor RL training
tensorboard --logdir train/outputs/rl_policy/logs
```

**Expected RL logs**:
```
Step 1000: reward=1.2, clubhead_speed=28.3 m/s, episode_len=90
Step 10000: reward=3.5, clubhead_speed=35.1 m/s, episode_len=87
Step 100000: reward=5.8, clubhead_speed=41.2 m/s, episode_len=85
...
✓ RL training complete. Best policy: step_950000.pth
```

### Stage 5: Evaluation

**Purpose**: Rollout trained policy and measure performance metrics.

**Input**: Trained policy checkpoint

**Output**: Metrics, plots, videos in `eval/outputs/`

```bash
# Evaluate imitation policy
python eval/rollout_eval.py \
  --policy train/outputs/imitation_policy/checkpoints/best.pth \
  --config sim/configs/humanoid_upper.yaml \
  --num-rollouts 50 \
  --output-dir eval/outputs/imitation_eval \
  --record-video \
  --seed 42

# Evaluate RL policy
python eval/rollout_eval.py \
  --policy train/outputs/rl_policy/checkpoints/best.pth \
  --config sim/configs/humanoid_upper.yaml \
  --num-rollouts 50 \
  --output-dir eval/outputs/rl_eval \
  --record-video

# Compare policies
python eval/compare_policies.py \
  --policies \
    train/outputs/imitation_policy/checkpoints/best.pth \
    train/outputs/rl_policy/checkpoints/best.pth \
  --labels "Imitation" "RL" \
  --output-dir eval/outputs/comparison
```

**Expected evaluation output**:
```
Running 50 rollouts...
[####################] 100%

Metrics Summary:
  Clubhead Speed: 39.2 ± 2.8 m/s (target: 40-45 m/s)
  Swing Duration: 1.42 ± 0.08 s (target: 1.2-1.5 s)
  Keyframe Timing Error: 0.034 ± 0.012 s
  Joint Limit Violations: 0.2% of timesteps
  Trajectory Smoothness: 0.87 (0-1 scale, higher better)

Phase Timing:
  Backswing: 0.65 ± 0.05 s
  Downswing: 0.28 ± 0.03 s
  Follow-through: 0.49 ± 0.04 s

✓ Evaluation complete. Results saved to eval/outputs/imitation_eval/
```

**View results**:
```bash
# Open HTML report
firefox eval/outputs/imitation_eval/report.html

# View videos
ls eval/outputs/imitation_eval/videos/*.mp4

# Check plots
ls eval/outputs/imitation_eval/plots/*.png
```

## Advanced Usage

### Multi-Golfer Training

```bash
# Ingest multiple golfers
python tools/video_ingest.py \
  --input-dir data/raw_video/tiger_woods \
  --golfer-name "Tiger Woods" \
  --output data/manifest_tiger.json

python tools/video_ingest.py \
  --input-dir data/raw_video/rory_mcilroy \
  --golfer-name "Rory McIlroy" \
  --output data/manifest_rory.json

# Merge manifests
python tools/merge_manifests.py \
  --inputs data/manifest_tiger.json data/manifest_rory.json \
  --output data/manifest_combined.json

# Train on combined dataset
python train/imitation_train.py \
  --config train/configs/imitation_config.yaml \
  --demo-dir data/retargeted_demos \
  --output-dir train/outputs/multi_golfer_policy
```

### Style-Conditioned Training

```bash
# Train policy conditioned on golfer style
python train/imitation_train.py \
  --config train/configs/imitation_config.yaml \
  --demo-dir data/retargeted_demos \
  --output-dir train/outputs/style_conditioned \
  --conditioning style \
  --num-styles 5  # Cluster swings into 5 styles
```

### Domain Randomization

```bash
# Add physics randomization during RL
python train/rl_finetune.py \
  --config train/configs/rl_config.yaml \
  --pretrained-policy train/outputs/imitation_policy/checkpoints/best.pth \
  --output-dir train/outputs/rl_policy_dr \
  --domain-randomization \
  --randomize-mass 0.1 \
  --randomize-friction 0.2 \
  --randomize-club-length 0.05
```

## Automation Scripts

### Full Pipeline Script

`scripts/run_vertical_slice.sh`:
```bash
#!/bin/bash
set -e

VIDEO=${1:-data/raw_video/sample_swing.mp4}
GOLFER=${2:-"Sample Golfer"}

echo "=== Project GROOT Vertical Slice Pipeline ==="
echo "Video: $VIDEO"
echo "Golfer: $GOLFER"

# Stage 1: Ingest
echo "[1/5] Data ingestion..."
python tools/video_ingest.py \
  --input-file $VIDEO \
  --output data/manifest.json \
  --golfer-name "$GOLFER"

# Stage 2: Pose
echo "[2/5] Pose extraction..."
python tools/pose_convert.py \
  --manifest data/manifest.json \
  --output-dir data/processed_pose \
  --pose-backend mediapipe

echo "[2/5] Club tracking..."
python tools/club_track.py \
  --manifest data/manifest.json \
  --pose-dir data/processed_pose \
  --output-dir data/processed_pose

# Stage 3: Retarget
echo "[3/5] Retargeting..."
python tools/retarget_to_sim.py \
  --input-dir data/processed_pose \
  --output-dir data/retargeted_demos \
  --robot-config sim/configs/humanoid_upper.yaml

# Stage 4: Train
echo "[4/5] Training (imitation)..."
python train/imitation_train.py \
  --config train/configs/imitation_config.yaml \
  --demo-dir data/retargeted_demos \
  --output-dir train/outputs/vertical_slice_policy \
  --num-epochs 100  # Quick training for vertical slice

# Stage 5: Evaluate
echo "[5/5] Evaluation..."
python eval/rollout_eval.py \
  --policy train/outputs/vertical_slice_policy/checkpoints/best.pth \
  --config sim/configs/humanoid_upper.yaml \
  --num-rollouts 10 \
  --output-dir eval/outputs/vertical_slice_eval \
  --record-video

echo "=== Pipeline Complete ==="
echo "Results: eval/outputs/vertical_slice_eval/report.html"
```

Make executable:
```bash
chmod +x scripts/run_vertical_slice.sh
```

## Troubleshooting

### Pipeline fails at pose extraction
- Check video format: should be MP4, AVI, or MOV
- Verify pose backend installed: `python -c "import mediapipe"`
- Reduce `--confidence-threshold` if many frames rejected

### Retargeting produces joint limit violations
- Increase `--smooth-window` to reduce noise
- Check if video angle is frontal (side view works best)
- Verify robot config joint limits are reasonable

### Training loss plateaus
- Increase model capacity in config
- Add more demonstration variety
- Check learning rate schedule
- Verify demonstrations are high quality (low retarget errors)

### RL training unstable
- Reduce learning rate
- Increase number of parallel environments
- Check reward scaling in config
- Ensure pretrained policy is good (test with imitation eval first)

### Evaluation shows poor clubhead speed
- Check retargeted demos have realistic speeds
- Tune RL reward weights (clubhead speed vs. smoothness)
- Increase training steps
- Verify club inertia parameters in sim config

## Performance Benchmarks

Expected timing on RTX 4090:

- Pose extraction: ~0.3s per frame (MediaPipe), ~0.8s (MMPose)
- Retargeting: ~0.1s per demo (90 frames)
- Imitation training: ~2 hours for 500 epochs (single demo)
- RL fine-tuning: ~8 hours for 10M steps (256 envs)
- Evaluation: ~1 min for 50 rollouts

## Next Steps

After completing vertical slice:
1. Add more demonstration data
2. Scale to full humanoid (add legs)
3. Implement ball contact physics
4. Add trajectory prediction rewards
5. Deploy to real robot (if available)

## References

- Isaac Lab examples: `$ISAAC_LAB_PATH/source/standalone/workflows/`
- GR00T documentation: `isaac-groot/docs/`
- Pipeline architecture: `docs/ARCHITECTURE.md`
