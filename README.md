# RoverMind — AI-Assisted Planetary Exploration Platform

RoverMind is an AI-assisted planetary exploration decision-support and visualization system. It ingests monocular Mars rover camera imagery (Navcam/Hazcam), performs visual concept segmentation via Meta SAM 3.1, decodes and projects spatial masks onto a discrete coordinate grid, compiles terrain-risk costmaps, and computes deterministic lower-cost routes using a custom A* path-planning algorithm.

---

## Key Features

- **Monocular Image Ingestion & Validation**: Safe two-pass Pillow validation (PNG and JPEG) with dimension and payload integrity enforcement.
- **Meta SAM 3.1 Integration**: Uses the official `meta-sam-parser` to parse streaming token grammar and decode binary raster masks.
- **Spatial Alignment & Conflict Arbitration**: Projects box-local masks onto source-media coordinates, resolving overlapping concepts with safety priority hierarchies.
- **Normalized Terrain Contract**: Converts semantic visual concepts to canonical terrain classes (`clear`, `rocky`, `loose`, `obstacle`, `unknown`).
- **Configurable Traversal Costmaps**: Translates terrain classes into numeric impedance grids with impassable obstacles.
- **Authoritative Custom A* Pathfinding**: Supports 4-way cardinal and 8-way diagonal movement, Octile/Manhattan heuristics, and corner-cutting prevention.
- **Meta Reasoning Model & Structured Mission Intelligence**: Integrates `llama-3.3-70b-instruct` to synthesize 4-part operational briefings (Observation, Navigation Assessment, Risk & Uncertainty, Actionable Takeaways) with zero hallucinated geometry.
- **Contextual Mission Chatbot & Controlled Tool Interface**: Conversational assistant with access to 6 sandboxed simulation tools (`get_mission_summary`, `get_terrain_distribution`, `get_region_details`, `get_route_metrics`, `compare_routes`, `get_analysis_diagnostics`) bounded to 4 tool-calling iterations and 20-message session memory.
- **Mission-Control React Frontend**: Dark Mars-themed UI with layer toggling, opacity slider, cell inspection, interactive Start/Goal placement, live Mission Briefing HUD, and interactive Mission Chatbot drawer.
- **Graceful Offline Mode**: Automatically operates with labelled synthetic fixtures and deterministic rule engines when API keys are not configured.
- **Comprehensive Test Suite**: 124 backend automated tests passing with 100% success rate, alongside strict frontend TypeScript compilation (128 total checks).
- **Hardened Security Architecture**: 25MP decompression bomb ceiling, dual-bounded in-memory session cache (25 frames and 100MB aggregate RAM ceiling), configurable production CORS origins, defensive HTTP security headers, and sanitized error disclosures.

---

## Architecture at a Glance

```
Mars Rover Image (1648×1200 PNG)
           ↓
Image Validation (Pillow 25MP Ceiling)
           ↓
Visual Segmentation (Meta SAM 3.1 / Offline Fixture)
           ↓
Mask Parsing & Decoding (meta-sam-parser)
           ↓
Spatial Grid Reconstruction & Alignment
           ↓
Terrain Interpretation (Concept -> Class Mapping)
           ↓
Normalized Segmentation Contract (SegmentationResult)
           ↓
Terrain Traversal Costmap (build_cost_map)
           ↓
Custom A* Path Planning (find_path)
           ↓
Structured Mission Context (MissionContextDto, LRU Store)
           ↓
Meta Reasoning Model (llama-3.3-70b-instruct / Deterministic Rule Engine)
   ├── Observation Summarization (4-part structured briefing)
   ├── Terrain & Route Analysis Justification
   ├── Physical Risk & Sensor Uncertainty Interpretation
   └── Contextual Mission Chatbot (6 Sandboxed Tools)
           ↓
Interactive Mission Control UI (React + TypeScript HUD)
```

---

## Detailed Documentation Directory (`docs/`)

Comprehensive technical documentation is provided in the [`docs/`](./docs) directory:

