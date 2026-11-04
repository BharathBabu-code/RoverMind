from typing import List, Tuple, Optional, Dict, Any
from pydantic import BaseModel, Field


class HealthResponse(BaseModel):
    status: str = "ok"
    service: str = "RoverMind API"
    version: str = "0.1.0"


class ConfigStatusResponse(BaseModel):
    is_meta_api_configured: bool
    meta_model: str = "sam-3.1"
    is_reasoning_api_configured: bool = False
    reasoning_model: str = "muse-spark-1.3"
    offline_mode: bool
    message: str
    external_api_enabled: bool = False
    external_api_dry_run: bool = True
    reasoning_provider: str = "muse-spark"
    muse_spark_model: str = "muse-spark-1.3"
    llama_model: str = "llama-3.3-70b-instruct"
    provider_provenance: str = "EXTERNAL INFERENCE DISABLED"
    sam_status: str = "not_configured"
    sam_last_verified: Optional[str] = None
    reasoning_status: str = "not_configured"
    reasoning_last_verified: Optional[str] = None
    active_segmentation_source: str = "offline-synthetic-fixture"
    active_reasoning_source: str = "deterministic-rule-engine"
    ledger: Optional[Dict[str, Any]] = None


class ImageMetadata(BaseModel):
    image_id: str
    filename: str
    width: int
    height: int
    mime_type: str
    file_size_bytes: int


class ImageUploadResponse(BaseModel):
    success: bool
    metadata: ImageMetadata
    message: str


class MaskRecordDto(BaseModel):
    object_id: str
    concept: str
    bounds: Optional[Dict[str, float]] = None
    area_pixels: int
    confidence: Optional[float] = None


class SegmentationResponse(BaseModel):
    image_id: str
    grid_width: int
    grid_height: int
    terrain_grid: List[List[str]]
    masks: List[MaskRecordDto]
    source_model: str
    is_synthetic: bool
    diagnostics: List[str] = Field(default_factory=list)


class CostmapResponse(BaseModel):
    image_id: str
    grid_width: int
    grid_height: int
    cost_grid: List[List[Optional[float]]]
    terrain_costs: Dict[str, Optional[float]]


class PathPlanRequest(BaseModel):
    image_id: Optional[str] = None
    cost_grid: Optional[List[List[Optional[float]]]] = None
    start: Tuple[int, int]
    goal: Tuple[int, int]
    allow_diagonal: bool = False


class PathPlanResponse(BaseModel):
    is_success: bool
    path: List[Tuple[int, int]]
    total_weighted_cost: float
    geometric_length: float
    expanded_nodes: int
    error_message: Optional[str] = None


class FullAnalysisRequest(BaseModel):
    image_id: str
    concepts: Optional[List[str]] = Field(default_factory=lambda: ["rock", "sand", "soil"])
    grid_downsample_factor: Optional[int] = Field(default=16, ge=1, le=64)
    terrain_costs: Optional[Dict[str, Optional[float]]] = None
    start: Optional[Tuple[int, int]] = None
    goal: Optional[Tuple[int, int]] = None
    allow_diagonal: bool = False


class RouteCostBreakdownDto(BaseModel):
    clear_cells_count: int
    rocky_cells_count: int
    loose_cells_count: int
    unknown_cells_count: int
    obstacle_cells_count: int = 0
    cardinal_steps_count: int
    diagonal_steps_count: int
    cost_contributions: Dict[str, float]
    total_calculated_cost: float
    reconciled: bool
    unknown_percentage: float
    unknown_warning: bool


class RecomputePathRequest(BaseModel):
    image_id: str
    terrain_costs: Optional[Dict[str, Optional[float]]] = None
    start: Optional[Tuple[int, int]] = None
    goal: Optional[Tuple[int, int]] = None
    allow_diagonal: bool = True


class RecomputePathResponse(BaseModel):
    image_id: str
    costmap: CostmapResponse
    path_result: PathPlanResponse
    breakdown: RouteCostBreakdownDto


class FullAnalysisResponse(BaseModel):
    image_id: str
    metadata: ImageMetadata
    segmentation: SegmentationResponse
    costmap: CostmapResponse
    path_result: Optional[PathPlanResponse] = None
    breakdown: Optional[RouteCostBreakdownDto] = None
    diagnostics: List[str] = Field(default_factory=list)


# --- Mission Context & Reasoning Layer Schemas ---

class MissionContextDto(BaseModel):
    mission_id: str
    image_id: str
    image_filename: str
    image_dimensions: Tuple[int, int]
    grid_dimensions: Tuple[int, int]
    is_synthetic: bool
    source_model: str
    detection_concepts: List[str]
    terrain_distribution: Dict[str, int]
    terrain_percentages: Dict[str, float]
    total_cells: int
    unknown_cells: int
    unknown_percentage: float
    terrain_costs: Dict[str, Optional[float]]
    start_coord: Optional[Tuple[int, int]] = None
    goal_coord: Optional[Tuple[int, int]] = None
    route_found: bool
    waypoints_count: int
    total_weighted_cost: float
    geometric_length: float
    expanded_nodes: int
    masks_count: int
    diagnostics: List[str] = Field(default_factory=list)
    limitations: List[str] = Field(default_factory=list)


class MissionBriefing(BaseModel):
    mission_id: str
    image_id: str
    generated_at: str
    source_model: str
    is_ai_generated: bool
    observation_overview: Dict[str, Any]
    navigation_assessment: Dict[str, Any]
    risk_and_uncertainty: Dict[str, Any]
    mission_takeaways: List[str]


class ToolExecutionLog(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    result: Any


class ChatMessage(BaseModel):
    role: str
    content: str
    timestamp: Optional[str] = None
    tool_calls: Optional[List[ToolExecutionLog]] = None


class ChatRequest(BaseModel):
    image_id: str
    message: str = Field(..., min_length=1, max_length=2000)
    conversation_id: Optional[str] = None


class ChatResponse(BaseModel):
    image_id: str
    conversation_id: str
    reply: str
    source_model: str
    is_ai_generated: bool
    tool_calls_executed: List[ToolExecutionLog] = Field(default_factory=list)


class RouteComparisonRequest(BaseModel):
    image_id: str
    alternative_terrain_costs: Dict[str, Optional[float]]
    allow_diagonal: Optional[bool] = None
    start: Optional[Tuple[int, int]] = None
    goal: Optional[Tuple[int, int]] = None


class RouteComparisonResponse(BaseModel):
    image_id: str
    original_cost: float
    original_length: float
    original_waypoints_count: int
    alternative_cost: float
    alternative_length: float
    alternative_waypoints_count: int
    cost_delta: float
    length_delta: float
    comparison_summary: str
    alternative_path: List[Tuple[int, int]]

