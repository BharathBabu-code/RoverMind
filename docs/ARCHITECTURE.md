# RoverMind — System Architecture

This document describes the software architecture, modular relationships, external integrations, and data flows of the **RoverMind** application.

---

## 1. High-Level System Architecture

RoverMind is divided into two decoupled subsystems:

1. **FastAPI Backend Services**: Responsible for image integrity validation, model orchestration, mask parsing and decoding, terrain normalization, costmap compilation, and authoritative A* route finding.
2. **React + TypeScript Mission Control Frontend**: Responsible for image ingestion, user coordinate interactions, spatial layer visualization (raw image, mask overlay, costmap grid, and path overlay), and telemetry diagnostics.

```mermaid
graph TD
    User["Mission Operator / Browser"] -->|HTTP / REST| API["FastAPI Application (Port 8000)"]
    subgraph Frontend ["Mission Control Frontend (React + TypeScript)"]
        UI["Mission Control HUD"]
        Canvas["Interactive Map Viewer"]
        Narrative["Planetary Narrative Journey"]
        BriefingPanel["Mission Intelligence Panel"]
        ChatbotDock["Contextual Mission Chatbot"]
        Follower["Spacecraft Cursor Layer"]
        APIClient["Typed API Client"]
        UI --> Canvas
        UI --> BriefingPanel
        UI --> ChatbotDock
        UI --> APIClient
    end

    subgraph Backend ["RoverMind Backend (Python 3.12)"]
        Router["API Routers (/health, /images, /analysis, /planning, /mission)"]
        Orchestrator["Analysis Orchestrator"]
        ImgService["Image Validation & Memory Store"]
        SAMService["SAM 3.1 Client & Parser"]
        Reconstruct["Mask Reconstruction Engine"]
        Interpreter["Terrain Interpreter"]
        Contract["Segmentation Adapter & Contract"]
        Costmap["Terrain Costmap Service"]
        Planner["Custom A* Path Planner"]
        Context["Mission Context Registry"]
        Reasoning["Reasoning Service"]
        Tools["Mission Tools (Read-Only & Sim)"]

        Router --> Orchestrator
        Router --> ImgService
        Router --> Planner
        Router --> Reasoning
        Orchestrator --> ImgService
        Orchestrator --> SAMService
        SAMService --> Reconstruct
        Reconstruct --> Interpreter
        Interpreter --> Contract
        Contract --> Costmap
        Costmap --> Planner
        Orchestrator --> Context
        Reasoning --> Context
        Reasoning --> Tools
        Tools --> Planner
        Tools --> Costmap
    end

    subgraph External ["External AI / Model Endpoints"]
        MetaSAM["Meta SAM 3.1 (api.meta.ai/v1)"]
        MetaLlama["Meta Reasoning / Llama (api.meta.ai/v1)"]
    end

    APIClient <--> Router
    SAMService -.->|TLS / Bearer Auth| MetaSAM
    Reasoning -.->|TLS / Tool Calling| MetaLlama
```

---

## 2. End-to-End Processing Pipeline

The execution flow begins with an uploaded optical image and terminates with an interactive route overlay on the user's display:

```mermaid
flowchart TD
    A["Raw Mars Image (PNG/JPEG)"] --> B["Image Validation (Pillow Detector)"]
    B --> C["In-Memory Image Store (UUID Registry)"]
    C --> D{"Is META_API_KEY Configured?"}
    
    D -- Yes --> E["Meta SAM 3.1 API (Concept Queries)"]
    D -- No --> F["Labelled Offline Synthetic Fixture"]
    
    E --> G["meta-sam-parser (Token Push & Extraction)"]
    G --> H["Mask Raster Decoding (decode_mask_to_raster)"]
    H --> I["Spatial Grid Alignment & Bounding Box Projection"]
    F --> I
    
    I --> J["Terrain Interpretation (Concept -> Class Mapping)"]
    J --> K["Hazard Priority Conflict Resolution"]
    K --> L["Segmentation Contract (SegmentationResult)"]
    L --> M["Terrain Costmap Compiler (build_cost_map)"]
    M --> N["Cost Grid (Floats & Blocked Cells)"]
    N --> O["Custom A* Algorithm (find_path)"]
    O --> P["Computed Lowest-Cost Path & Metrics"]
    P --> Q["Interactive Mission Control Visualizer"]
```

---

## 3. Meta SAM 3.1 Integration Architecture

Visual segmentation uses Meta AI's promptable SAM 3.1 model. SAM streaming outputs return custom tokenized grammar rather than raw raster PNGs. RoverMind parses this data using `meta-sam-parser`:

