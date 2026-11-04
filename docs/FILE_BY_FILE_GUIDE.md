# RoverMind — Exhaustive File-by-File Guide

This guide provides a comprehensive technical breakdown of every source file across the RoverMind repository.

---

# TABLE OF CONTENTS
1. [Backend Modules](#1-backend-modules)
   - [backend/app/main.py](#backendappmainpy)
   - [backend/app/core/config.py](#backendappcoreconfigpy)
   - [backend/app/schemas/models.py](#backendappschemasmodelspy)
   - [backend/app/services/path_planner.py](#backendappservicespath_plannerpy)
   - [backend/app/services/terrain_costmap.py](#backendappservicesterrain_costmappy)
   - [backend/app/services/segmentation_contract.py](#backendappservicessegmentation_contractpy)
   - [backend/app/services/segmentation_adapter.py](#backendappservicessegmentation_adapterpy)
   - [backend/app/services/mask_reconstruction.py](#backendappservicesmask_reconstructionpy)
   - [backend/app/services/terrain_interpreter.py](#backendappservicesterrain_interpreterpy)
   - [backend/app/services/image_service.py](#backendappservicesimage_servicepy)
   - [backend/app/services/sam_service.py](#backendappservicessam_servicepy)
   - [backend/app/services/analysis_orchestrator.py](#backendappservicesanalysis_orchestratorpy)
   - [backend/app/api/routes/health.py](#backendappapirouteshealthpy)
   - [backend/app/api/routes/images.py](#backendappapiroutesimagespy)
   - [backend/app/api/routes/analysis.py](#backendappapiroutesanalysispy)
   - [backend/app/api/routes/planning.py](#backendappapiroutesplanningpy)
2. [Frontend Modules](#2-frontend-modules)
   - [frontend/src/App.tsx](#frontendsrcapptsx)
   - [frontend/src/main.tsx](#frontendsrcmaintsx)
   - [frontend/src/services/api.ts](#frontendsrcservicesapits)
   - [frontend/src/types/api.ts](#frontendsrctypesapits)
   - [frontend/src/components/Navbar.tsx](#frontendsrccomponentsnavbartsx)
   - [frontend/src/components/SpacecraftCursor.tsx](#frontendsrccomponentsspacecraftcursortsx)
   - [frontend/src/components/ImageUploadPanel.tsx](#frontendsrccomponentsimageuploadpaneltsx)
   - [frontend/src/components/InteractiveMapViewer.tsx](#frontendsrccomponentsinteractivemapviewertsx)
   - [frontend/src/components/PathPlanningPanel.tsx](#frontendsrccomponentspathplanningpaneltsx)
   - [frontend/src/components/DiagnosticsPanel.tsx](#frontendsrccomponentsdiagnosticspaneltsx)
   - [frontend/src/components/MethodologyModal.tsx](#frontendsrccomponentsmethodologymodaltsx)
3. [Configuration & Environment Files](#3-configuration--environment-files)
   - [.env.example](#envexample)
   - [requirements.txt](#requirementstxt)
   - [.gitignore](#gitignore)
4. [Test Suite Modules](#4-test-suite-modules)

---

# 1. Backend Modules

---

### `backend/app/main.py`
- **Responsibility**: Application root entry point. Instantiates the FastAPI application, mounts CORS middleware, registers all route blueprints, and mounts the compiled React frontend static files.
- **Why it exists**: Serves as the central server coordinating all incoming HTTP traffic from browsers, mission operators, and automated testing tools.
- **Imports & Dependencies**: `FastAPI`, `CORSMiddleware`, `StaticFiles` from Starlette, `ROOT_DIR` from `config.py`, and route routers (`health`, `images`, `analysis`, `planning`).
- **Classes & Functions**:
  - `app`: The top-level FastAPI instance.
- **Execution Flow**:
  1. Bootstraps FastAPI with API title, version, and description.
  2. Applies `CORSMiddleware` with unrestricted origins for local development.
  3. Registers routes under both root (`/health`, `/images/...`) and `/api` prefix (`/api/health`, `/api/images/...`) for backwards compatibility.
  4. Inspects if `frontend/dist` exists; if so, mounts `StaticFiles` at `/` so the frontend is served out-of-the-box on port 8000.
- **Callers**: Uvicorn server (`uvicorn backend.app.main:app`), `TestClient` in automated test suites.
- **Edge Cases**: Missing `frontend/dist` during early backend-only execution does not crash the server; the check is guarded with `dist_dir.exists()`.
- **Tests Covering It**: `backend/tests/test_health.py`, `backend/tests/test_api_routes.py`.

---

### `backend/app/core/config.py`
- **Responsibility**: Environment variable discovery, loading, and credential encapsulation.
- **Why it exists**: Prevents secret leaks, ensures safe loading from the root `.env` file, and provides read-only properties for external modules.
- **Imports & Dependencies**: `os`, `pathlib.Path`, `dotenv.load_dotenv`.
- **Classes & Functions**:
  - `Settings`: Encapsulates `META_API_KEY` access.
  - `is_meta_api_configured`: Property returning `bool`. Returns `True` only if `META_API_KEY` exists and contains non-whitespace characters.
  - `meta_api_key`: Property providing read-only access to the secret key.
  - `settings`: Global singleton instance.
- **Callers**: `sam_service.py`, `health.py`, `test_health.py`, `analysis_orchestrator.py`.
- **Tests Covering It**: `backend/tests/test_health.py` (credential leak test).

---

### `backend/app/schemas/models.py`
- **Responsibility**: Data Transfer Object (DTO) contracts and Pydantic schema validation.
- **Why it exists**: Establishes strict type safety for API requests and responses, guaranteeing synchronization between the backend and TypeScript frontend.
- **Key Schemas**:
  - `HealthResponse`: Status indicator (`ok`), service name, and version.
  - `ConfigStatusResponse`: Model status, offline indicator, and human-readable explanation.
  - `ImageMetadata`: Validated image ID, filename, width, height, MIME type, and byte size.
  - `ImageUploadResponse`: Wrapper returning upload status and `ImageMetadata`.
  - `MaskRecordDto`: Bounding box coordinates (`left`, `top`, `right`, `bottom`), concept label, pixel area, and confidence.
  - `SegmentationResponse`: 2D terrain grid, mask records, source model identifier, synthetic flag, and diagnostics.
  - `CostmapResponse`: Numeric 2D cost grid (floats with `None` for impassable) and the active terrain-to-cost mapping dictionary.
  - `PathPlanRequest`: Query containing `start` tuple, `goal` tuple, optional `cost_grid`, optional `image_id`, and `allow_diagonal` flag.
  - `PathPlanResponse`: Detailed route result with `is_success`, ordered `path` coordinate list, cumulative cost, geometric length, and expanded nodes.
  - `FullAnalysisRequest` & `FullAnalysisResponse`: Complete end-to-end payload aggregating all steps.

---

### `backend/app/services/path_planner.py`
- **Responsibility**: Custom A* algorithm for discrete 2D grid pathfinding.
- **Why it exists**: Authoritative path calculation service. Replaces third-party graph libraries with an exact, auditable implementation.
- **Key Classes & Functions**:
  - `PathResult`: Dataclass returning `is_success`, `path`, `total_weighted_cost`, `geometric_length`, and `expanded_nodes`.
  - `_validate_grid_and_get_min_cost(grid)`: Validates rectangular structure, rejects booleans and NaNs, and extracts the minimum cost for heuristic scaling.
  - `_validate_coord(grid, coord, name)`: Validates integer coordinates, bounds checking, and non-blocked status.
  - `_calculate_heuristic(...)`: Computes admissible heuristics (Manhattan for 4-way, Octile for 8-way diagonal), scaled by `min_cost`.
  - `find_path(cost_grid, start, goal, allow_diagonal=False)`: Core A* loop using a min-heap priority queue.
- **Corner-Cutting Prevention**:
  When evaluating a diagonal step from $(r, c)$ to $(r + dr, c + dc)$, both adjacent cardinal cells—$(r + dr, c)$ and $(r, c + dc)$—must be non-None (traversable). If either is blocked, the diagonal move is rejected.
- **Tests Covering It**: `backend/tests/test_path_planner.py` (25 comprehensive test cases).

---

### `backend/app/services/terrain_costmap.py`
- **Responsibility**: Compiles a 2D grid of terrain string labels into a numeric traversal cost grid.
- **Why it exists**: Bridges qualitative visual terrain classification and quantitative algorithmic pathfinding.
- **Key Function**:
  - `build_cost_map(terrain_grid, terrain_costs)`:
    - Input: 2D rectangular list of strings and a dictionary mapping string labels to non-negative floats (or `None`).
    - Output: 2D list of floats with `None` representing impassable terrain.
    - Non-mutating: Inputs are never modified in place.
    - Validation: Rejects malformed rows, ragged grids, booleans, infinite values, negative costs, or missing label keys.
- **Tests Covering It**: `backend/tests/test_terrain_costmap.py` (16 test cases).

---

### `backend/app/services/segmentation_contract.py`
- **Responsibility**: Provider-independent data contract for segmentation results.
- **Why it exists**: Ensures that any upstream visual model delivers a strictly validated terrain grid before entering the pipeline.
- **Key Class**:
  - `SegmentationResult`:
    - Fields: `terrain_grid` (2D list of strings), `image_width` (int), `image_height` (int), `source_model` (str).
    - Post-init Validation: Checks dimensions are strictly positive integers (rejecting booleans), validates non-empty grid strings, and creates a defensive copy of the grid.
- **Tests Covering It**: `backend/tests/test_segmentation_contract.py` (13 test cases).

---

### `backend/app/services/segmentation_adapter.py`
- **Responsibility**: Normalizes raw integer region grids into the canonical `SegmentationResult` contract.
- **Why it exists**: Translates upstream integer region labels into standardized string labels.
- **Key Function**:
  - `normalize_segmentation(region_grid, region_labels, image_width, image_height, source_model)`:
    - Translates integer cells to string labels via `region_labels[cell]`.
    - Enforces non-negative integer cell validation and checks that all IDs exist in the mapping.
- **Tests Covering It**: `backend/tests/test_segmentation_adapter.py` (19 test cases).

---

### `backend/app/services/mask_reconstruction.py`
- **Responsibility**: Decodes tokenized masks and projects them onto the image coordinate space.
- **Why it exists**: SAM returns binary rasters and box bounds that must be geometrically mapped onto the discrete mission grid.
- **Key Classes & Functions**:
  - `DecodedMask`: Dataclass holding `object_id`, `concept`, `width`, `height`, `raster` bytes, `bounds` tuple, and `confidence`.
  - `decode_and_align_mask(record, concept, image_width, image_height)`: Calls `meta-sam-parser.decode_mask_to_raster()` and scales normalized/pixel bounds to source-media coordinates.
  - `reconstruct_grid_from_masks(masks, image_width, image_height, grid_rows, grid_cols, concept_priorities)`: Discretizes masks onto grid cells, arbitrating overlapping regions using concept priorities.
- **Tests Covering It**: `backend/tests/test_mask_reconstruction.py`.

---

### `backend/app/services/terrain_interpreter.py`
- **Responsibility**: Maps visual concepts to standardized terrain labels and manages hazard prioritization.
- **Why it exists**: Visual models detect semantic concepts (e.g., "boulder", "ripple"), which must be mapped to operational terrain classes (`rocky`, `loose`, `obstacle`, `clear`, `unknown`).
- **Key Mappings & Constants**:
  - `CANONICAL_TERRAIN_LABELS`: Set of supported terrain labels.
  - `CONCEPT_TO_TERRAIN_MAP`: Dictionary mapping visual nouns to terrain classes.
  - `TERRAIN_PRIORITY`: Hazard priority weights (`obstacle`: 100, `rocky`: 70, `loose`: 50, `unknown`: 30, `clear`: 10).
  - `DEFAULT_TERRAIN_COSTS`: Configured traversal costs (`clear`: 1.0, `rocky`: 3.0, `loose`: 5.0, `unknown`: 2.0, `obstacle`: `None`).
  - `build_normalized_segmentation(...)`: Prepares integer region maps and invokes `normalize_segmentation`.
- **Tests Covering It**: `backend/tests/test_terrain_interpreter.py`.

---

### `backend/app/services/image_service.py`
- **Responsibility**: In-memory storage, format verification, and data URL preparation for uploaded images.
- **Why it exists**: Provides safe temporary handling without persisting untrusted files to arbitrary filesystem paths.
- **Key Functions**:
  - `validate_and_store_image(file_bytes, original_filename)`: Two-pass Pillow verification (integrity verify, then property extraction); enforces 20MB limit and 8192px dimension limits.
  - `get_image_bytes(image_id)`: Fetches binary payload.
  - `get_image_metadata(image_id)`: Fetches metadata.
  - `get_image_data_url(image_id)`: Base64 encodes the image for API consumption.
- **Tests Covering It**: `backend/tests/test_image_service.py`.

---

### `backend/app/services/sam_service.py`
- **Responsibility**: Interfaces with Meta SAM 3.1 API and provides offline synthetic fallback fixtures.
- **Why it exists**: Encapsulates external AI requests and guarantees that the system functions gracefully in offline mode when credentials are not configured.
- **Key Functions**:
  - `run_live_sam_segmentation(...)`: Queries Meta's OpenAI-compatible endpoint with noun phrases and decodes outputs using `meta-sam-parser`.
  - `generate_synthetic_offline_segmentation(...)`: Synthesizes labelled test fixtures representing Martian terrain features for structural testing without network access.

---

### `backend/app/services/analysis_orchestrator.py`
- **Responsibility**: Coordinates the full pipeline from image retrieval through path planning.
- **Why it exists**: Provides a single service call for end-to-end analysis execution.
- **Key Function**:
  - `run_full_analysis(request)`: Retrieves image, determines spatial grid downsampling, runs segmentation (live or synthetic), compiles the costmap, and executes default or custom A* path planning.

---

### `backend/app/api/routes/health.py`
- **Responsibility**: Health probe and model configuration status endpoints.
- **Endpoints**:
  - `GET /health`: Returns 200 OK with service identifier.
  - `GET /config`: Returns AI configuration status without leaking API keys.

---

### `backend/app/api/routes/images.py`
- **Responsibility**: Image upload, sample image loading, and raw binary streaming.
- **Endpoints**:
  - `POST /images/upload`: Handles multipart form file uploads.
  - `POST /images/load-sample`: Ingests the authentic repository `rover_image.png`.
  - `GET /images/{image_id}/metadata`: Retrieves image metadata.
  - `GET /images/{image_id}/raw`: Streams image binary bytes.

---

### `backend/app/api/routes/analysis.py`
- **Responsibility**: Dispatches end-to-end analysis requests.
- **Endpoints**:
  - `POST /analysis/run`: Accepts `FullAnalysisRequest` and returns `FullAnalysisResponse`.

---

### `backend/app/api/routes/planning.py`
- **Responsibility**: Dedicated path-planning endpoint.
- **Endpoints**:
  - `POST /planning/find-path`: Accepts start/goal coordinates and cost grid; returns A* path results.

---

# 2. Frontend Modules

---

### `frontend/src/App.tsx`
- **Responsibility**: Top-level mission-control layout, active session state coordinator, and event dispatcher.
- **Why it exists**: Serves as the central mission control dashboard bringing together the telemetry bar, exploration viewport, analytics panel, diagnostics drawer, and methodology modals.
- **Key State Variables**:
  - `currentImage`: Metadata of active image.
  - `analysis`: Complete `FullAnalysisResponse` payload.
  - `startCoord` & `goalCoord`: Grid tuples `[row, col]`.
  - `allowDiagonal`: Boolean governing 4-way vs 8-way movement.
  - `isUploadOpen` & `isMethodologyOpen`: Modal state controls.

---

### `frontend/src/components/MissionStatusBar.tsx`
- **Responsibility**: Top-level aerospace mission status HUD.
- **Why it exists**: Visually communicates the active tactical mission, loaded optical payload dimensions, step-by-step pipeline progress (Ingestion $\to$ SAM 3.1 $\to$ Normalization $\to$ Costmap $\to$ A* Path), and quick-action buttons for loading sample frames and uploading new data.

---

### `frontend/src/components/InteractiveMapViewer.tsx`
- **Responsibility**: Large, immersive centerpiece spatial exploration viewport.
- **Why it exists**: Acts as the primary visual display for planetary terrain perception and path decision-support.
- **Key Features**:
  - Zoom & Pan engine (Zoom in, Zoom out, Fit-to-view, Alt+Drag / Middle-click panning).
  - Layer switches: Optical Rover Frame, Terrain Risk Costmap, A* Route Waypoints, Spatial Grid Lines.
  - Continuous overlay opacity adjustment slider (10% to 100%).
  - Click-to-place coordinate selection: switches between Rover Origin (S) and Target Destination (G).
  - Floating HUD tooltip with smart positioning: inspects row, column, terrain classification, numerical traversal cost, and traversability status without obstructing content.
  - Comprehensive color-coded terrain risk legend.

---

### `frontend/src/components/AnalysisPanel.tsx`
- **Responsibility**: Integrated path planning controls and empirical terrain distribution analytics.
- **Why it exists**: Combines algorithmic route computation controls with actual response data visualizations.
- **Key Features**:
  - Dynamic route metrics HUD: Cumulative Weighted Cost, Geometric Travel Distance, Expanded Graph Nodes, and Solution Status.
  - 4-way (Manhattan) vs 8-way (Octile) diagonal movement selector with corner-cutting prevention.
  - Immediate route recalculation action.
  - Mathematical explanation distinguishing weighted traversal impedance from geometric distance.
  - Empirical terrain distribution bar and percentage breakdown derived from actual grid cells.
  - Overall traversability ratio badge.

---

### `frontend/src/components/DiagnosticsDrawer.tsx`
- **Responsibility**: Collapsible deep technical telemetry and execution trace drawer.
- **Why it exists**: Allows engineers and reviewers to inspect underlying model outputs, mask bounding boxes, pixel areas, and backend execution logs without cluttering the primary viewport.
- **Key Features**:
  - Decoded mask instances table (ID, concept, bounding box coordinates, pixel area).
  - Chronological pipeline execution logs with HTTP status codes.
  - Explicit scientific honesty notice regarding monocular 2D imagery limitations.

---

### `frontend/src/components/Navbar.tsx`
- **Responsibility**: Top aerospace mission-control header bar. Displays RoverMind orbital branding, live API status badge (`ONLINE` / `OFFLINE`), SAM 3.1 integration indicator (`LIVE` / `DEMO FIXTURE`), quick frame actions, and methodology modal trigger.

---

### `frontend/src/components/ImageUploadPanel.tsx`
- **Responsibility**: Optical payload ingestion dialog. Supports drag-and-drop file upload, file picker, two-pass Pillow validation feedback, file size/dimension limits, and quick-loading of the authentic repository sample frame (`rover_image.png`).

---

### `frontend/src/components/MethodologyModal.tsx`
- **Responsibility**: Comprehensive methodology and architecture reference modal explaining SAM 3.1 token parsing, cost model math, custom A* algorithm properties, and scientific limitations.

---

### `frontend/src/components/SpacecraftCursor.tsx`
- **Responsibility**: Animated Mars orbital scout craft following the user's cursor.
- **Implementation Highlights**:
  - Linear interpolation (`LERP_FACTOR = 0.085`) via `requestAnimationFrame`.
  - Dynamic heading angle orientation calculated via `Math.atan2(dy, dx)`.
  - Pulsing ion propulsion thruster flame.
  - Direct DOM mutation via `ref` to avoid triggering React re-renders.
  - `pointer-events: none` on the container layer to prevent click obstruction.
  - Automatically disabled on touch screens (`pointer: coarse`) and under `prefers-reduced-motion`.

---

### `frontend/src/services/api.ts`
- **Responsibility**: Centralized, typed HTTP client communicating with backend endpoints.

---

### `frontend/src/types/api.ts`
- **Responsibility**: TypeScript interfaces mirroring backend Pydantic models.

---

# 3. Configuration & Environment Files

- **`.env.example`**: Documents `META_API_KEY=` without hardcoded secrets.
- **`requirements.txt`**: Python dependencies including `fastapi`, `uvicorn`, `meta-sam-parser==0.1.0`, `openai`, `pillow`, `pytest`, `httpx`, and `python-multipart`.
- **`.gitignore`**: Ignores `.env`, virtual environments (`.venv`), Python cache (`__pycache__`), and frontend build artifacts (`node_modules/`, `dist/`).

---

# 4. Test Suite Modules

- **`backend/tests/test_health.py`**: Health check reachable (200 OK), payload structure, and credential leakage protection.
- **`backend/tests/test_path_planner.py`**: 25 tests covering A* optimality, diagonal corner-cutting prevention, start-equals-goal, impassable barriers, octile/Manhattan heuristics, and ragged input validation.
- **`backend/tests/test_terrain_costmap.py`**: 16 tests covering label-to-cost conversion, impassable `None` preservation, defensive copying, and input validation.
- **`backend/tests/test_segmentation_contract.py`**: 13 tests verifying `SegmentationResult` initialization, dimension constraints, string label validation, and defensive copying.
- **`backend/tests/test_segmentation_adapter.py`**: 19 tests verifying region ID translation, unmapped ID rejection, non-negative integer enforcement, and non-mutation of inputs.
- **`backend/tests/test_sam_integration_helpers.py`**: 10 tests verifying image MIME detection, non-binary raster rejection, and response text extraction.
- **`backend/tests/test_terrain_interpreter.py`**: 5 tests verifying concept-to-terrain translation, hazard priority hierarchy, and default cost maps.
- **`backend/tests/test_mask_reconstruction.py`**: 3 tests verifying mask grid reconstruction, spatial projection, and priority conflict resolution.
- **`backend/tests/test_image_service.py`**: 4 tests verifying PNG/JPEG validation, corrupt data rejection, and memory store operations.
- **`backend/tests/test_security_audit.py`**: 9 tests verifying CORS header restrictions, configurable production origins, image store dual-bounded LRU eviction (25 entries & 100MB RAM budget), decompression bomb protection (25MP ceiling), path traversal sanitization, mask dimension ceilings, HTTP security headers, scanline-level truncated image rejection, and sanitized HTTP 500 error messages.
- **`backend/tests/test_api_routes.py`**: 5 tests verifying `/health`, `/config`, `/images/load-sample`, `/analysis/run`, `/planning/find-path`, and `/` frontend serving.
