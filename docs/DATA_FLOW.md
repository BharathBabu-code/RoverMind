# RoverMind — Data Flow Trace

This document provides a step-by-step trace of a single image analysis transaction moving through the entire RoverMind system.

---

## Complete End-to-End Walkthrough

### Step 1: User Selects or Drops an Image
- **Location**: Browser / React UI (`ImageUploadPanel.tsx`)
- **Action**: The mission operator drags `rover_image.png` into the upload zone or clicks "Load Authentic Rover Sample".
- **Payload**: A browser `File` object (MIME `image/png`, 4,454,540 bytes, 1648×1200 px).

---

### Step 2: Browser Dispatches Multipart Upload Request
- **Location**: `frontend/src/services/api.ts` -> `uploadRoverImage()`
- **HTTP Call**:
  ```http
  POST /api/images/upload HTTP/1.1
  Content-Type: multipart/form-data; boundary=----WebKitFormBoundaryXYZ
  
  ------WebKitFormBoundaryXYZ
  Content-Disposition: form-data; name="file"; filename="rover_image.png"
  Content-Type: image/png
  
  [Binary PNG Bytes]
  ------WebKitFormBoundaryXYZ--
  ```

---

### Step 3: FastAPI Ingestion & Pillow Header Validation
- **Location**: `backend/app/api/routes/images.py` -> `upload_image()`
- **Processing**:
  1. `file.read()` extracts raw bytes in memory.
  2. `validate_and_store_image()` executes a two-pass Pillow verification:
     - Pass 1: `Image.open().verify()` inspects header chunk integrity.
     - Pass 2: Re-opens to extract `width=1648`, `height=1200`, `format='PNG'`.
  3. Validates that size is within 20MB limit and dimensions are within 8192×8192.
  4. Generates a unique UUID (`image_id`).
  5. Stores `(bytes, metadata)` in the `_IMAGE_STORE` dictionary.
- **Response**:
  ```json
  {
    "success": true,
    "metadata": {
      "image_id": "8d3e9f4a-71b2-482a-bc93-5e7e6a1d48c0",
      "filename": "rover_image.png",
      "width": 1648,
      "height": 1200,
      "mime_type": "image/png",
      "file_size_bytes": 4454540
    },
    "message": "Image successfully validated and stored."
  }
  ```

---

### Step 4: Frontend Triggers Analysis Execution
- **Location**: `frontend/src/App.tsx` -> `runFullAnalysis()`
- **HTTP Call**:
  ```http
  POST /api/analysis/run HTTP/1.1
  Content-Type: application/json

  {
    "image_id": "8d3e9f4a-71b2-482a-bc93-5e7e6a1d48c0",
    "concepts": ["rock", "sand", "obstacle"],
    "grid_downsample_factor": 24,
    "allow_diagonal": true
  }
  ```

---

