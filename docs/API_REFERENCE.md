# RoverMind — API Reference

The RoverMind REST API is exposed by FastAPI at `http://127.0.0.1:8000`. 
Interactive Swagger / OpenAPI documentation is automatically served at `/docs`, and ReDoc documentation at `/redoc`.

All endpoints are available both at the root path (`/endpoint`) and under the `/api` prefix (`/api/endpoint`).

---

## 1. System Health & Configuration

### `GET /health`
Verifies backend server liveness without reading external services or disclosing internal configuration.

- **Status Code**: `200 OK`
- **Response Schema** (`HealthResponse`):
  ```json
  {
    "status": "ok",
    "service": "RoverMind API",
    "version": "0.1.0"
  }
  ```

---

### `GET /config`
Reports the active AI model integration status and whether credentials are configured.

- **Status Code**: `200 OK`
- **Response Schema** (`ConfigStatusResponse`):
  ```json
  {
    "is_meta_api_configured": false,
    "meta_model": "sam-3.1",
    "offline_mode": true,
    "message": "META_API_KEY is not configured in .env. Operating in offline/demonstration mode with synthetic test data."
  }
  ```

---

## 2. Optical Imagery Operations

### `POST /images/upload`
Uploads and validates a Mars rover camera frame.

- **Content-Type**: `multipart/form-data`
- **Form Parameters**:
  - `file`: Binary file upload (JPEG or PNG, max 20MB, max 8192×8192 px).
- **Status Codes**:
  - `200 OK`: Successful validation and registration.
  - `400 Bad Request`: Empty payload, corrupt image, unsupported format, or dimension limits exceeded.
- **Example Response**:
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

### `POST /images/load-sample`
Immediately ingests and registers the authentic local sample image (`rover_image.png`, 1648×1200 px) from the repository root.

- **Status Codes**:
  - `200 OK`: Sample image loaded successfully.
  - `404 Not Found`: Sample image missing from disk.
- **Example Response**: Same structure as `POST /images/upload`.

---

### `GET /images/{image_id}/metadata`
Retrieves image dimensions, format, and size for an active in-memory session.

- **Path Parameters**:
  - `image_id`: String UUID of the image.
- **Status Codes**:
  - `200 OK`: Image found.
  - `404 Not Found`: Image ID not recognized.
- **Example Response**:
  ```json
  {
    "image_id": "8d3e9f4a-71b2-482a-bc93-5e7e6a1d48c0",
    "filename": "rover_image.png",
    "width": 1648,
    "height": 1200,
    "mime_type": "image/png",
    "file_size_bytes": 4454540
  }
  ```

---

### `GET /images/{image_id}/raw`
Streams raw binary image bytes for direct browser `<img>` rendering.

- **Path Parameters**:
  - `image_id`: String UUID of the image.
- **Status Codes**:
  - `200 OK`: Binary image data streamed with appropriate `Content-Type: image/png` or `image/jpeg`.
  - `404 Not Found`: Image ID not recognized.

---

## 3. Analysis Orchestration

### `POST /analysis/run`
Executes end-to-end visual segmentation, terrain-risk costmap generation, and optional default path planning.

- **Request Body** (`FullAnalysisRequest`):
  ```json
  {
    "image_id": "8d3e9f4a-71b2-482a-bc93-5e7e6a1d48c0",
    "concepts": ["rock", "sand", "obstacle"],
    "grid_downsample_factor": 24,
    "terrain_costs": {
      "clear": 1.0,
      "rocky": 3.0,
      "loose": 5.0,
      "unknown": 2.0,
      "obstacle": null
    },
    "start": [49, 34],
    "goal": [0, 34],
    "allow_diagonal": true
  }
  ```
- **Status Codes**:
  - `200 OK`: Analysis successfully executed.
  - `400 Bad Request`: Invalid grid downsample factor or malformed parameters.
  - `404 Not Found`: Image ID not found.
