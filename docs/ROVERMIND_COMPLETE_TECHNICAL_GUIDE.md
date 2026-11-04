# RoverMind — Complete Technical Guide & Engineering Blueprint

This document is the authoritative technical reference for RoverMind. It explains exactly what the application displays, where every value comes from, how data flows through the backend and frontend, and precisely what occurs in both offline (synthetic) and live (Meta SAM 3.1) modes.

---

# TABLE OF CONTENTS
1. [System Overview & Architecture](#1-system-overview--architecture)
2. [What the User Sees: Screen-by-Screen & Component Breakdown](#2-what-the-user-sees-screen-by-screen--component-breakdown)
3. [Deep Dives into Visualizations & Metrics](#3-deep-dives-into-visualizations--metrics)
4. [Application Workflow Without META_API_KEY (Offline Mode)](#4-application-workflow-without-meta_api_key-offline-mode)
5. [Application Workflow With META_API_KEY (Live Mode)](#5-application-workflow-with-meta_api_key-live-mode)
6. [Live vs. Offline Comparison Matrix](#6-live-vs-offline-comparison-matrix)
7. [API Key Configuration & Activation Guide (Windows PowerShell)](#7-api-key-configuration--activation-guide-windows-powershell)
8. [Scientific Honesty & Decision Support Boundaries](#8-scientific-honesty--decision-support-boundaries)

---

# 1. System Overview & Architecture

RoverMind is a computational decision-support system designed to assist planetary scientists and rover operators in evaluating terrain hazards from monocular surface imagery.

The core data processing pipeline consists of 9 discrete stages:
```
1. Image Ingestion (Pillow validation, 25MP decompression ceiling, thread-safe LRU store)
       ↓
2. Visual Segmentation (Meta SAM 3.1 streaming token inference OR offline synthetic fixtures)
       ↓
3. Mask Parsing (meta-sam-parser grammar unrolling into SegmentationMaskRecord objects)
       ↓
4. Raster Decoding & Coordinate Alignment (RLE to binary raster, spatial downsampling)
       ↓
5. Normalized Terrain Interpretation (concept mapping to canonical classes: clear, sand, rock, obstacle)
       ↓
6. Discrete Costmap Compilation (numeric traversability impedance grid)
       ↓
7. Custom A* Path Planning (8-way octile search with diagonal corner-cutting prevention)
       ↓
8. Mission Intelligence Layer (Meta Llama 3.3 Reasoning Model OR deterministic rule engine)
       ↓
9. Contextual Mission Assistant (Controlled tool-based Q&A and non-destructive route simulation)
```

---

# 2. What the User Sees: Screen-by-Screen & Component Breakdown

### 2.1 Navigation Bar (`frontend/src/components/Navbar.tsx`)
- **What is displayed**:
  - Application brand mark and logo (`ROVERMIND`).
  - System status pill: Green `● ONLINE` when the backend is responsive; Red `● OFFLINE` if the backend cannot be reached.
  - Model status badge: Green `● LIVE SAM 3.1 ACTIVE` when `META_API_KEY` is present; Amber `⚡ OFFLINE SYNTHETIC DEMO` when `META_API_KEY` is empty.
  - Action buttons: "Methodology" modal button, "Load Sample Frame" quick button, and "Upload Image" button.
- **Where values come from**:
  - Polled every 15 seconds from `GET /api/health` and `GET /api/config`.
  - Supplied by `backend/app/api/routes/health.py`.
- **Live vs. Synthetic vs. Static**:
  - Status indicators are **live** backend telemetry.
  - Branding and methodology content are **static**.

### 2.2 Tactical Pipeline Status Bar (`frontend/src/components/MissionStatusBar.tsx`)
- **What is displayed**:
  - Active optical frame filename (e.g. `rover_image.png`).
  - Monocular frame resolution (e.g. `1648 × 1200 px`).
  - Ingestion file size (e.g. `2.4 MB`).
  - Discrete grid matrix dimensions (e.g. `103 × 75 cells`).
  - Active detection concepts (e.g. `["rock", "sand", "obstacle"]`).
  - Model provenance attribution tag (e.g. `sam-3.1` or `sam-3.1-offline-synthetic`).
- **Where values come from**:
  - Extracted from `FullAnalysisResponse.metadata` and `FullAnalysisResponse.segmentation`.
  - Supplied by `POST /api/analysis/run` or `POST /api/images/load-sample`.
- **Live vs. Synthetic vs. Static**:
  - Image properties and grid dimensions are **calculated** from uploaded bytes.
  - Provenance tag is **live** telemetry reflecting actual model execution mode.

### 2.3 Interactive Exploration Viewport (`frontend/src/components/InteractiveMapViewer.tsx`)
- **What is displayed**:
  - Centerpiece multi-layer canvas rendering the rover surface scene.
  - Layer visibility switches:
    1. *Raw Optical Frame*: Original RGB Martian surface image.
    2. *SAM Concept Segmentation*: Color-coded segmentation masks.
    3. *Terrain Risk Costmap*: Heatmap indicating traversal impedance (green to dark red).
    4. *Custom A\* Trajectory*: Cyan route line connecting Start (A) to Goal (B).
    5. *Tactical Grid Lines*: Subtle grid dividing image space into cells.
  - Opacity Slider: Adjusts overlay transparency from 0.0 to 1.0.
  - Zoom & Pan Toolbar: Zoom in (+), Zoom out (-), Reset view (center).
  - Waypoint Selection Mode: Toggles Start (Pin A, green) and Goal (Pin B, red) placement modes.
  - Real-Time Hover HUD: Floating card showing cell coordinate `(row, col)`, terrain class, traversal cost, and obstacle blockage status.
- **Where values come from**:
  - Raw image: Streamed from `GET /api/images/{image_id}/raw`.
  - Grid & masks: From `FullAnalysisResponse.segmentation`.
  - Cost grid: From `FullAnalysisResponse.costmap.cost_grid`.
  - Path line: From `FullAnalysisResponse.path_result.path`.
- **Live vs. Synthetic vs. Calculated**:
  - Image is **live binary data**.
  - Path and hover costs are **calculated** from the costmap matrix.

### 2.4 Tactical Analysis & Planning Panel (`frontend/src/components/AnalysisPanel.tsx`)
- **What is displayed**:
  - *Path Metrics*:
    - Waypoints count (e.g. `75 waypoints`).
    - Total weighted traversal cost (e.g. `74.00`).
    - Geometric distance (e.g. `74.00 units`).
    - Expanded search nodes (e.g. `74 nodes`).
  - *A\* Navigation Controls*:
    - Diagonal Movement toggle (enables 8-way octile search vs 4-way cardinal search).
    - Recalculate Path button (triggers `POST /api/planning/find-path`).
    - Reset Endpoints button (restores default start and goal).
  - *Terrain Classification Distribution*:
    - Horizontal breakdown bars for Clear Bedrock, Loose Sand, Rocky Field, and Blocked Obstacles with exact cell counts and percentages.
- **Where values come from**:
  - Supplied by `FullAnalysisResponse.path_result` and `FullAnalysisResponse.segmentation.terrain_grid`.
- **Live vs. Synthetic vs. Calculated**:
  - Traversal metrics and terrain percentages are **calculated** deterministically by the backend.

### 2.5 Technical Diagnostics Drawer (`frontend/src/components/DiagnosticsDrawer.tsx`)
- **What is displayed**:
  - Table of all decoded mask objects extracted by `meta-sam-parser`: Object ID, Prompt Concept, Bounding Box coordinates `(left, top, right, bottom)`, and Pixel Area.
  - Diagnostic execution trace logs: API round-trip status, fallback notices, downsampling timings.
  - Raw JSON viewer for engineers.
- **Where values come from**:
  - Supplied by `FullAnalysisResponse.segmentation.masks` and `FullAnalysisResponse.diagnostics`.

---

# 3. Deep Dives into Visualizations & Metrics

### 3.1 What Does the Original Rover Image Represent?
The original image is a monocular 2D photographic frame captured by a rover surface navigation camera (Navcam) or hazard avoidance camera (Hazcam). It is rendered in sRGB color space. It contains perspective distortion and scale ambiguity (distant hills appear small; nearby pebbles appear large).

### 3.2 What is a Segmentation Overlay?
A segmentation overlay is a composite raster highlighting regions identified as matching semantic prompts (such as `rock`, `loose sand`, `obstacle`). When SAM 3.1 processes an image, it outputs binary run-length masks corresponding to bounding boxes. These masks are rendered with semi-transparent tinted overlays (e.g., amber for sand, copper for rock, red for obstacles).

### 3.3 What is a Normalized Terrain Category?
Natural language prompts are varied (e.g. "boulder", "rock", "stone", "gravel"). RoverMind normalizes all visual prompts into four canonical categories:
- `clear`: Firm, traversable bedrock or compacted soil.
- `sand`: Loose granular regolith presenting moderate wheel sinkage / slippage risk.
- `rock`: Uneven rocky terrain presenting mechanical shock and suspension wear risk.
- `obstacle`: Severe hazard (large boulder, steep crater rim, non-traversable drop).

### 3.4 What Does a Costmap Cell Represent?
A costmap cell represents an aggregated spatial patch of terrain. Its value is a floating-point numeric traversal impedance weight:
- `1.0`: Nominal traversability (clear bedrock).
- `3.5`: Elevated traversal cost (loose sand; rover consumes more energy, risks wheel slip).
- `6.0`: High traversal cost (rocky field; rover must navigate slowly).
- `null`: Impassable / blocked cell (obstacle; cannot be entered by pathfinding).

### 3.5 What Does the Route Line Represent?
The cyan polyline represents the path of least cumulative traversal impedance calculated by RoverMind's custom A* algorithm. It is a discrete sequence of grid coordinates $(r_0, c_0) \to (r_1, c_1) \to \dots \to (r_k, c_k)$ minimizing the objective function:
$$f(n) = g(n) + h(n)$$
Where $g(n)$ is the exact accumulated path impedance and $h(n)$ is the admissible octile heuristic distance to the goal.

### 3.6 What do "Weighted Traversal Cost", "Geometric Distance", and "Expanded Nodes" Mean?
- **Weighted Traversal Cost**: The sum of cell-to-cell traversal costs along the trajectory. Diagonal steps across cells with costs $c_1, c_2$ cost $\sqrt{2} \times \frac{c_1 + c_2}{2}$.
- **Geometric Distance**: The physical Euclidean or octile length of the route, assuming unit cell spacing, independent of terrain penalties.
- **Expanded Nodes**: The number of cells the A* search explored from the priority queue before reaching the goal. This indicates search efficiency: an unobstructed direct path expands only $N$ nodes (where $N$ is path length), while complex obstacle fields require expanding more nodes.

### 3.7 What is an "Unknown Cell" and a "Blocked Cell"?
- **Unknown Cell**: A grid patch where no visual mask was segmented or confidence was indeterminate. RoverMind conservatively assigns unknown cells a default traversal cost of `2.0`.
- **Blocked Cell**: A cell classified as an obstacle (`cost = null`). The A* algorithm treats blocked cells as infinite-cost barriers and will never route through them.

---

# 4. Application Workflow Without META_API_KEY (Offline Mode)

When RoverMind is launched in an environment where `META_API_KEY` is empty, it operates in **deterministic offline demonstration mode**.

### Execution Sequence:
1. **Application Startup**:
   - `backend/app/core/config.py` loads `.env`.
   - `settings.meta_api_key` is `None` or empty.
   - `settings.is_meta_api_configured` evaluates to `False`.
2. **Frontend Discovery**:
   - The browser queries `GET /api/config`.
   - The response returns: `{"is_meta_api_configured": false, "offline_mode": true}`.
   - The UI status badge renders: `⚡ OFFLINE SYNTHETIC DEMO`.
3. **Sample Image Ingestion**:
   - The user clicks "Load Authentic Rover Frame".
   - `POST /api/images/load-sample` reads `rover_image.png` (1648×1200 px) from disk.
   - `validate_and_store_image()` validates the image structure with Pillow, checks dimensions, enforces the 25MP decompression ceiling, and registers it in `_IMAGE_STORE`.
4. **Synthetic Fixture Generation**:
   - `run_full_analysis()` detects `settings.is_meta_api_configured == False`.
   - Instead of calling Meta's cloud API, it invokes `generate_synthetic_offline_segmentation()`.
   - This produces a deterministic synthetic terrain pattern:
     - Foreground: Clear traversable soil.
     - Middle-left: Loose sand drift.
     - Middle-right: Rocky cluster.
     - Center: Discrete obstacle barrier (crater rim / large boulder).
   - The response metadata is explicitly marked:
     - `source_model = "sam-3.1-offline-synthetic"`
     - `is_synthetic = True`
     - Diagnostic note: `"SYNTHETIC DEMO DATA: META_API_KEY is not configured... does not reflect actual live SAM inference."`
5. **Real Downstream Computation**:
   - Crucially, **all downstream pipeline stages are 100% genuine computations**:
     - `build_cost_map()` compiles the numeric cost grid from the synthetic categories.
     - `find_path()` runs the actual custom 8-directional A* algorithm on the resulting grid.
6. **Frontend Rendering**:
   - The browser displays the real rover image overlaid with the synthetic terrain zones and the computed A* trajectory.

---

# 5. Application Workflow With META_API_KEY (Live Mode)

When `META_API_KEY` is provided in `.env`, RoverMind performs live visual segmentation against Meta's cloud infrastructure.

### End-to-End Sequence Diagram:
```mermaid
sequenceDiagram
    autonumber
    actor User as Rover Operator / Browser
    participant API as FastAPI Backend (/api)
    participant Config as Settings (.env)
    participant Store as Image Store (Pillow)
    participant SAM as SAM Service (sam_service.py)
    participant Meta as Meta AI API (api.meta.ai/v1)
    participant Parser as meta-sam-parser
    participant Interp as Terrain Interpreter
    participant Cost as Costmap Engine
    participant Path as Custom A* Engine

    User->>API: POST /api/analysis/run {image_id, concepts}
    API->>Config: settings.is_meta_api_configured
    Config-->>API: True
    API->>Store: get_image_data_url(image_id)
    Store-->>API: data:image/png;base64,iVBORw...
    API->>SAM: run_live_sam_segmentation(...)

    loop For each concept in ["rock", "sand", "obstacle"]
        SAM->>Meta: POST /v1/responses (model="sam-3.1", input=[text, image_url])
        Meta-->>SAM: Streaming grammar tokens
        SAM->>Parser: push(token_stream) + finish(CompletedOutcome)
        Parser-->>SAM: List[SegmentationMaskRecord]
        SAM->>SAM: decode_mask_to_raster(record.mask)
        SAM->>SAM: Spatial coordinate alignment & downsampling
    end

    SAM->>Interp: Raw discrete concept grid
    Interp-->>SAM: Normalized SegmentationResult
    SAM-->>API: SegmentationResponse + MaskRecordDtos
    API->>Cost: build_cost_map(terrain_grid, costs)
    Cost-->>API: 2D numeric Cost Grid
    API->>Path: find_path(cost_grid, start, goal, allow_diagonal)
    Path-->>API: PathResult (waypoints, cost, length, nodes)
    API-->>User: FullAnalysisResponse (JSON)
```

### Detailed Technical Trace:
1. **Secret Loading**: `backend/app/core/config.py` loads `META_API_KEY` via `python-dotenv`.
2. **OpenAI SDK Client Initialization**:
   ```python
   client = openai.OpenAI(
       base_url="https://api.meta.ai/v1",
       api_key=settings.meta_api_key,
       timeout=httpx.Timeout(30.0, connect=10.0)
   )
   ```
3. **Payload Construction**:
   The stored image is formatted as a Base64 data URL. For each query concept:
   ```python
   response = client.responses.create(
       model="sam-3.1",
       input=[
           {
               "type": "message",
               "role": "user",
               "content": [
                   {"type": "input_text", "text": prompt},
                   {"type": "input_image", "image_url": image_data_url},
               ],
           },
       ],
   )
   ```
4. **Token Stream Extraction & Parser Push**:
   The response text containing Meta's image segmentation grammar tokens is parsed:
   ```python
   import meta_sam_parser as sam
   response_format = sam.image_segmentation_format()
   parser = response_format.create_parser()
   parser.push(response_text)
   finished = parser.finish(sam.CompletedOutcome())
   result = finished.result
   ```
5. **Raster Decoding & Spatial Projection**:
   For each `sam.SegmentationMaskRecord`:
   - `sam.decode_mask_to_raster(record.mask)` decodes the binary byte raster.
   - Bounding coordinates (`record.bounds.left, top, right, bottom`) are clamped to the image frame ($W \times H$).
   - The raster is downsampled onto the discrete matrix ($R \times C$).
   - Priority resolution hierarchy assigns cell labels (`obstacle` overrides `rock`, which overrides `sand`).
6. **Provenance Attribution**:
   - `source_model = "sam-3.1"`
   - `is_synthetic = False`
   - Diagnostics contain live API round-trip execution records.

---

# 6. Live vs. Offline Comparison Matrix

| Pipeline Dimension | Offline Demo Mode (`META_API_KEY` empty) | Live API Mode (`META_API_KEY` active) |
|---|---|---|
| **API Key Requirement** | None (empty string or absent) | Valid Meta API Key in `.env` |
| **Network Access** | 100% local, zero external network calls | Outbound HTTPS to `https://api.meta.ai/v1` |
| **Image Validation** | Full Pillow validation, 25MP ceiling | Full Pillow validation, 25MP ceiling |
| **Segmentation Engine** | Deterministic synthetic geometric pattern | Meta SAM 3.1 cloud model inference |
| **Token Parsing** | Bypassed (synthetic records constructed directly) | Active `meta-sam-parser` stream decoding |
| **Raster Decoding** | Synthetic raster bounds | `sam.decode_mask_to_raster()` |
| **Model Provenance Tag** | `"sam-3.1-offline-synthetic"` | `"sam-3.1"` |
| **Synthetic Flag** | `is_synthetic: true` | `is_synthetic: false` |
| **Costmap Compilation** | Real `build_cost_map()` calculation | Real `build_cost_map()` calculation |
| **A\* Path Planning** | Real custom `find_path()` search | Real custom `find_path()` search |
| **UI Telemetry Badge** | Amber: `⚡ OFFLINE SYNTHETIC DEMO` | Green: `● LIVE SAM 3.1 ACTIVE` |

---

# 7. API Key Configuration & Activation Guide (Windows PowerShell)

Follow these exact steps to enable live Meta SAM 3.1 inference on Windows PowerShell:

### Step 1: Open or Create `.env`
In the `RoverMind` repository root, write your key to `.env`:
```powershell
# In RoverMind root directory:
Set-Content -Path .\.env -Value "META_API_KEY=your_actual_meta_api_key_here"
```
*(Note: Do not wrap the key in quotes unless it contains special shell characters; standard alphanumeric keys require no quotes).*

### Step 2: Restart the Backend Server
The backend loads environment variables on initialization. Restart Uvicorn:
```powershell
.\.venv\Scripts\uvicorn.exe backend.app.main:app --host 127.0.0.1 --port 8000
```

### Step 3: Verify Key Discovery
Query the configuration endpoint:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/config" | ConvertTo-Json
```
**Expected Response:**
```json
{
  "is_meta_api_configured": true,
  "meta_model": "sam-3.1",
  "offline_mode": false,
  "message": "Meta SAM 3.1 API is configured with valid credentials."
}
```

### Step 4: Run Live Analysis
```powershell
# 1. Ingest sample image
$upload = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/images/load-sample" -Method Post
$imageId = $upload.metadata.image_id

# 2. Trigger analysis
$body = @{
    image_id = $imageId
    concepts = @("rock", "sand", "obstacle")
    start = @(74, 51)
    goal = @(0, 51)
    allow_diagonal = $true
} | ConvertTo-Json

$analysis = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/analysis/run" -Method Post -Body $body -ContentType "application/json"

# 3. Check live attribution
Write-Host "Model Source: $($analysis.segmentation.source_model)"
Write-Host "Is Synthetic: $($analysis.segmentation.is_synthetic)"
Write-Host "Path Found:   $($analysis.path_result.is_success)"
```

### Step 5: Troubleshooting Failures
- **Authentication Failure (401 / 403)**:
  - If the key is invalid or revoked, the backend catches the OpenAI API error and logs: `"API request failed for concept '...': [REDACTED_API_KEY] Unauthorized"`.
  - The pipeline automatically falls back to labelled synthetic data with an explanatory diagnostic message so the user experience does not crash.
- **Quota Exceeded (429)**:
  - Caught gracefully with fallback to synthetic data and notice in `diagnostics`.
- **Parser Failure**:
  - If Meta's response does not match SAM grammar, `meta-sam-parser` raises an exception; RoverMind logs the parser diagnostic and continues.

---

# 8. Scientific Honesty & Decision Support Boundaries

RoverMind adheres strictly to the principles of scientific honesty in aerospace computing:

1. **No Ground Truth Claims**: A single 2D camera image cannot establish true physical elevation, slope angle, soil cohesion, or subsurface cavities.
2. **Computational Decision Support**: Trajectories computed by RoverMind represent estimated lowest-cost routes on image-derived impedance models. They must **never** be interpreted as certified autonomous drive commands or physically guaranteed safe paths.
3. **No Fabricated Confidence**: Confidence metrics are only displayed if provided by the model. When uncalibrated, confidence is explicitly designated as `null`.
4. **Deterministic Separation**: Offline demonstration data is always prominently labelled with `"sam-3.1-offline-synthetic"` and `is_synthetic: true`.

---

# 9. Comprehensive Algorithmic, Interaction & Transparency Reference

### 9.1 Who Decides the Route in Offline vs. Live Mode?
- **In Offline Mode**: The route is decided **100% deterministically by RoverMind's custom A\* pathfinding algorithm** running on a discrete cost grid. However, the cost grid itself is populated from a **predefined synthetic geometric benchmark pattern** (`sam-3.1-offline-synthetic`), **NOT** by an AI model visually analyzing the uploaded image pixels. The uploaded image is real, the costmap calculation is real, and the A\* path is mathematically optimal on that grid, but the segmentation is synthetic.
- **In Live Mode (with `META_API_KEY`)**: Meta SAM 3.1 analyzes the raw pixel stream and returns concept bounding boxes and masks. RoverMind normalizes these masks into canonical terrain classes, builds the numerical costmap, and the **custom A\* algorithm** calculates the route. The AI model **never decides the route**; it only segments the visual pixels. The route is always chosen by the mathematical pathfinding engine.

### 9.2 How Offline Synthetic Segmentation Works
When `META_API_KEY` is not provisioned:
1. `generate_synthetic_offline_segmentation()` creates a discrete 2D matrix matching the requested grid resolution (e.g. $103 \times 75$ cells).
2. It mathematically partitions the grid into benchmark zones using relative fractional coordinates:
   - Middle-left ($r \in [0.35 H, 0.65 H], c \in [0.1 W, 0.45 W]$): assigned as `"loose sand"` where $(r+c) \pmod 3 \neq 0$.
   - Middle-right ($r \in [0.25 H, 0.60 H], c \in [0.55 W, 0.85 W]$): assigned as `"rock"` where $(r \cdot c) \pmod 4 \neq 0$.
   - Central obstacle ($r \in [0.45 H, 0.55 H], c \in [0.40 W, 0.50 W]$): assigned as `"obstacle"`.
   - Remaining cells: assigned as `"clear"`.
3. It creates synthetic bounding box records with `confidence: None`.
4. The output is tagged with `source_model: "sam-3.1-offline-synthetic"` and `is_synthetic: True`.
5. **No computer vision, neural network, or pixel analysis occurs on the uploaded image in offline mode.**

### 9.3 How Live SAM Segmentation Works
When `META_API_KEY` is provisioned:
1. The image is encoded as a Base64 Data URL (`data:image/png;base64,...`).
2. An OpenAI SDK client configured with base URL `https://api.meta.ai/v1` submits multimodal requests for concepts `["rock", "sand", "obstacle"]`.
3. Meta SAM 3.1 streams token grammar containing spatial bounding boxes and compressed binary mask tokens.
4. `meta-sam-parser` parses tokens into `SegmentationMaskRecord` objects.
5. `sam.decode_mask_to_raster()` decodes 1-byte-per-pixel rasters and maps box-local coordinates into global image coordinates.

### 9.4 How Terrain Classes Are Assigned & Overlaps Arbitrated
RoverMind maps open-domain concepts into 5 canonical normalized terrain labels:
- `"clear"`: firm bedrock, soil, flat ground, smooth terrain.
- `"rocky"`: rock, boulder, stone, bedrock outcrop.
- `"loose"`: loose sand, dune, ripple, sand drift.
- `"obstacle"`: crater rim, cliff, dropoff, rover chassis, wheel, solar panel.
- `"unknown"`: shadow, unmapped concept, unclassified regions.

When multiple masks cover the same cell, deterministic safety priority arbitrates:
$$\text{obstacle } (100) > \text{rocky } (70) > \text{loose } (50) > \text{unknown } (30) > \text{clear } (10)$$
Cells with no detected masks default to `"clear"` (or `"unknown"` if in shadow).

### 9.5 How Traversal Costs Are Assigned
Numerical impedance weights represent traversal difficulty:
- `"clear"`: $1.0\times$ (nominal baseline impedance).
- `"rocky"`: $3.0\times$ (wheel wear and vibration penalty).
- `"loose"`: $5.0\times$ (wheel sinkage and motor stall hazard).
- `"unknown"`: $2.0\times$ (precautionary penalty for unclassified regions).
- `"obstacle"`: `None` (strictly impassable; $\infty$ impedance).

### 9.6 Unknown Terrain Handling & Why 2.0x Was Chosen
- **Distinguishability**: A cost of 2.0x places unknown terrain strictly between clear bedrock (1.0x) and rocky terrain (3.0x). It ensures A\* prefers verified clear bedrock over unknown terrain whenever an equivalent clear corridor exists, but will traverse unknown terrain rather than crossing severe rocky fields (3.0x) or loose dunes (5.0x).
- **Configurability**: In the **Terrain Cost Configuration** panel, operators can increase the unknown penalty up to 15.0x to enforce strict avoidance of shadow regions.
- **Exposure Warnings**: If any computed path traverses unknown cells, the UI immediately surfaces an **Unknown Terrain Exposure Warning** showing the exact cell count and percentage.

### 9.7 Exact A* Mathematics & Worked Example
#### Objective Function:
$$f(n) = g(n) + h(n)$$
- $g(n)$: exact accumulated weighted path cost from start to node $n$.
- $h(n)$: admissible heuristic estimating remaining cost to goal.

#### Step Cost Formulation:
Transition from node $u = (r_u, c_u)$ to neighbor $v = (r_v, c_v)$:
$$\Delta g(u, v) = \text{geo\_dist}(u, v) \times \text{Cost}(v)$$
- For cardinal moves ($\Delta r = 0$ or $\Delta c = 0$): $\text{geo\_dist} = 1.0$.
- For diagonal moves ($|\Delta r| = 1$ and $|\Delta c| = 1$): $\text{geo\_dist} = \sqrt{2} \approx 1.41421356$.
- Initial condition: $g(\text{start}) = 0.0$. Entry cost is accumulated upon entering each subsequent cell.

#### Admissible Octile Heuristic:
$$h(r, c) = \left[ \max(\Delta r, \Delta c) + (\sqrt{2} - 1)\min(\Delta r, \Delta c) \right] \cdot \min_{\text{traversable}}(\text{Cost})$$
Because $\min(\text{Cost}) \le \text{Cost}(v)$ everywhere, $h(r, c)$ never overestimates the true remaining cost, guaranteeing mathematical optimality.

#### Corner-Cutting Prevention:
Diagonal move from $(r, c)$ to $(r+\Delta r, c+\Delta c)$ is permitted **if and only if** both adjacent orthogonal cells are traversable:
$$\text{Cost}(r+\Delta r, c) \neq \text{None} \quad \text{AND} \quad \text{Cost}(r, c+\Delta c) \neq \text{None}$$

#### Worked Numerical Example (3×3 Grid):
Consider a 3×3 grid:
```
Row 0:  [1.0 (clear),  3.0 (rocky),  1.0 (clear)]
Row 1:  [5.0 (loose),  None (BLOCKED), 1.0 (clear)]
Row 2:  [1.0 (clear),  1.0 (clear),  1.0 (clear)]
```
- Start: $(2, 0)$, Goal: $(0, 2)$.
- Step 1 from $(2,0)$ to $(2,1)$ (cardinal, clear): $\Delta g = 1.0 \times 1.0 = 1.0$, $g = 1.0$.
- Step 2 from $(2,1)$ to $(2,2)$ (cardinal, clear): $\Delta g = 1.0 \times 1.0 = 1.0$, $g = 2.0$.
- Step 3 from $(2,2)$ to $(1,2)$ (cardinal, clear): $\Delta g = 1.0 \times 1.0 = 1.0$, $g = 3.0$.
- Step 4 from $(1,2)$ to $(0,2)$ (cardinal, clear): $\Delta g = 1.0 \times 1.0 = 1.0$, $g = 4.0$.
- Alternative diagonal move from $(2,1)$ to $(1,2)$ passes through blocked corner $(1,1)$ where $\text{Cost}(1,1) = \text{None}$. Corner-cutting prevention rejects this diagonal!
- Final optimal path: $[(2,0), (2,1), (2,2), (1,2), (0,2)]$ with total cost $= 4.0$.

### 9.8 How the Route is Mapped onto the Original Image
Let original image have dimensions $W \times H$ (e.g. $1648 \times 1200$) and downsampled grid have dimensions $C \times R$ (e.g. $103 \times 75$).
Each grid cell $(r, c)$ maps to pixel coordinates:
$$x_{\text{min}} = c \cdot \frac{W}{C}, \quad x_{\text{max}} = (c + 1) \cdot \frac{W}{C}$$
$$y_{\text{min}} = r \cdot \frac{H}{R}, \quad y_{\text{max}} = (r + 1) \cdot \frac{H}{R}$$
Cell centroid:
$$x_{\text{center}} = \left(c + \frac{1}{2}\right) \frac{W}{C}, \quad y_{\text{center}} = \left(r + \frac{1}{2}\right) \frac{H}{R}$$
In the React canvas viewer (`InteractiveMapViewer.tsx`), the SVG overlay uses CSS grid with `aspectRatio: W / H` and `transform: translate(panOffset) scale(zoomLevel)`, preserving pixel-perfect spatial alignment across all device pixel ratios, pans, and zooms.

### 9.9 How Source and Destination Selection Works
1. Operator clicks **Rover Origin (S)** or **Destination (G)** in the viewport action bar.
2. Clicking a cell on the map fires `onClick(r, c)`.
3. If $\text{Cost}(r, c) == \text{None}$ (obstacle), the action is immediately blocked with an explanatory warning banner: *"Cell [r, c] is an impassable obstacle! Please select a traversable terrain cell."*
4. If traversable, the green `S` or amber `G` pin updates instantly.
5. Operator clicks **Replan Route (A\*)** directly in the viewport bar.
6. `recomputePath()` executes on the backend and updates the route, HUD telemetry, and cost breakdown in under 50ms.

### 9.10 Accurate API Status Telemetry
RoverMind uses an in-memory `ApiTelemetryTracker` that enforces strict truthfulness:
- `not_configured`: API key is empty in `.env`.
- `configured_untested`: Key is present but no live external request has succeeded yet.
- `last_request_successful`: A genuine HTTP request to Meta's endpoints returned HTTP 200 and valid JSON.
- `request_failed`: External call returned an error (sanitized to protect keys).
- The navbar and HUD badges strictly reflect this telemetry. Green `LIVE VERIFIED` is displayed **only** when verified by real external requests.

### 9.11 Cinematic Multi-Stage Rocket Launch Animation
The hero section features a dedicated vector launch system (`RocketHeroGraphic.tsx` & `PlanetaryNarrative.tsx`):
- Multi-layer composition: launch gantry tower, concrete blast deflector, retractable cryogenic umbilical arms, multi-stage spacecraft hull, aerospike engine bell, supersonic Mach shock diamonds, and volumetric ground deluge steam.
- Kinematic progression tied continuously to scroll progress ($p \in [0.0, 1.0]$):
  1. **Stage 1: Pre-Launch on Pad ($p \in [0.00, 0.08]$)**: Retaining clamps locked against rocket hull, gentle cryo boil-off vapor venting from interstage and booster valves.
  2. **Stage 2: Main Engine Ignition ($p \in [0.08, 0.28]$)**: Umbilical support arms swing backward by $36^\circ$, ignition flash emerges, shock-diamond plasma core expands, atmospheric ground light spill flares on the launch deck.
  3. **Stage 3: Supersonic Liftoff ($p \in [0.28, 0.75]$)**: Non-linear vertical acceleration ($y = -p_{\text{lift}}^{1.8} \times 600$), supersonic exhaust plume reaches full thrust, volumetric deluge ground smoke clouds billow laterally.
  4. **Stage 4: Space Ascent ($p \in [0.75, 1.00]$)**: Rocket exits beyond upper viewport into space; ground smoke gently dissipates as user transitions into surface operations.
- Reversible: Scrolling upward seamlessly reverses the launch, retracting the plume, swinging arms forward, and docking the rocket back onto the pad.
- Fully accessible: Adheres to `prefers-reduced-motion` and preserves 100% typography contrast via an ambient darkened radial scrim.

---

# 10. Meta Muse Spark Architecture & Provider Routing

### 10.1 Investigation & Compatibility Findings
Meta Muse Spark is Meta's state-of-the-art multimodal and reasoning model family developed by Meta Superintelligence Labs:
- **API Protocol**: Full drop-in OpenAI API compatibility (`/chat/completions`). Supports system/user messages, streaming Server-Sent Events (SSE), and OpenAI tool calling (`tools` / `tool_choice`).
- **Structured JSON Mode**: Supports `response_format={"type": "json_object"}` with strict JSON schema compliance.
- **Model Identifiers**:
  - `muse-spark-1.3`: Standard production reasoning release.
  - `muse-spark-1.3-contributor`: Contributor and hackathon tier access.
  - `muse-spark-open`: Open-weights endpoint variant.
- **Base URL**: Standard endpoint is `https://api.meta.ai/v1`. Partner cloud deployments include OpenRouter, Google Cloud Model Garden, Oracle Cloud Infrastructure, and AWS SageMaker.
- **Authentication**: Standard Bearer token (`Authorization: Bearer <API_KEY>`).
- **Access Restrictions & Graceful Fallback**: Contributor/hackathon accounts with early access can query `muse-spark-1.3-contributor` or allowlisted models. Accounts encountering HTTP 403 Forbidden or 404 Model Not Found automatically and seamlessly fall back to `llama-3.3-70b-instruct`, and subsequently to the deterministic rule engine without throwing unhandled exceptions.

### 10.2 Provider Routing Hierarchy
The pipeline implements a three-tier reasoning architecture:
1. **Primary Provider** (`REASONING_PROVIDER="muse-spark"`):
   Queries configured `MUSE_SPARK_MODEL` (default: `muse-spark-1.3`).
2. **Fallback Provider** (`FALLBACK_REASONING_PROVIDER="llama-3.3"`):
   Activated automatically if the primary provider raises an HTTP 403, 404, or network timeout.
3. **Deterministic Rule Engine** (`"deterministic-rule-engine"`):
   Offline fallback that computes ground-truth metrics directly from backend A* and costmap telemetry with zero hallucination.

### 10.3 Provenance Labeling Standards
Every response produced by the reasoning layer explicitly carries one of five standardized provenance tags:
- `LIVE — MUSE SPARK`: Live inference verified through Meta Muse Spark.
- `LIVE — LLAMA 3.3`: Live inference verified through Meta Llama 3.3 Instruct.
- `DETERMINISTIC — OFFLINE FALLBACK`: Generated deterministically from backend state when reasoning API is unconfigured, unreachable, or offline.
- `EXTERNAL INFERENCE DISABLED`: Blocked by the master kill switch (`EXTERNAL_API_ENABLED=false`).
- `DRY RUN`: Verified simulation with zero external HTTP calls dispatched (`EXTERNAL_API_DRY_RUN=true`).

---

# 11. Pre-Live API Security, Cost & Reliability Architecture

RoverMind enforces strict safety, cost, and rate controls before live API keys are introduced.

### 11.1 Master API Kill Switch (`EXTERNAL_API_ENABLED=false`)
- Default is **`false`**.
- Evaluated prior to every single external network call in `sam_service.py` and `reasoning_service.py`.
- When `false`, zero external network calls can be dispatched under any circumstances.
- Prevents unintended paid API consumption or accidental execution during development and testing.
- Updates the telemetry ledger with `blocked_kill_switch` event records.

### 11.2 Dry-Run Mode (`EXTERNAL_API_DRY_RUN=true`)
- Default is **`true`**.
- Validates prompt construction, payload sizes, token bounds, and schema formatting locally.
- Returns realistic simulated responses tagged with `DRY RUN`.
- Records dry-run verification in the persistent usage ledger without incurring network latency or API expense.

### 11.3 Hard Request & Cost Budgets
- **SAM Requests per Analysis**: Hard capped at `MAX_SAM_REQUESTS_PER_ANALYSIS=1`. If an operator submits multiple visual concepts, the list is safely truncated to 1, logging a budget enforcement diagnostic.
- **Reasoning Briefing Requests**: Hard capped at `MAX_REASONING_REQUESTS_PER_BRIEFING=1`.
- **Reasoning Chat Requests**: Hard capped at `MAX_REASONING_REQUESTS_PER_CHAT=1`.
- **Tool Iterations per Chat Turn**: Hard capped at `MAX_TOOL_ITERATIONS_PER_CHAT=2` (maximum 4).
- **Duplicate Tool Call Breaker**: Tracks tool signatures `(tool_name, arguments)` within the chat loop. If an identical call is made, the loop breaks immediately, preventing runaway cost spirals.
- **Tool Output Size Limit**: Tool results are truncated to `MAX_TOOL_OUTPUT_BYTES=8192` (8 KB) before entering LLM context.
- **Operator Input Character Bound**: Operator chat inputs are strictly truncated to `MAX_INPUT_TEXT_LENGTH=1000` characters.
- **Context Message Limit**: In-memory conversation history preserves at most `MAX_CONVERSATION_HISTORY_MESSAGES=10` turns.

### 11.4 Concurrency & In-Flight Request Caps
- Uses dedicated threading semaphores (`sam_semaphore`, `reasoning_semaphore`) limiting concurrent in-flight requests to `MAX_CONCURRENT_SAM_REQUESTS=1` and `MAX_CONCURRENT_REASONING_REQUESTS=1`.
- Prevents race conditions, duplicate submissions, and concurrency-induced rate limit exhaustion.

### 11.5 Network Reliability & Zero Automatic Retries
- `MAX_RETRIES=0`: OpenAI SDK automatic retries are disabled by default. If a rate limit (HTTP 429) or server error (HTTP 500) occurs, the system fails fast and falls back gracefully rather than burning token quota on automatic retry loops.
- Timeouts: Explicit connection timeout (`CONNECT_TIMEOUT_SECONDS=5.0s`) and read timeout (`READ_TIMEOUT_SECONDS=25.0s`).

### 11.6 Persistent Local Usage Ledger (`api_usage_ledger.json`)
- Stored at project root and tracked in `.gitignore` to prevent committing usage telemetry.
- Persists cumulative statistics across application and server restarts:
  - Total SAM requests attempted, succeeded, failed, blocked by kill switch, and dry-run simulated.
  - Total Reasoning requests attempted, succeeded, failed, blocked by kill switch, and dry-run simulated.
  - Breakdown by model identifier (`muse-spark-1.3`, `llama-3.3-70b-instruct`).
  - Rolling log of the last 50 events with ISO 8601 UTC timestamps.
- Written atomically to disk with file locking to ensure complete thread and process safety.
