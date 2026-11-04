# RoverMind: AI-Assisted Planetary Surface Perception & Autonomous Path Planning

RoverMind is an AI-assisted planetary exploration decision-support and tactical navigation platform. It ingests monocular Mars rover camera imagery (Navcam/Hazcam), performs zero-shot promptable visual concept segmentation via **Meta SAM 3.1**, projects spatial raster masks onto a discrete coordinate grid, compiles multi-hazard traversability costmaps, computes deterministic optimal trajectories using a custom **8-way Octile A\*** algorithm, and synthesizes structured operational telemetry briefings through **Meta LLaMA 3.3 / Muse Spark**.

- **Repository**: [https://github.com/BharathBabu-code/RoverMind.git](https://github.com/BharathBabu-code/RoverMind.git)
- **Evaluation Status**: Live Meta Model API Ready & Deterministic Fallback Verified

---

## Evaluation Notice for Hackathon Judges

> **Meta API Key Configuration for Evaluation**:  
> In compliance with competition guidelines, RoverMind evaluates live planetary imagery using your Meta Model API keys. Follow the sequential setup instructions below to configure your credentials:
> 1. Copy `.env.example` to create your local `.env` configuration.
> 2. Insert your Meta Model API keys (`META_API_KEY` for Meta SAM 3.1 and `META_REASONING_API_KEY` for Meta LLaMA 3.3 / Muse Spark).
> 3. Activate live inference by toggling `EXTERNAL_API_ENABLED=false` to `true` and `EXTERNAL_API_DRY_RUN=true` to `false`.
> 
> *(Note: The non-API offline mode is optionally supported as a fallback for local testing without network connectivity, automatically utilizing built-in deterministic adapters and our pre-downloaded Jezero/Gale gallery).*

---

## Pre-Existing Work vs. Original Work (Hackathon Disclosure)

### Required Opening Line for Submission Video
> *"In this video, we present RoverMind, an original planetary hazard perception and A\* path planning platform built on top of Meta's SAM 3.1 and LLaMA 3.3 models..."*

### Architectural Attribution Matrix

| Component | Status | Source / Attribution | Description & Role |
| :--- | :--- | :--- | :--- |
| **Meta SAM 3.1** | Pre-Existing Model | Meta AI | Foundation vision model for zero-shot promptable visual segmentation (`rock`, `sand`, `obstacle`, `bedrock`). |
| **Meta LLaMA 3.3 (70B Instruct)** | Pre-Existing Model | Meta AI | Foundation large language model used for operational briefing generation and operator dialogue. |
| **Meta Muse Spark (1.3)** | Pre-Existing Model | Meta AI | Specialized reasoning model evaluated for multi-step mission assessment. |
| **`meta-sam-parser`** | Pre-Existing Library | Meta AI (v0.1.0) | Open-source parser for decoding streaming token grammar from SAM 3.1. |
| **Mars Optical Imagery** | Pre-Existing Data | NASA / JPL-Caltech / MSSS | Public-domain Navcam/Hazcam frames from Mars 2020 (Perseverance) and MSL (Curiosity). |
| **Spatial Downsampling & Grid Mapping** | **Original Work** | RoverMind Authors | Custom algorithm converting high-resolution continuous monocular rasters into discrete 2D spatial coordinate grids. |
| **Hazard Conflict Arbitration Engine** | **Original Work** | RoverMind Authors | Multi-class priority hierarchy resolving overlapping segmentation boundaries into canonical terrain classes. |
| **Traversability Risk Costmap Compiler** | **Original Work** | RoverMind Authors | Physical terrain impedance modeling translating surface classifications into weighted movement penalties. |
| **8-Way Octile A\* Path Planning Engine** | **Original Work** | RoverMind Authors | Custom pathfinder with diagonal corner-cutting prevention, Octile distance heuristic, and mathematical step-cost explainability. |
| **Deterministic Rule & Fallback Engine** | **Original Work** | RoverMind Authors | Hermetic, zero-external-dependency reasoning pipeline ensuring 100% offline uptime and automated test repeatability. |
| **Mission Telemetry Chatbot & Tool Sandbox** | **Original Work** | RoverMind Authors | Sandboxed operator assistant exposing 6 simulation tools with hard iteration ceilings and strict security guardrails. |
| **Interactive Mission Cockpit UI** | **Original Work** | RoverMind Authors | React/TypeScript tactical interface with pan/zoom canvas, interactive waypoint dragging, live layer toggling, and Mars science facts HUD. |

---

## Meta Models Used & System Capabilities

### 1. Meta SAM 3.1 (Segment Anything Model 3.1)
- **Deployment Location**: Hosted Meta AI Inference Server (`https://api.meta.ai/v1`) or Local Deterministic Segmentation Adapter (Offline Fallback).
- **Function**: Receives downsampled optical frames and evaluates text prompts: `rock`, `loose sand drift`, `hazard obstacle`, and `firm bedrock`.
- **RoverMind Layer Built On Top**:
  - Streams and unpacks raw token grammar using `meta-sam-parser`.
  - Translates local bounding rasters into global media coordinate space.
  - Arbitrates overlapping masks using a safety-first priority ladder: `Obstacle (Impassable) > Sand Drift (High Slip) > Rocky Field (High Center) > Bedrock (Nominal) > Unclassified (Precautionary)`.

### 2. Meta LLaMA 3.3 (70B Instruct) & Muse Spark (1.3)
- **Deployment Location**: Hosted Meta AI OpenAI-Compatible API Endpoint or Local Deterministic Aerospace Reasoning Engine (Offline Fallback).
- **Function**: Ingests structured terrain distributions, obstacle density matrices, and computed A* traversal metrics to generate human-readable operational intelligence.
- **RoverMind Layer Built On Top**:
  - **4-Part Structured Telemetry Briefing**: Synthesizes structured mission assessments across *Visual Terrain Observation*, *Tactical Traversal Assessment*, *Sensor Uncertainty & Hazard Analysis*, and *Actionable Waypoint Recommendations*.
  - **Operator Chatbot with 6 Sandboxed Simulation Tools**:
    1. `get_mission_summary`: Aggregated terrain and traversal health metrics.
    2. `get_terrain_distribution`: Exact cell-level surface classification counts.
    3. `get_region_details`: Focused bounding-box hazard inspection.
    4. `get_route_metrics`: Turn-by-turn geometry, impedance sums, and step deviations.
    5. `compare_routes`: Non-mutating counterfactual trajectory evaluations.
    6. `get_analysis_diagnostics`: Compute budgets, latency logs, and model providences.
  - **Mission Security Guardrails**: Strict policy enforcement preventing prompt-injection attacks, refusing internal configuration or credential disclosure, and deflecting non-space/off-topic inquiries.

---

## Open-Source Assets & Data Rights

All assets and dependencies utilized in RoverMind comply with open-source and public-domain licensing:

1. **Planetary Imagery**: Public-domain imagery provided by NASA / JPL-Caltech / Malin Space Science Systems (MSSS) via the Mars 2020 and MSL mission archives. Under NASA's standard media guidelines, these images are in the public domain and authorized for educational, scientific, and software evaluation purposes.
2. **Backend Framework & Algorithms**:
   - `FastAPI` & `Uvicorn`
   - `Pydantic` — Data validation and schema enforcement
   - `Pillow` — Secure image decoding and dimensional bounds checking
   - `HTTPX` — Resilient asynchronous HTTP transport
   - `Pytest` — Hermetic automated test suite
3. **Frontend Application**:
   - `React 18` & `TypeScript`
   - `Vite` — Frontend tooling and asset compilation
   - `Tailwind CSS` — Mission control design system
   - `Lucide React` — Aerospace telemetry iconography

---

## System Architecture Pipeline

```
              NASA Rover Optical Frame (Navcam / Hazcam)
                                  │
                                  ▼
             Two-Pass Pillow Validation (25MP Decomp Ceiling)
                                  │
                                  ▼
       ┌──────────────────────────────────────────────────────┐
       │             Visual Concept Segmentation              │
       │    Meta SAM 3.1 API (Live) OR Deterministic Adapter   │
       └──────────────────────────┬───────────────────────────┘
                                  │ Token Grammar & Binary Masks
                                  ▼
       ┌──────────────────────────────────────────────────────┐
       │       Spatial Alignment & Conflict Arbitration       │
       │     (Obstacle > Loose Sand > Rocky > Bedrock)        │
       └──────────────────────────┬───────────────────────────┘
                                  │ Canonical Segmentation Grid
                                  ▼
       ┌──────────────────────────────────────────────────────┐
       │         Traversability Risk Costmap Compiler         │
       │   Bedrock: 1.0x | Rocky: 3.0x | Sand: 5.0x | Obstacle │
       └──────────────────────────┬───────────────────────────┘
                                  │ Weighted Impedance Matrix
                                  ▼
       ┌──────────────────────────────────────────────────────┐
       │          Custom 8-Way Octile A* Path Planner         │
       │    Diagonal Corner-Cutting Prevention & Octile h(n)  │
       └──────────────────────────┬───────────────────────────┘
                                  │ Waypoints, Cost Sum, Diagnostics
                                  ▼
       ┌──────────────────────────────────────────────────────┐
       │            Structured Mission Intelligence           │
       │ Meta LLaMA 3.3 / Muse Spark OR Deterministic Engine  │
       │  • 4-Part Telemetry Briefing (Zero-Hallucination)    │
       │  • Contextual Mission Chatbot (6 Sandboxed Tools)    │
       │  • Strict Security Guardrails (No Secret Leakage)    │
       └──────────────────────────┬───────────────────────────┘
                                  │
                                  ▼
       ┌──────────────────────────────────────────────────────┐
       │         Interactive Mission Cockpit Frontend         │
       │  • 2D Pan/Zoom Canvas with Dynamic Waypoint Dragging │
       │  • Real-Time Impedance & Step-Cost Explainability    │
       │  • Built-in Mars Rover Gallery (4 Jezero/Gale Frames)│
       │  • 10s Non-Blocking Mars Science Facts HUD Ticker    │
       └──────────────────────────────────────────────────────┘
```

---

## Sequential Setup & Execution Guide

Follow this sequence to clone, configure API keys, install dependencies, and run the platform on your system.

### System Prerequisites
- **Python**: Version `3.10`, `3.11`, or `3.12`
- **Node.js**: Version `18.x`, `20.x`, or higher (includes `npm`)
- **Git**

---

### Step 1: Clone the Repository
Open your terminal and clone the repository:
```bash
git clone https://github.com/BharathBabu-code/RoverMind.git
cd RoverMind
```

---

### Step 2: Configure Environment & Meta Model API Keys

RoverMind includes a template file `.env.example`. Create your active `.env` file from this template:

**On Windows (PowerShell):**
```powershell
Copy-Item .env.example .env
```

**On macOS / Linux:**
```bash
cp .env.example .env
```

Open `.env` in any text editor and complete the two required configuration steps:

#### 1. Enable Live External API Calls (Change False to True)
Locate the safety kill switches at the top of `.env` and change them as follows:
```env
# Switch from 'false' to 'true' to enable live network inference
EXTERNAL_API_ENABLED=true

# Switch from 'true' to 'false' to disable dry-run mock mode
EXTERNAL_API_DRY_RUN=false
```

#### 2. Insert Your Meta Model Credentials
Enter your Meta API keys and desired model identifiers:
```env
# Meta SAM 3.1 visual segmentation API key
META_API_KEY=your_actual_meta_sam_api_key_here

# Meta Reasoning API key (defaults to META_API_KEY if using unified key)
META_REASONING_API_KEY=your_actual_meta_reasoning_api_key_here

# Reasoning Model Routing
REASONING_PROVIDER=llama-3.3
LLAMA_MODEL=llama-3.3-70b-instruct
META_REASONING_BASE_URL=https://api.meta.ai/v1
```

> **Optional Non-API Offline Fallback**: If you ever need to test locally without internet access or without consuming API quota, you can optionally set `EXTERNAL_API_ENABLED=false`. In this mode, RoverMind runs its built-in deterministic segmentation adapter and aerospace rule engine with zero external network calls.

---

### Step 3: Configure Backend Virtual Environment

#### On Windows (PowerShell / Command Prompt):
```powershell
# Create virtual environment
python -m venv .venv

# Activate virtual environment in PowerShell:
.\.venv\Scripts\Activate.ps1
# (Or in Command Prompt: .\.venv\Scripts\activate.bat)

# Upgrade pip and install backend dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

#### On macOS (Terminal / zsh):
```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

#### On Linux (Ubuntu / Debian / bash):
```bash
# Install system packages if needed
sudo apt update && sudo apt install -y python3-venv python3-pip

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Upgrade pip and install dependencies
pip install --upgrade pip
pip install -r requirements.txt
```

---

### Step 4: Install Frontend Dependencies & Build

In the same repository, compile the React mission control interface:

**On Windows (PowerShell / Command Prompt):**
```powershell
cd frontend
npm install
npm run build
cd ..
```

**On macOS / Linux:**
```bash
cd frontend
npm install
npm run build
cd ..
```

---

### Step 5: Launch the Application

With the backend virtual environment active (`.venv`), start the unified FastAPI server:

```bash
uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

### Step 6: Access the Mission Cockpit

Open your web browser and navigate to:

- **Mission Cockpit UI**: [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive OpenAPI Documentation**: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)
- **ReDoc Technical Specification**: [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc)

When connected with live API keys, the top status bar in the Mission Cockpit displays:
- `SERVER: LOCAL OK`
- `SAM: LIVE`
- `AI: LLAMA 3.3` (or `AI: MUSE SPARK`)

---

### Dual Development Server Mode (Optional for Active Frontend Editing)
If you wish to make live modifications to frontend components with hot-module replacement (Vite proxying to FastAPI):
- **Terminal 1 (Backend)**: `uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload`
- **Terminal 2 (Frontend)**: `cd frontend && npm run dev`
- **Development UI**: [http://localhost:5173](http://localhost:5173)

---

## Automated Test Suite & Verification

RoverMind includes 207 automated tests covering image ingestion, coordinate downsampling, SAM token parsing, 8-way octile A* pathfinding, budget enforcement, and chatbot guardrails.

### Run Backend Test Suite
```bash
# Ensure virtual environment is activated
pytest backend/tests -v
```

### Run Frontend Static Verification & Build
```bash
cd frontend
npm run build
cd ..
```

---

## Key Mission Capabilities & UI Controls

- **Curated Mars Rover Gallery**: Click **Sample Frame** to instantly select between 4 authentic Mars rover exploration terrains:
  1. *Jezero Crater Vista* (Perseverance Sol 180) — Broad bedrock corridor with scattered gravel.
  2. *Boulder Field Hazard* (Perseverance Western Scarp) — High-density obstacle field testing obstruction clearance.
  3. *Loose Sand Drift* (Curiosity Gale Dunes) — High-impedance ripple field testing wheel-slip avoidance.
  4. *Bedrock Corridor* (Kodiak Mesa Approach) — Favorable low-impedance traversal pathway.
- **Local Device Ingestion**: Click **Upload Image** to process any external monocular JPEG or PNG rover image (validated with two-pass Pillow safety checks).
- **Interactive Waypoint Manipulation**: Click and drag the cyan **Start (Alpha)** and orange **Goal (Bravo)** flags across the grid canvas. The A* algorithm recalculates the optimal path in real time (< 15 ms).
- **Explainability Dashboard**: Switch tabs in the intelligence panel to inspect exact step-cost reconciliation, cardinal vs. diagonal step distribution, and mathematical Octile heuristic proofs.
- **Mars Science Facts HUD**: A 10-second non-blocking informational ticker displays verified planetary science facts during analysis operations, equipped with user dismissal controls.
- **Mission Operator Chatbot**: Open the right drawer to query mission telemetry, ask space exploration science questions, or request hypothetical counterfactual route simulations with built-in aerospace security guardrails.

---

## Scientific Honesty & Operational Boundaries

A single 2D RGB monocular camera frame cannot determine physical 3D elevation profiles, soil shear mechanics, sub-surface voids, or certified rover steering dynamics. RoverMind is designed as an **operator decision-support and tactical planning visualization platform**, not an autonomous spacecraft flight controller. All generated costmaps, impedance values, and trajectories represent mathematical optimizations over image-derived visual hazard classifications.