- **Example Response** (`FullAnalysisResponse`):
  ```json
  {
    "image_id": "8d3e9f4a-71b2-482a-bc93-5e7e6a1d48c0",
    "metadata": {
      "image_id": "8d3e9f4a-71b2-482a-bc93-5e7e6a1d48c0",
      "filename": "rover_image.png",
      "width": 1648,
      "height": 1200,
      "mime_type": "image/png",
      "file_size_bytes": 4454540
    },
    "segmentation": {
      "image_id": "8d3e9f4a-71b2-482a-bc93-5e7e6a1d48c0",
      "grid_width": 68,
      "grid_height": 50,
      "terrain_grid": [
        ["clear", "clear", "rocky", "..."]
      ],
      "masks": [
        {
          "object_id": "synthetic_rock_outcrop",
          "concept": "rock",
          "bounds": { "left": 906, "top": 300, "right": 1400, "bottom": 720 },
          "area_pixels": 158208,
          "confidence": null
        }
      ],
      "source_model": "sam-3.1-offline-synthetic",
      "is_synthetic": true,
      "diagnostics": [
        "SYNTHETIC DEMO DATA: META_API_KEY is not configured or offline mode was requested."
      ]
    },
    "costmap": {
      "image_id": "8d3e9f4a-71b2-482a-bc93-5e7e6a1d48c0",
      "grid_width": 68,
      "grid_height": 50,
      "cost_grid": [
        [1.0, 1.0, 3.0, null]
      ],
      "terrain_costs": {
        "clear": 1.0,
        "rocky": 3.0,
        "loose": 5.0,
        "unknown": 2.0,
        "obstacle": null
      }
    },
    "path_result": {
      "is_success": true,
      "path": [[49, 34], [48, 35], [47, 35]],
      "total_weighted_cost": 54.28,
      "geometric_length": 52.83,
      "expanded_nodes": 184,
      "error_message": null
    },
    "diagnostics": []
  }
  ```

---

## 4. Path Planning Operations

### `POST /planning/find-path`
Calculates an optimal A* path between two grid coordinates across a provided cost grid.

- **Request Body** (`PathPlanRequest`):
  ```json
  {
    "cost_grid": [
      [1.0, 1.0, 1.0],
      [null, null, 1.0],
      [1.0, 1.0, 1.0]
    ],
    "start": [0, 0],
    "goal": [2, 0],
    "allow_diagonal": false
  }
  ```
- **Status Codes**:
  - `200 OK`: Path calculation completed.
  - `400 Bad Request`: Coordinates out of bounds, start/goal in blocked cell, ragged grid, or invalid costs.