```mermaid
sequenceDiagram
    autonumber
    actor Backend as Analysis Orchestrator
    participant Client as OpenAI SDK Client
    participant Meta as Meta SAM 3.1 API
    participant Parser as meta-sam-parser
    participant Recon as Mask Reconstruction

    Backend->>Client: Send image Data URL + prompt ('rock')
    Client->>Meta: POST /responses.create (model: sam-3.1)
    Meta-->>Client: Streaming tokenized grammar response
    Client-->>Backend: Raw response text payload
    Backend->>Parser: push(response_text) & finish()
    Parser-->>Backend: SegmentationResult with SegmentationMaskRecords
    loop For each mask record
        Backend->>Parser: decode_mask_to_raster(record.mask)
        Parser-->>Backend: 1-byte-per-pixel flat raster bytes
        Backend->>Recon: Align raster using record.bounds
        Recon-->>Backend: DecodedMask in image coordinate space
    end
```

---

## 4. Terrain Normalization & Costmap Compilation

Visual concepts are distinct from operational terrain traversal parameters. The translation occurs through an explicit multi-stage normalization contract:

```mermaid
flowchart LR
    subgraph Concepts ["Visual Concept Segmentation"]
        C1["rock"]
        C2["boulder"]
        C3["loose sand"]
        C4["crater"]
        C5["bedrock"]
    end

    subgraph Interpreter ["Terrain Interpreter"]
        M1["rocky (Priority: 70)"]
        M2["loose (Priority: 50)"]
        M3["obstacle (Priority: 100)"]
        M4["clear (Priority: 10)"]
    end

    subgraph Contract ["Segmentation Contract"]
        SR["SegmentationResult (2D Grid of Strings)"]
    end

    subgraph Costmap ["Costmap Service"]
        CG["Numeric Cost Grid (Float | None)"]
    end

    C1 --> M1
    C2 --> M1
    C3 --> M2
    C4 --> M3
    C5 --> M4

    M1 & M2 & M3 & M4 --> SR
    SR --> CG
```

---

## 5. Custom A* Route-Planning Flow

The path-planning engine is strictly authoritative on the backend. The search algorithm explores the cost grid while enforcing corner-cutting constraints:

```mermaid
flowchart TD
    StartNode["Start Coordinate (r, c)"] --> OpenSet["Open Set Priority Queue (Min-Heap)"]
    OpenSet --> Pop["Pop Node with Min f = g + h"]
    Pop --> CheckGoal{"Is Node == Goal?"}
    
    CheckGoal -- Yes --> ReconstructPath["Trace Back Parents & Return PathResult"]
    CheckGoal -- No --> GenNeighbors["Generate Neighbors (Cardinals & Diagonals)"]
    
    GenNeighbors --> BoundsCheck{"Within Grid Bounds?"}
    BoundsCheck -- No --> Skip["Discard"]
    BoundsCheck -- Yes --> ImpassableCheck{"Is Cell Traversable?"}
    
    ImpassableCheck -- No --> Skip
    ImpassableCheck -- Yes --> DiagCheck{"Is Diagonal Movement?"}
    
    DiagCheck -- Yes --> CornerCut{"Are Adjacent Cardinals Traversable?"}
    CornerCut -- No (Corner Cut) --> Skip
    CornerCut -- Yes --> CalcCost["Compute g = current_g + (dist * cell_cost)"]
    DiagCheck -- No --> CalcCost
    
    CalcCost --> BetterG{"tentative_g < g_score?"}
    BetterG -- Yes --> Update["Update g_score, came_from, Push to Heap"]
    BetterG -- No --> Skip
    
    Update --> OpenSet
```

---

## 6. Frontend / Backend Communication

The browser interface communicates with the FastAPI backend through a typed API client:

```mermaid
sequenceDiagram
    autonumber
    actor Operator as Mission Operator
    participant UI as React Mission Control
    participant API as FastAPI Backend

    Operator->>UI: Selects or drops rover camera frame
    UI->>API: POST /images/upload (multipart/form-data)
    API-->>UI: ImageUploadResponse { image_id, width, height }
    
    UI->>API: POST /analysis/run { image_id, downsample: 24 }
    API-->>UI: FullAnalysisResponse { terrain_grid, cost_grid, default_path }
    UI->>Operator: Renders Image + Costmap + Initial Path

    Operator->>UI: Clicks grid cell to relocate Destination
    UI->>API: POST /planning/find-path { cost_grid, start, new_goal }
    API-->>UI: PathPlanResponse { is_success, path, total_weighted_cost }
    UI->>Operator: Updates route overlay and telemetry metrics
```