1. [**Project Overview** (`docs/PROJECT_OVERVIEW.md`)](./docs/PROJECT_OVERVIEW.md) — Motivation, executive summary, objectives, and technology stack.
2. [**Architecture** (`docs/ARCHITECTURE.md`)](./docs/ARCHITECTURE.md) — Complete system architecture with detailed Mermaid diagrams across all stages.
3. [**File-by-File Guide** (`docs/FILE_BY_FILE_GUIDE.md`)](./docs/FILE_BY_FILE_GUIDE.md) — **Highest priority technical reference** detailing every source module, its functions, classes, data contracts, and edge cases.
4. [**Data Flow Trace** (`docs/DATA_FLOW.md`)](./docs/DATA_FLOW.md) — Step-by-step trace of a single image analysis with concrete request/response payloads through reasoning and chatbot stages.
5. [**Algorithmic Foundations** (`docs/ALGORITHMS.md`)](./docs/ALGORITHMS.md) — Detailed formulation of the custom A* engine, heuristic admissibility, corner-cutting prevention, and worked examples.
6. [**API Reference** (`docs/API_REFERENCE.md`)](./docs/API_REFERENCE.md) — Complete REST endpoint documentation with request/response schemas including mission and chatbot routes.
7. [**Reasoning Model Integration** (`docs/REASONING_MODEL_INTEGRATION.md`)](./docs/REASONING_MODEL_INTEGRATION.md) — Architecture, prompt engineering, structured briefing schemas, and offline fallback mechanics for Meta's reasoning layer.
8. [**Mission Chatbot & Tool Interface** (`docs/MISSION_CHATBOT.md`)](./docs/MISSION_CHATBOT.md) — Tool specifications, execution loops, conversational session bounds, and non-mutating route simulations.
9. [**Quality Assurance & Test Report** (`docs/TEST_REPORT.md`)](./docs/TEST_REPORT.md) — Execution report covering all 128 automated backend and frontend tests.
10. [**Security Audit Report** (`docs/SECURITY_AUDIT.md`)](./docs/SECURITY_AUDIT.md) — In-depth vulnerability audit covering CORS, memory DoS, decompression bombs, timeouts, and sanitized errors.
11. [**Complete Technical Guide & Engineering Blueprint** (`docs/ROVERMIND_COMPLETE_TECHNICAL_GUIDE.md`)](./docs/ROVERMIND_COMPLETE_TECHNICAL_GUIDE.md) — Exhaustive guide detailing what every visual element represents, offline vs live execution traces, and PowerShell instructions.
12. [**Live API Workflow & Verification Guide** (`docs/LIVE_API_WORKFLOW.md`)](./docs/LIVE_API_WORKFLOW.md) — End-to-end trace when `META_API_KEY` is configured, token grammar decoding, and PowerShell activation instructions.
13. [**Requirements Traceability Matrix** (`docs/REQUIREMENTS_TRACEABILITY.md`)](./docs/REQUIREMENTS_TRACEABILITY.md) — Verification status across all 16 platform capabilities.
14. [**Known Limitations** (`docs/KNOWN_LIMITATIONS.md`)](./docs/KNOWN_LIMITATIONS.md) — Scientific boundaries, physical sensor limits, and operational assumptions.

---

## Getting Started

### Prerequisites
- **Python**: 3.12+
- **Node.js**: 20+ (with npm)
- **Git**

---

### Installation

#### 1. Clone the Repository
```bash
git clone https://github.com/your-repo/RoverMind.git
cd RoverMind
```

#### 2. Backend Environment Setup (Windows PowerShell)
```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment
.\.venv\Scripts\Activate.ps1

# Install backend dependencies
pip install -r requirements.txt
```

*(Linux/macOS equivalent)*:
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

#### 3. Frontend Environment Setup
```powershell
Set-Location frontend
npm install
npm run build
Set-Location ..
```

*(Linux/macOS equivalent)*:
```bash
cd frontend
npm install
npm run build
cd ..
```

---

## Environment & API Key Safety

The root `.env.example` file contains:
```env
# Meta SAM 3.1 Visual Segmentation
META_API_KEY=

# Meta Reasoning Model (Llama 3.3 70B Instruct / Muse Spark candidate)
META_REASONING_API_KEY=
META_REASONING_MODEL=llama-3.3-70b-instruct
META_REASONING_BASE_URL=https://api.meta.ai/v1
```

To run with live Meta SAM 3.1 and Meta Reasoning models, copy `.env.example` to `.env` and set your API keys:
```powershell
Copy-Item .env.example .env
```

> **Security Note**: Never commit `.env` to version control. If `META_API_KEY` or `META_REASONING_API_KEY` are empty, RoverMind gracefully operates in **offline demonstration mode** using labelled synthetic fixtures and the deterministic reasoning engine.

---

## Running the Application

### Option A: Unified Full-Stack Server (Recommended)
FastAPI automatically serves the compiled React mission-control frontend directly on port 8000:

```powershell
# From project root with virtual environment activated:
.\.venv\Scripts\uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Open your browser to:
- **Mission Control UI**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger Docs**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc API Reference**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

### Option B: Independent Frontend Development Server
For active frontend development with hot-module replacement (Vite proxying to FastAPI):

```powershell
# Terminal 1 (Backend):
.\.venv\Scripts\uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload

# Terminal 2 (Frontend):
Set-Location frontend
npm run dev
```

Open your browser to: [http://localhost:5173](http://localhost:5173)

---

## Running Tests

### Run All Backend Automated Tests
```powershell
.\.venv\Scripts\python.exe -m pytest backend/tests -v
```

### Run Frontend Static Type Checking & Build
```powershell
Set-Location frontend
npm test        # executes tsc --noEmit
npm run build   # executes tsc && vite build
```

---

## Scientific Honesty & Decision Support Notice

A single 2D RGB or grayscale camera frame cannot establish physical terrain depth, slope stability, mechanical soil shear strength, or certified rover traversability. RoverMind is a **computational decision-support and visualization system**, not an autonomous flight navigation system. All outputs represent image-derived visual estimations and mathematical lowest-cost paths under configured parameters.
