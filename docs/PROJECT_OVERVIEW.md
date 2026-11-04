# RoverMind — Project Overview

## 1. Executive Summary

**RoverMind** is an AI-assisted planetary exploration decision-support and visualization system. Designed for Mars rover mission simulation, it processes monocular camera frames (such as Navcam and Hazcam RGB/grayscale imagery), extracts visual concept segmentations using Meta SAM 3.1, decodes and projects spatial masks onto a discrete coordinate grid, normalizes estimated terrain features into risk traversal costs, and calculates deterministic lower-cost routes using a custom A* path-planning engine.

---

## 2. Problem Statement & Motivation

Planetary surface rovers—such as NASA's Curiosity and Perseverance—operate under severe communication latency (ranging from 4 to 24 minutes one-way light time between Earth and Mars). Surface navigation requires high-fidelity hazard identification, traversability assessment, and tactical path planning. 

While terrestrial autonomous vehicles rely heavily on active LiDAR scans, stereo disparity maps, and dense real-time compute, planetary roboticists frequently rely on decision-support tools that evaluate camera frames to propose path options to human rover drivers during tactical uplink planning cycles.

RoverMind bridges visual perception and deterministic algorithmic pathfinding by creating an integrated, auditable pipeline where every stage of processing—from tokenized model responses to heuristic graph expansions—can be inspected and verified.

---

## 3. Core Objectives

1. **End-to-End Pipeline**: Provide a complete, unbroken execution pipeline from an uploaded planetary image to an interactive route visualization.
2. **AI Visual Segmentation**: Integrate Meta SAM 3.1 via OpenAI-compatible APIs and the official `meta-sam-parser` utility to segment visual concepts (such as rocks, loose sand drifts, and obstacles).
3. **Spatial Grid Reconstruction**: Maintain coordinate integrity when mapping decoded binary rasters and bounding boxes to a downsampled mission grid.
4. **Normalized Terrain Classification**: Convert open-vocabulary visual concepts into standardized terrain classes (`clear`, `rocky`, `loose`, `obstacle`, `unknown`) through a deterministic contract.
5. **Configurable Traversal Costmaps**: Transform terrain labels into a numerical traversal cost grid where impassable terrain is strictly blocked.
6. **Custom A* Route Calculation**: Use an exact, authoritative backend A* planner supporting 4-way and 8-way diagonal movement with corner-cutting prevention and admissible heuristics.
7. **Interactive Mission-Control Interface**: Deliver a responsive React mission-control dashboard featuring real-time layer toggling, opacity adjustment, coordinate picking, and a spacecraft cursor follower.
8. **Scientific Honesty**: Ensure that all outputs are accurately described as computational decision-support and image-derived estimates rather than certified physical traversability or ground truth.

---

## 4. Complete Processing Workflow

```
[Mars Rover Camera Frame (JPEG/PNG)]
                 ↓
[Image Validation & Integrity Check (Pillow)]
                 ↓
[Meta SAM 3.1 Visual Segmentation (API or Offline Fixture)]
                 ↓
[Grammar Token Parsing & Binary Raster Decoding (meta-sam-parser)]
                 ↓
[Spatial Reconstruction & Bounding Box Alignment]
                 ↓
[Terrain Interpretation & Conflict Priority Arbitration]
                 ↓
[Normalized Segmentation Contract (SegmentationResult)]
                 ↓
[Terrain Traversal Costmap Compilation (build_cost_map)]
                 ↓
[Custom A* Path Planning (find_path)]
                 ↓
[Interactive Mission Control Visualizer & Telemetry HUD]
```

---

## 5. Technology Stack

### Backend
- **Python 3.12**: Core runtime environment.
- **FastAPI (0.100+)**: Asynchronous REST API framework providing OpenAPI documentation and high-performance routing.
- **Pydantic (v2)**: Strict type validation, serialization, and request/response schema enforcement.
- **Pillow (PIL)**: Binary image validation, format verification, and dimension extraction.
- **meta-sam-parser (0.1.0)**: Meta AI's official streaming grammar parser and raster mask decoder.
- **OpenAI Python SDK**: Client interface connecting to Meta's OpenAI-compatible model endpoints.
- **Pytest (8.x)**: Comprehensive automated unit and integration test suite.

### Frontend
- **React 18.3**: Declarative component-based UI framework.
- **TypeScript 5.6**: Static typing ensuring strict contract synchronization with backend schemas.
- **Vite 5.4**: Modern frontend build tooling and development server.
- **Lucide React**: Clean, accessible mission-control iconography.
- **CSS3 / Vanilla Styles**: Custom deep-space and Mars mission-control theme with hardware-accelerated animations.

---

## 6. Scientific & Engineering Limitations

A single 2D monocular image cannot establish physical terrain reality. RoverMind operates under explicit scientific limitations:

1. **No Ground Truth**: Image-derived terrain categories are visual estimations, not verified geological strata or geotechnical classifications.
2. **Absence of 3D Elevation & Slope**: A 2D RGB image does not provide stereo disparity, physical slope gradient, or digital elevation models (DEM).
3. **Subsurface Mechanics**: Visual appearance cannot determine soil sinkage risk, wheel slip ratios, compaction, or sub-surface boulder cavities.
4. **Computational Decision Support**: Computed routes represent mathematical lowest-cost paths under configured parameters, not certified safety clearances for flight rover hardware.
