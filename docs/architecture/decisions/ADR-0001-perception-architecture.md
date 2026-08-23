# ADR-0001: Modular Perception Engine Architecture

## Status
Accepted (Volume 2)

## Context
The legacy prototype coupled detection, motion analysis, and tracking into a single monolithic script with hardcoded weights, magic numbers, and dynamic runtime pip execution (`_ensure()`).

## Decision
1. **Abstract Base Detectors**: Define `BaseDetector` and `BaseMotionDetector` to isolate deep learning and computer vision implementations.
2. **Multi-Cue Candidate Fusion**: Maintain independent evidence provenance (`yolo`, `motion`, `yolo+motion`) and fuse detections using spatial IoU with a transparent weighted candidate scoring formula.
3. **Strict Model Safety**: Eliminate runtime pip package installations and silent downloads. If model weights are missing or unreadable, raise a clear `ModelLoadError` with actionable configuration instructions when in strict mode, or fall back cleanly to motion detection.
4. **Offline Testability**: Implement `MockDetector` and synthetic test generators to ensure 100% of perception tests run deterministically in CI environments without GPU or external internet access.

## Consequences
- Clean separation of concerns between raw detection, temporal tracking (V3), and geometric pose estimation (V4+).
- Fully testable and configurable perception pipeline.
- Preserved backward compatibility for all existing V1 callers.