### Step 5: Grid Resolution Calculation
- **Location**: `backend/app/services/analysis_orchestrator.py`
- **Calculation**:
  $$\text{grid\_cols} = \text{max}(4, \min(120, 1648 // 24)) = 68$$
  $$\text{grid\_rows} = \text{max}(4, \min(120, 1200 // 24)) = 50$$
- Resulting decision grid: $50 \text{ rows} \times 68 \text{ columns}$.

---

### Step 6: Visual Segmentation (SAM 3.1 or Offline Fixture)
- **Location**: `backend/app/services/sam_service.py`
- **Branch A (Live Mode with `META_API_KEY`)**:
  - Image is converted to Base64 Data URL (`data:image/png;base64,...`).
  - Calls `client.responses.create(model="sam-3.1", input=[...])` for prompt `"rock"`.
  - Response text contains special tokens (e.g. `<|box_start|>...<|mask_start|>!...`).
- **Branch B (Offline Demonstration Mode)**:
  - If `META_API_KEY` is empty, invokes `generate_synthetic_offline_segmentation()`.
  - Labels outputs with `source_model="sam-3.1-offline-synthetic"`, `is_synthetic=true`.

---

### Step 7: Grammar Parsing & Mask Decoding
- **Location**: `backend/app/services/mask_reconstruction.py`
- **Parsing**:
  ```python
  response_format = sam.image_segmentation_format()
  parser = response_format.create_parser()
  parser.push(response_text)
  finished = parser.finish(sam.CompletedOutcome())
  result = finished.result
  ```
- **Decoding**:
  ```python
  raster = sam.decode_mask_to_raster(record.mask)
  # Returns 1-byte-per-pixel flat bytes array (length: width * height)
  ```

---

### Step 8: Spatial Projection & Priority Conflict Arbitration
- **Location**: `backend/app/services/mask_reconstruction.py` -> `reconstruct_grid_from_masks()`
- Each grid cell $(r, c)$ corresponds to an image rectangle:
  $$x \in [c \cdot \Delta w, (c+1) \cdot \Delta w), \quad y \in [r \cdot \Delta h, (r+1) \cdot \Delta h)$$
- If multiple masks cover cell $(r, c)$, conflict resolution chooses the highest hazard priority:
  $$\text{obstacle } (100) > \text{rocky } (70) > \text{loose } (50) > \text{unknown } (30) > \text{clear } (10)$$
- Uncovered cells default to `"clear"`.

---

### Step 9: Normalization Contract
- **Location**: `backend/app/services/terrain_interpreter.py`
- Calls `normalize_segmentation(region_grid, region_labels, 1648, 1200, "sam-3.1")`.
- Produces a validated `SegmentationResult` where `terrain_grid` is a $50 \times 68$ matrix of strings.

---

### Step 10: Costmap Compilation
- **Location**: `backend/app/services/terrain_costmap.py` -> `build_cost_map()`
- Translates string labels into floating-point traversal costs:
  - `"clear"` $\to 1.0$
  - `"rocky"` $\to 3.0$
  - `"loose"` $\to 5.0$
  - `"unknown"` $\to 2.0$
  - `"obstacle"` $\to \text{None (Impassable)}$
- Generates `cost_grid` of dimensions $50 \times 68$.

---

### Step 11: Authoritative Custom A* Pathfinding
- **Location**: `backend/app/services/path_planner.py` -> `find_path()`
- Start coordinate: $(49, 34)$ (bottom center).
- Goal coordinate: $(0, 34)$ (top center).
- Explores priority queue using Octile distance heuristic:
  $$h = \max(\Delta r, \Delta c) + (\sqrt{2} - 1) \min(\Delta r, \Delta c) \cdot \text{min\_cost}$$
- Enforces corner-cutting prevention on diagonal moves.
- Reconstructs path by following `came_from` parent pointers.

---

### Step 12: Backend Delivers Full Response to Browser
- Returns `FullAnalysisResponse` containing:
  - Image metadata
  - 2D `terrain_grid`
  - 2D `cost_grid`
  - `path_result` with waypoints list: `[[49, 34], [48, 35], ...]`
  - Diagnostics logs

---

### Step 13: Interactive Presentation in Browser
- **Location**: `frontend/src/components/InteractiveMapViewer.tsx`
- Renders:
  - Original rover image backdrop.
  - Spatially aligned SVG/CSS grid with color-coded cells.
  - Start marker (S, green) and Goal marker (G, amber).
  - Blue glowing waypoint line for the calculated route.
  - Telemetry HUD showing cumulative cost, geometric distance, and expanded nodes.

---

### Step 14: Mission Registration & Structured Context Compilation
- **Location**: `backend/app/services/analysis_orchestrator.py` & `backend/app/services/mission_context.py`
- **Processing**:
  1. Once `run_full_analysis()` completes, it invokes `store_analysis(image_id, result)`.
  2. The run is indexed in `_ANALYSIS_STORE` (thread-safe LRU store, bounded to 25 entries).
  3. `build_mission_context(image_id)` computes high-level telemetry metrics:
     - Terrain coverage distribution (cells and percentages per canonical class).
     - Hazard density ($\% \text{obstacle} + \% \text{rocky}$).
     - Route characteristics (waypoint count, straight-line Euclidean distance, path tortuosity ratio $\frac{L}{\text{Euclidean}}$, average traversal cost per step).
     - Safety margin (distance from nearest obstacle cell to route waypoints).
     - Model provenance (e.g., `sam-3.1-offline-synthetic` vs. live SAM 3.1).
- **Output**: `MissionContextDto` object ready for reasoning model consumption or API clients.

---

### Step 15: Meta Reasoning Model Briefing Generation
- **Location**: `backend/app/services/reasoning_service.py` -> `generate_live_mission_briefing()` / `generate_deterministic_briefing()`
- **HTTP Call**:
  ```http
  POST /api/mission/{image_id}/briefing/generate HTTP/1.1
  Content-Type: application/json
  ```
- **Execution Branches**:
  - **Branch A (Live Reasoning with `META_REASONING_API_KEY`)**:
    - Instantiates `openai.OpenAI(api_key=..., base_url=...)`.
    - Formats verified mission context into system/user prompts with strict ground-truth constraints.
    - Sends structured request to `llama-3.3-70b-instruct` with JSON schema enforcement (`response_format={"type": "json_object"}`).
    - Decodes 4 mandatory structured sections:
      1. `observation_overview`: Image resolution, dominant terrain, general layout.
      2. `navigation_assessment`: Traversal feasibility, path tortuosity, hazard bottlenecks.
      3. `risk_and_uncertainty`: Slope ambiguity, subsurface wheel slip, sensor blindness.
      4. `key_takeaways`: Prioritized operational guidance bullets.
  - **Branch B (Deterministic Offline Fallback)**:
    - If `META_REASONING_API_KEY` is absent or upstream call fails, invokes `generate_deterministic_briefing()`.
    - Computes briefing purely from verified statistical rules without hallucination.
    - Annotates payload with `model="deterministic-rule-engine"` and `is_synthetic=false`.
- **Response**: `MissionBriefing` JSON object delivered to `MissionIntelligencePanel.tsx`.

---

### Step 16: Interactive Mission Chatbot & Controlled Tool Invocations
- **Location**: `backend/app/api/routes/mission.py` -> `POST /api/mission/chat` -> `reasoning_service.py`
- **Chatbot Turn Execution Flow**:
  1. Frontend submits user query (e.g. *"What is the terrain breakdown?"* or *"What if rocky terrain cost is 15.0?"*).
  2. Mission-isolated history in `_CONVERSATION_STORE` (bounded to 20 messages per session) retrieves prior conversation turns.
  3. Context injector appends active `MissionContextDto` ground-truth summary.
  4. Reasoning agent evaluates query against 6 sandboxed tools:
     - `get_mission_summary`: High-level operational summary.
     - `get_terrain_distribution`: Exact cell counts and area percentages.
     - `get_region_details`: Inspection of specific coordinates or bounding boxes.
     - `get_route_metrics`: Waypoints, cumulative cost, and path tortuosity.
     - `compare_routes`: Non-mutating simulation of alternative terrain costs using `find_path()`.
     - `get_analysis_diagnostics`: Processing latencies and model provenance.
  5. Live Tool Loop executes up to 4 iterations:
     - LLM requests tool call $\to$ backend executes tool $\to$ returns tool result to LLM $\to$ LLM synthesizes final answer.
  6. If reasoning API is offline, the deterministic query interpreter handles queries via pattern-matched rules.
  7. Final answer is logged with tool execution records and returned to `MissionChatbot.tsx` in the frontend HUD.
