# RoverMind Live API Workflow & Meta SAM 3.1 Verification Guide

This document provides an exhaustive, end-to-end architectural walkthrough of how RoverMind operates when `META_API_KEY` is configured in the environment. It details the complete data flow from environment discovery to token parsing, raster decoding, costmap derivation, and A* path planning.

---

## 1. High-Level Lifecycle Diagram

```mermaid
sequenceDiagram
    autonumber
    actor Analyst as Planetary Analyst / UI
    participant Backend as FastAPI Orchestrator
    participant Config as App Settings (.env)
    participant ImageSvc as Image Store (Pillow)
    participant SAM as Meta SAM 3.1 Service
    participant MetaAPI as Meta AI Endpoint (api.meta.ai/v1)
    participant Parser as meta-sam-parser
    participant Normalizer as Terrain Interpreter
    participant Costmap as Costmap Engine
    participant Planner as Custom A* Engine

    Analyst->>Backend: POST /api/analysis/run (image_id, concepts, costs)
    Backend->>Config: Check is_meta_api_configured
    Config-->>Backend: Return True (META_API_KEY detected)
    Backend->>ImageSvc: get_image_data_url(image_id)
    ImageSvc-->>Backend: data:image/png;base64,...
    Backend->>SAM: run_live_sam_segmentation(...)
    loop For Each Concept ("rock", "sand", "obstacle")
        SAM->>MetaAPI: POST /v1/responses (model="sam-3.1", input=[prompt, image_url])
        MetaAPI-->>SAM: Tokenized response stream (SAM grammar format)
        SAM->>Parser: push(token_stream) + finish(CompletedOutcome)
        Parser-->>SAM: List[SegmentationMaskRecord]
        SAM->>SAM: decode_mask_to_raster() + coordinate alignment
    end
    SAM->>Normalizer: Raw discrete concept grid
    Normalizer-->>SAM: Normalized SegmentationResult
    SAM-->>Backend: SegmentationResponse + MaskRecordDtos
    Backend->>Costmap: build_cost_map(terrain_grid, terrain_costs)
    Costmap-->>Backend: 2D Cost Grid
    Backend->>Planner: find_path(cost_grid, start, goal)
    Planner-->>Backend: PathResult (waypoints, cost, status)
    Backend-->>Analyst: FullAnalysisResponse (JSON)
```

---

## 2. Step-by-Step Workflow Walkthrough

### Step 1: Configuration Discovery & Secrets Loading
- **Files Involved**: `backend/app/core/config.py`, `.env`
- **Class / Engine**: `Settings(BaseSettings)`
- **Behavior**:
  1. On application startup, `pydantic-settings` inspects the `.env` file located at the repository root.
  2. If `META_API_KEY` is set to a non-empty string, `settings.meta_api_key` stores the value in memory.
  3. The computed property `settings.is_meta_api_configured` evaluates to `True`.
  4. The `/api/health` endpoint reports:
     ```json
     {
       "status": "healthy",
       "meta_api_configured": true,
       "supported_models": ["sam-3.1", "sam-3.1-offline-synthetic"]
     }
     ```
  5. The API key is stored securely in backend server memory and is **never** transmitted to the browser, logged, or reflected in API responses.

### Step 2: Image Ingestion & Validation
- **Files Involved**: `backend/app/api/routes/images.py`, `backend/app/services/image_service.py`
- **Class / Engine**: `Pillow`, `validate_and_store_image()`, `ImageMetadata`
- **Behavior**:
  1. An image is uploaded via `POST /api/images/upload` or loaded from sample via `POST /api/images/load-sample`.
  2. The image bytes are inspected by Pillow with decompression bomb detection active (`Image.MAX_IMAGE_PIXELS = 25_000_000`).
  3. Format must be `image/jpeg` or `image/png`. Max dimensions are capped at $8192 \times 8192$.
  4. The image is stored in the thread-safe `_IMAGE_STORE` (LRU cache with a maximum capacity of 25 active session frames).
  5. When requested for live SAM analysis, `get_image_data_url(image_id)` transforms the raw bytes into a Base64-encoded `data:image/png;base64,...` data URL.

### Step 3: Meta SAM 3.1 Client Invocation
- **Files Involved**: `backend/app/services/sam_service.py`
- **Class / Engine**: `openai.OpenAI`, `httpx.Timeout`
- **Behavior**:
  1. The client is initialized against Meta's v1 base URL:
     ```python
     client = openai.OpenAI(
         base_url="https://api.meta.ai/v1",
         api_key=settings.meta_api_key,
         timeout=httpx.Timeout(30.0, connect=10.0)
     )
     ```
  2. For each query concept (e.g. `["rock", "sand", "obstacle"]`), RoverMind constructs the SAM 3.1 prompt message:
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
  3. The response text containing SAM's structured grammar tokens is extracted.

### Step 4: Token Stream Parsing with `meta-sam-parser`
- **Files Involved**: `backend/app/services/sam_service.py`, `backend/app/services/mask_reconstruction.py`
- **Class / Engine**: `meta_sam_parser` (`sam.image_segmentation_format()`, `sam.CompletedOutcome()`)
- **Behavior**:
  1. The raw grammar token text emitted by the model is passed into the official parser:
     ```python
     response_format = sam.image_segmentation_format()
     parser = response_format.create_parser()
     parser.push(response_text)
     finished = parser.finish(sam.CompletedOutcome())
     result = finished.result
     ```
  2. The parser produces a typed abstract syntax tree containing `SegmentationMaskRecord` objects.
  3. Each record contains:
     - `object_id`: Unique identifier for the segmented mask region.
     - `mask`: Encoded run-length / bitmap representation with width and height.
     - `bounds`: Geometric boundary box (`left`, `top`, `right`, `bottom`).
     - `confidence`: Optional model confidence scalar.

