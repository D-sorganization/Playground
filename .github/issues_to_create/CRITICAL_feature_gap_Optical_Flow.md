---
title: "CRITICAL: Feature Gap - Optical Flow Tracking Missing"
labels: ["incomplete-implementation", "critical"]
---

# Issue: Feature Gap - Optical Flow Tracking Missing

## Description
The Optical Flow Tracking method is marked as "coming soon" and remains unimplemented in the club trajectory tracking module. When calling this tracking method, a `NotImplementedError` is raised.

- File: `src/Project_GROOT/tools/club_track.py`
- Line: 169

## Impact
Users specifying `method="optical_flow"` for club tracking will face a runtime crash. The codebase relies solely on the baseline `line_fit` methodology.

## Action Required
- Implement optical flow tracking algorithms (e.g., using OpenCV) inside `_track_optical_flow`.
- Remove the `NotImplementedError` stub.