- **Example Response** (`PathPlanResponse`):
  ```json
  {
    "is_success": true,
    "path": [
      [0, 0],
      [0, 1],
      [0, 2],
      [1, 2],
      [2, 2],
      [2, 1],
      [2, 0]
    ],
    "total_weighted_cost": 6.0,
    "geometric_length": 6.0,
    "expanded_nodes": 7,
---

## 5. Mission Intelligence & Reasoning Operations

### `GET /mission/capabilities`
Returns operational statuses for both AI models (SAM 3.1 perception and Meta Reasoning), along with the list of exposed backend tools.

- **Status Code**: `200 OK`
- **Example Response**:
  ```json
  {
    "visual_segmentation": {
      "model": "sam-3.1",
      "is_configured": false,
      "mode": "offline-synthetic"
    },
    "mission_reasoning": {
      "model": "llama-3.3-70b-instruct",
      "is_configured": false,
      "mode": "deterministic-rule-engine"
    },
    "available_tools": [
      "get_mission_summary",
      "get_terrain_distribution",
      "get_region_details",
      "get_route_metrics",
      "compare_routes",
      "get_analysis_diagnostics"
    ]
  }
  ```

---

### `GET /mission/{image_id}/context`
Returns the compact, bounded structured mission context extracted from the active image analysis.

- **Status Codes**: `200 OK`, `404 Not Found`
- **Example Response** (`MissionContextDto`):
  ```json
  {
    "mission_id": "mission_8d3e9f4a",
    "image_id": "8d3e9f4a-71b2-482a-bc93-5e7e6a1d48c0",
    "image_filename": "rover_image.png",
    "image_dimensions": [1648, 1200],
    "grid_dimensions": [103, 75],
    "is_synthetic": true,
    "source_model": "sam-3.1-offline-synthetic",
    "detection_concepts": ["rock", "sand", "obstacle"],
    "terrain_distribution": {
      "clear": 5420,
      "loose": 1280,
      "rocky": 850,
      "obstacle": 175
    },
    "terrain_percentages": {
      "clear": 70.16,
      "loose": 16.57,
      "rocky": 11.00,
      "obstacle": 2.27
    },
    "total_cells": 7725,
    "unknown_cells": 0,
    "unknown_percentage": 0.0,
    "route_found": true,
    "waypoints_count": 75,
    "total_weighted_cost": 74.0,
    "geometric_length": 74.0,
    "expanded_nodes": 74,
    "masks_count": 3
  }
  ```

---

### `GET /mission/{image_id}/briefing`
Returns the structured 4-part observation briefing for an active mission. Uses the Meta reasoning model when configured; falls back deterministically to rule-based generation.

- **Query Parameters**:
  - `force_deterministic`: Optional boolean (default `false`)
- **Status Codes**: `200 OK`, `404 Not Found`
- **Example Response** (`MissionBriefing`):
  ```json
  {
    "mission_id": "mission_8d3e9f4a",
    "image_id": "8d3e9f4a-71b2-482a-bc93-5e7e6a1d48c0",
    "generated_at": "2026-11-04T15:00:00Z",
    "source_model": "llama-3.3-70b-instruct",
    "is_ai_generated": true,
    "observation_overview": {
      "dominant_terrain": "clear",
      "detected_concepts": ["rock", "sand", "obstacle"]
    },
    "navigation_assessment": {
      "path_feasibility": "FEASIBLE",
      "waypoints_count": 75,
      "total_weighted_cost": 74.0
    },
    "risk_and_uncertainty": {
      "elevated_cost_regions": ["Loose sand: 1280 cells", "Rocky terrain: 850 cells"],
      "monocular_limitations": ["Scale ambiguity", "Lack of 3D slope"]
    },
    "mission_takeaways": [
      "Optimal lowest-cost trajectory computed across bedrock corridor.",
      "Computational decision support only."
    ]
  }
  ```

---

### `POST /mission/chat`
Submits an operator query to the mission assistant. The assistant executes controlled backend tools scoped to `image_id` before formulating its response.

- **Request Body** (`ChatRequest`):
  ```json
  {
    "image_id": "8d3e9f4a-71b2-482a-bc93-5e7e6a1d48c0",
    "message": "Why did RoverMind select this route instead of going straight?",
    "conversation_id": null
  }
  ```
- **Status Codes**: `200 OK`, `400 Bad Request`, `404 Not Found`
- **Example Response** (`ChatResponse`):
  ```json
  {
    "image_id": "8d3e9f4a-71b2-482a-bc93-5e7e6a1d48c0",
    "conversation_id": "7b1f3c2a-9941-4cde-a110-388274d81736",
    "reply": "A direct straight-line route intersects 175 mapped obstacle cells. The selected route avoids obstacles by navigating through lower-cost bedrock.",
    "source_model": "llama-3.3-70b-instruct",
    "is_ai_generated": true,
    "tool_calls_executed": [
      {
        "tool_name": "get_route_metrics",
        "arguments": {"image_id": "8d3e9f4a-71b2-482a-bc93-5e7e6a1d48c0"},
        "result": {"is_success": true, "waypoints_count": 75}
      }
    ]
  }
  ```

---

### `POST /mission/compare-routes`
Non-destructively recalculates path metrics using alternative terrain traversal costs.

- **Request Body** (`RouteComparisonRequest`):
  ```json
  {
    "image_id": "8d3e9f4a-71b2-482a-bc93-5e7e6a1d48c0",
    "alternative_terrain_costs": {
      "rocky": 15.0,
      "loose": 8.0
    },
    "allow_diagonal": true
  }
  ```
- **Status Codes**: `200 OK`, `400 Bad Request`, `404 Not Found`
- **Example Response** (`RouteComparisonResponse`):
  ```json
  {
    "image_id": "8d3e9f4a-71b2-482a-bc93-5e7e6a1d48c0",
    "original_cost": 74.0,
    "original_length": 74.0,
    "original_waypoints_count": 75,
    "alternative_cost": 74.0,
    "alternative_length": 74.0,
    "alternative_waypoints_count": 75,
    "cost_delta": 0.0,
    "length_delta": 0.0,
    "comparison_summary": "Alternative weights resulted in identical path impedance and geometry.",
    "alternative_path": [[74, 51], [73, 51]]
  }
  ```

