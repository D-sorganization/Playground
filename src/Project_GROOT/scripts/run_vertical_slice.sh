#!/bin/bash
# Project GROOT Vertical Slice Pipeline
# Runs the complete pipeline from video to trained policy

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default parameters
VIDEO=${1:-"data/raw_video/sample_swing.mp4"}
GOLFER=${2:-"Sample Golfer"}
OUTPUT_PREFIX="vertical_slice"

echo -e "${BLUE}================================================================${NC}"
echo -e "${BLUE}Project GROOT - Vertical Slice Pipeline${NC}"
echo -e "${BLUE}================================================================${NC}"
echo ""
echo -e "Video: ${GREEN}${VIDEO}${NC}"
echo -e "Golfer: ${GREEN}${GOLFER}${NC}"
echo ""

# Check if video exists
if [ ! -f "${VIDEO}" ]; then
    echo -e "${RED}Error: Video file not found: ${VIDEO}${NC}"
    echo "Please provide a valid video file path as the first argument."
    echo "Example: ./scripts/run_vertical_slice.sh data/raw_video/my_swing.mp4"
    exit 1
fi

# Stage 1: Data Ingestion
echo -e "${YELLOW}[Stage 1/5]${NC} Data Ingestion..."
python tools/video_ingest.py \
    --input-file "${VIDEO}" \
    --output data/manifest_${OUTPUT_PREFIX}.json \
    --golfer-name "${GOLFER}" \
    --video-source local

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Data ingestion complete${NC}"
else
    echo -e "${RED}✗ Data ingestion failed${NC}"
    exit 1
fi

# Stage 2: Pose Extraction
echo ""
echo -e "${YELLOW}[Stage 2/5]${NC} Pose Extraction..."
python tools/pose_convert.py \
    --manifest data/manifest_${OUTPUT_PREFIX}.json \
    --output-dir data/processed_pose \
    --pose-backend mediapipe \
    --confidence-threshold 0.5

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Pose extraction complete${NC}"
else
    echo -e "${RED}✗ Pose extraction failed${NC}"
    exit 1
fi

# Stage 2b: Club Tracking
echo ""
echo -e "${YELLOW}[Stage 2b/5]${NC} Club Tracking..."
python tools/club_track.py \
    --manifest data/manifest_${OUTPUT_PREFIX}.json \
    --pose-dir data/processed_pose \
    --output-dir data/processed_pose \
    --method line_fit

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Club tracking complete${NC}"
else
    echo -e "${RED}✗ Club tracking failed${NC}"
    exit 1
fi

# Stage 3: Retargeting
echo ""
echo -e "${YELLOW}[Stage 3/5]${NC} Retargeting to Robot..."
python tools/retarget_to_sim.py \
    --input-dir data/processed_pose \
    --output-dir data/retargeted_demos \
    --robot-config sim/configs/humanoid_upper.yaml \
    --smooth-window 5

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Retargeting complete${NC}"
else
    echo -e "${RED}✗ Retargeting failed${NC}"
    exit 1
fi

# Stage 4: Training (Quick imitation for vertical slice)
echo ""
echo -e "${YELLOW}[Stage 4/5]${NC} Training Policy (Imitation)..."
python train/imitation_train.py \
    --config train/configs/imitation_config.yaml \
    --demo-dir data/retargeted_demos \
    --output-dir train/outputs/${OUTPUT_PREFIX}_policy \
    --num-epochs 100 \
    --batch-size 32

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Training complete${NC}"
else
    echo -e "${RED}✗ Training failed${NC}"
    exit 1
fi

# Stage 5: Evaluation
echo ""
echo -e "${YELLOW}[Stage 5/5]${NC} Evaluating Policy..."
python eval/rollout_eval.py \
    --policy train/outputs/${OUTPUT_PREFIX}_policy/checkpoints/best.pth \
    --config sim/configs/humanoid_upper.yaml \
    --num-rollouts 10 \
    --output-dir eval/outputs/${OUTPUT_PREFIX}_eval \
    --record-video

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Evaluation complete${NC}"
else
    echo -e "${RED}✗ Evaluation failed${NC}"
    exit 1
fi

# Summary
echo ""
echo -e "${BLUE}================================================================${NC}"
echo -e "${GREEN}✓ Vertical Slice Pipeline Complete!${NC}"
echo -e "${BLUE}================================================================${NC}"
echo ""
echo "Results:"
echo -e "  Training outputs: ${GREEN}train/outputs/${OUTPUT_PREFIX}_policy/${NC}"
echo -e "  Evaluation results: ${GREEN}eval/outputs/${OUTPUT_PREFIX}_eval/${NC}"
echo -e "  HTML report: ${GREEN}eval/outputs/${OUTPUT_PREFIX}_eval/report.html${NC}"
echo ""
echo "Next steps:"
echo "  1. Review evaluation metrics in the HTML report"
echo "  2. Add more demonstration videos for better training"
echo "  3. Run RL fine-tuning: python train/rl_finetune.py ..."
echo "  4. Scale to full humanoid (add legs)"
echo ""
