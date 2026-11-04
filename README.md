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
- **Meta Reasoning Model & Structured Mission Intelligence**: Multi-model reasoning pipeline featuring primary `meta/muse-spark` with automatic graceful fallback to `meta/llama-3.3-70b-instruct`, and deterministic offline rule engine to synthesize 4-part operational briefings (Observation, Navigation Assessment, Risk & Uncertainty, Actionable Takeaways) with zero hallucinated geometry.
- **Contextual Mission Chatbot & Controlled Tool Interface**: Conversational assistant with access to 6 sandboxed simulation tools (`get_mission_summary`, `get_terrain_distribution`, `get_region_details`, `get_route_metrics`, `compare_routes`, `get_analysis_diagnostics`) bounded to 4 tool-calling iterations and 25-message session memory.
- **Mission-Control React Frontend**: Dark Mars-themed UI with layer toggling, opacity slider, cell inspection, interactive Start/Goal placement, live Mission Briefing HUD, and interactive Mission Chatbot drawer.
- **Graceful Offline Mode**: Automatically operates with labelled synthetic fixtures and deterministic rule engines when API keys are not configured or external access is disabled.
- **Comprehensive Test Suite**: 203 backend automated tests passing with 100% success rate under a hermetic test firewall, alongside strict frontend TypeScript compilation (`tsc`) and Vite production build.
- **Hardened Security & API Cost Governance**: Global API kill switch (`EXTERNAL_API_ENABLED=false`), dry-run validation mode, atomic operation budget limits (`RequestBudget`), concurrency semaphores, 25MP decompression bomb ceiling, dual-bounded in-memory session cache (25 frames and 100MB aggregate RAM ceiling), configurable production CORS origins, defensive HTTP security headers, and comprehensive regex error sanitization for credentials and tokens.

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
Meta Reasoning Model (Primary: muse-spark / Fallback: llama-3.3 / Deterministic Rule Engine)
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
git clone https://github.com/BharathBabu-code/RoverMind.git
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

The project ships with `.env.example` defining safe pre-live defaults:

```env
# Global Kill Switch & Pre-Live Safety Mode
EXTERNAL_API_ENABLED=false
EXTERNAL_API_DRY_RUN=true

# Meta SAM 3.1 Visual Segmentation
META_API_KEY=your_meta_sam_api_key_here

# Meta Reasoning Model (Primary: muse-spark, Fallback: llama-3.3)
META_REASONING_API_KEY=your_meta_reasoning_api_key_here
REASONING_PROVIDER=muse-spark
MUSE_SPARK_MODEL=muse-spark-1.3
LLAMA_MODEL=llama-3.3-70b-instruct
META_REASONING_BASE_URL=https://api.meta.ai/v1

# Security & Governance Limits
MAX_CONCURRENT_SAM_REQUESTS=2
MAX_CONCURRENT_REASONING_REQUESTS=2
MAX_REASONING_REQUESTS_PER_BRIEFING=2
MAX_REASONING_REQUESTS_PER_CHAT=5
MAX_TOOL_ITERATIONS_PER_CHAT=4
```

### Running Offline (Default — No Keys Required)
If you **do not create a `.env` file**, RoverMind runs in **100% deterministic offline mode**:
- Segmentation generates synthetic labelled terrain fixtures.
- Mission briefings and chatbot replies use the local deterministic rule engine.
- No billable external requests or network connections are ever made.

### Running Live (When Ready for Real API Inference)
When you are ready to make real external API calls:
1. Copy `.env.example` to create a `.env` file in the project root:
   ```powershell
   Copy-Item .env.example .env
   ```
2. Open `.env` and fill in your actual API keys:
   ```env
   META_API_KEY=your_actual_sam_api_key
   META_REASONING_API_KEY=your_actual_reasoning_api_key
   ```
3. Enable external API calls and disable dry-run mode:
   ```env
   EXTERNAL_API_ENABLED=true
   EXTERNAL_API_DRY_RUN=false
   ```

> **Security Note**: Never commit your `.env` file to Git. The `.gitignore` file is pre-configured to ignore `.env` so your secrets remain protected on your machine.

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
