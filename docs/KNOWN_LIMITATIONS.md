# RoverMind — Known Limitations & Operational Boundaries

This document records the engineering boundaries, physical limitations, and operational assumptions of RoverMind.

---

## 1. Scientific & Physical Limitations

### 1.1 Monocular Imagery Constraints
A single 2D optical frame (RGB or grayscale) does not provide metric 3D depth. Monocular images exhibit perspective distortion and scale ambiguity: distant large boulders can occupy the same pixel area as nearby pebbles.

### 1.2 Lack of Digital Elevation & Slope Models
Traversability on planetary surfaces is heavily dictated by slope angle and tilt. Rover chassis and suspension systems (such as the rocker-bogie mechanism on Mars rovers) have strict tip-over and high-centering thresholds (typically 15°–30° slope limits). RoverMind does not compute physical slope or elevation from stereo disparity.

### 1.3 Subsurface & Soil Mechanics
A visual camera cannot evaluate geotechnical bearing capacity, shear strength, or wheel sinkage risk. A region visually segmented as "soil" may conceal loose drift sand capable of trapping a rover (as occurred with NASA's Spirit rover in 2009 at Troy).

### 1.4 Decision Support vs. Flight Locomotion
RoverMind is an interactive **computational decision-support system**. Outputs must never be used as flight-certified autonomous drive commands.

---

## 2. Model & Segmentation Limitations

### 2.1 Meta SAM 3.1 Characteristics
Meta SAM 3.1 is a visual concept segmenter trained on general-domain visual concepts. It does not possess intrinsic Martian geological taxonomy. Semantic labels (e.g. `rock`, `sand`) are visual prompt concepts, not verified geological classifications.

### 2.2 Streaming Token Grammar & Parser Dependency
The integration relies on `meta-sam-parser` to parse tokenized text responses into rasters. If upstream API formats change or token grammars evolve, the parser must be updated accordingly.

### 2.3 Live Integration Status
Because `META_API_KEY` is intentionally empty in local configuration, live API execution against Meta's cloud infrastructure remains **UNVERIFIED AGAINST LIVE NETWORK**. The system gracefully executes with labelled offline synthetic fixtures.

---

## 3. Discretization & Spatial Alignment Assumptions

### 3.1 Grid Discretization
To maintain interactive pathfinding and visualization performance, the full-resolution image ($1648 \times 1200$) is downsampled onto a discrete grid (e.g. $50 \times 68$ cells). Fine visual details smaller than a single grid cell ($24 \times 24$ pixels) are averaged into the cell's dominant or prioritized terrain class.

### 3.2 Overlap Arbitration
When multiple concept masks overlap on the same grid cell, arbitration uses a deterministic priority hierarchy (`obstacle` $>$ `rocky` $>$ `loose` $>$ `unknown` $>$ `clear`). While this favors safety, it may cause a small obstacle to block an entire cell.

---

## 4. Software & Deployment Boundaries

### 4.1 In-Memory Session Storage
Images and analysis sessions are stored in backend memory (`_IMAGE_STORE`) bounded to a maximum capacity of 25 active session frames with thread-safe LRU eviction to prevent unbounded memory growth. A server restart clears active sessions. For multi-user cloud deployments, an external object store (e.g. S3 / GCS) and database would be required. Uploads are strictly capped at 20MB file size, 8192px maximum dimensions, and 25 Megapixels decompression ceiling to prevent decompression bomb Denial-of-Service attacks.

### 4.2 Single Instance Concurrency
The custom A* planner executes synchronously on the backend. For very large grids ($>500 \times 500$), pathfinding runs in linear memory and could benefit from background task queues (e.g. Celery or ARQ) if deployed in high-concurrency environments.

---

## 5. Reasoning Model & Mission Assistant Boundaries

### 5.1 Maximum Tool-Calling Loop Horizon
The contextual mission chatbot implements an explicit limit of **4 tool-calling iterations** per turn. This deterministic bounding prevents runaway execution loops or unbounded API latency when the model requests iterative simulated adjustments or diagnostic queries.

### 5.2 Conversation History Horizon & Storage Volatility
Conversation histories are tracked in-memory within `_CONVERSATION_STORE` and bounded to a maximum of **20 messages per mission session** (with eviction of older turns) across up to **25 concurrent active mission sessions**. Conversation state is volatile and resets upon server restart. For persistent mission logs, an external database (e.g. PostgreSQL) would be required.

### 5.3 Ground-Truth Enforcement & Absence of Hallucinated Geometry
The reasoning model operates strictly on structured mission context (`MissionContextDto`) provided by the deterministic segmentation and pathfinding engines. The LLM is technically constrained by system prompt contracts and JSON schemas from fabricating terrain classifications, coordinates, traversal costs, or route metrics; all quantitative statistics derive from verified Python calculations.

### 5.4 Live API Credential Dependency
Live reasoning intelligence relies on `META_REASONING_API_KEY` (targeting Meta's `llama-3.3-70b-instruct` or compatible OpenAI endpoints). When credentials are not provisioned or network timeouts occur, the platform automatically falls back to an offline deterministic briefing engine and rule-based query interpreter, maintaining 100% operational availability without external network calls.