### Step 5: Mask Decoding, Coordinate Alignment & Grid Reconstruction
- **Files Involved**: `backend/app/services/mask_reconstruction.py`
- **Class / Engine**: `sam.decode_mask_to_raster()`, `DecodedMask`, `reconstruct_grid_from_masks()`
- **Behavior**:
  1. `sam.decode_mask_to_raster(record.mask)` unrolls the binary foreground/background byte raster.
  2. Bounds coordinates are evaluated: if normalized ($[0..1]$), they are multiplied by image dimensions ($W \times H$); if absolute, they are clamped to image frame extents.
  3. The decoded mask raster is spatially downsampled and projected onto the discrete grid ($R \times C$).
  4. Where multiple masks overlap on the same grid cell, `concept_priorities` resolves conflicts (e.g., `obstacle` (priority 3) overrides `rock` (priority 2), which overrides `sand` (priority 1)).

### Step 6: Normalized Terrain Classification
- **Files Involved**: `backend/app/services/terrain_interpreter.py`
- **Class / Engine**: `build_normalized_segmentation()`, `SegmentationResult`
- **Behavior**:
  1. The raw grid is translated into standard normalized terrain categories:
     - `clear` (traversable bedrock / firm soil)
     - `sand` (loose drift / elevated slip risk)
     - `rock` (rough rocky terrain)
     - `obstacle` (impassable boulder / steep crater lip)
  2. The resulting `SegmentationResult` carries metadata denoting `source_model="sam-3.1"` and `is_synthetic=False`.

### Step 7: Costmap Generation & A* Path Planning
- **Files Involved**: `backend/app/services/terrain_costmap.py`, `backend/app/services/path_planner.py`
- **Class / Engine**: `build_cost_map()`, `find_path()`
- **Behavior**:
  1. `build_cost_map` assigns impedance weights to each grid cell according to configured terrain costs (default: `clear: 1.0`, `sand: 3.5`, `rock: 6.0`, `obstacle: 999.0`).
  2. `find_path` executes RoverMind's custom 8-directional A* search with Euclidean heuristic and diagonal transition penalties ($d \times \sqrt{2}$).
  3. The response contains full waypoint coordinates, route distance, cumulative cost, and execution time.

---

## 3. Offline vs. Live Mode Differentiation

RoverMind is engineered with a strict distinction between live inference and offline synthetic demonstration:

| Dimension | Live Mode (`META_API_KEY` present) | Offline Demo Mode (`META_API_KEY` absent) |
|---|---|---|
| **Health API Status** | `"meta_api_configured": true` | `"meta_api_configured": false` |
| **Model Identifier** | `"sam-3.1"` | `"sam-3.1-offline-synthetic"` |
| **Data Provenance** | Real SAM 3.1 model predictions via Meta API | Labelled synthetic test patterns |
| **Synthetic Flag** | `is_synthetic: false` | `is_synthetic: true` |
| **Diagnostics Message** | Model diagnostics or execution timestamps | Explicit `SYNTHETIC DEMO DATA` disclaimer |
| **UI Mission Badge** | Green: `● LIVE SAM 3.1 ACTIVE` | Amber: `⚡ OFFLINE SYNTHETIC DEMO` |

---

## 4. Step-by-Step Activation Instructions (PowerShell)

To activate live SAM 3.1 inference on Windows PowerShell:

### 1. Set your Meta API Key
Create or edit the `.env` file in the `RoverMind` repository root:
```powershell
# Open or create .env in the repository root
Set-Content -Path .\.env -Value "META_API_KEY=your_actual_meta_api_key_here"
```

Alternatively, export it into your current PowerShell environment:
```powershell
$env:META_API_KEY = "your_actual_meta_api_key_here"
```

### 2. Verify Key Discovery via Health Endpoint
Start or restart the backend server:
```powershell
.\.venv\Scripts\uvicorn.exe backend.app.main:app --host 127.0.0.1 --port 8000
```
Then query the health check:
```powershell
Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/health" | ConvertTo-Json
```
**Expected Response:**
```json
{
  "status": "healthy",
  "meta_api_configured": true,
  "supported_models": [
    "sam-3.1",
    "sam-3.1-offline-synthetic"
  ]
}
```

### 3. Execute Live Analysis
```powershell
# 1. Load sample image
$upload = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/images/load-sample" -Method Post
$imageId = $upload.metadata.image_id

# 2. Trigger live segmentation and path planning
$body = @{
    image_id = $imageId
    concepts = @("rock", "sand", "obstacle")
    start_point = @{ x = 2; y = 2 }
    goal_point = @{ x = 30; y = 20 }
} | ConvertTo-Json

$analysis = Invoke-RestMethod -Uri "http://127.0.0.1:8000/api/analysis/run" -Method Post -Body $body -ContentType "application/json"
$analysis.segmentation.source_model
# Returns: "sam-3.1"
$analysis.segmentation.is_synthetic
# Returns: false
```
