---
title: "CRITICAL: Feature Gap - MMPose Backend Missing"
labels: ["incomplete-implementation", "critical"]
---

# Issue: Feature Gap - MMPose Backend Missing

## Description
The MMPose backend is designated as an upcoming feature but is currently missing. The `MMPosePoseExtractor.extract` method throws a `NotImplementedError` ("MMPose backend coming soon") acting as a placeholder stub.

- File: `src/Project_GROOT/tools/pose_extractors.py`
- Line: 164

## Impact
Users attempting to leverage the MMPose backend for accurate, GPU-accelerated pose estimation will encounter hard failures. Only the MediaPipe backend is currently viable.

## Action Required
- Implement MMPose integration utilizing `mmpose`, `mmdet`, and `mmcv`.
- Replace the `NotImplementedError` placeholder with real processing logic.
