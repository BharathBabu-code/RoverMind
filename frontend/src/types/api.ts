export interface HealthResponse {
  status: string;
  service: string;
  version: string;
}

export interface ConfigStatusResponse {
  is_meta_api_configured: boolean;
  meta_model: string;
  is_reasoning_api_configured?: boolean;
  reasoning_model?: string;
  offline_mode: boolean;
  message: string;
  external_api_enabled?: boolean;
  external_api_dry_run?: boolean;
  reasoning_provider?: string;
  muse_spark_model?: string;
  llama_model?: string;
  provider_provenance?: string;
  sam_status?: string;
  sam_last_verified?: string | null;
  reasoning_status?: string;
  reasoning_last_verified?: string | null;
  active_segmentation_source?: string;
  active_reasoning_source?: string;
  ledger?: Record<string, any>;
}

export interface ImageMetadata {
  image_id: string;
  filename: string;
  width: number;
  height: number;
  mime_type: string;
  file_size_bytes: number;
}

export interface ImageUploadResponse {
  success: boolean;
  metadata: ImageMetadata;
  message: string;
}

export interface GalleryItem {
  id: string;
  title: string;
  rover: string;
  camera: string;
  sol: number;
  site: string;
  description: string;
  filename: string;
  width: number;
  height: number;
  file_size_bytes: number;
  preview_url: string;
}

export interface MaskRecordDto {
  object_id: string;
  concept: string;
  bounds?: {
    left: number;
    top: number;
    right: number;
    bottom: number;
  };
  area_pixels: number;
  confidence?: number;
}

export interface SegmentationResponse {
  image_id: string;
  grid_width: number;
  grid_height: number;
  terrain_grid: string[][];
  masks: MaskRecordDto[];
  source_model: string;
  is_synthetic: boolean;
  diagnostics: string[];
}

export interface CostmapResponse {
  image_id: string;
  grid_width: number;
  grid_height: number;
  cost_grid: (number | null)[][];
  terrain_costs: Record<string, number | null>;
}

export interface PathPlanResponse {
  is_success: boolean;
  path: [number, number][];
  total_weighted_cost: number;
  geometric_length: number;
  expanded_nodes: number;
  error_message?: string;
}

export interface RouteCostBreakdownDto {
  clear_cells_count: number;
  rocky_cells_count: number;
  loose_cells_count: number;
  unknown_cells_count: number;
  obstacle_cells_count: number;
  cardinal_steps_count: number;
  diagonal_steps_count: number;
  cost_contributions: Record<string, number>;
  total_calculated_cost: number;
  reconciled: boolean;
  unknown_percentage: number;
  unknown_warning: boolean;
}

export interface RecomputePathRequest {
  image_id: string;
  terrain_costs?: Record<string, number | null>;
  start?: [number, number];
  goal?: [number, number];
  allow_diagonal?: boolean;
}

export interface RecomputePathResponse {
  image_id: string;
  costmap: CostmapResponse;
  path_result: PathPlanResponse;
  breakdown: RouteCostBreakdownDto;
}

export interface FullAnalysisResponse {
  image_id: string;
  metadata: ImageMetadata;
  segmentation: SegmentationResponse;
  costmap: CostmapResponse;
  path_result?: PathPlanResponse;
  breakdown?: RouteCostBreakdownDto;
  diagnostics: string[];
}

export interface MissionBriefing {
  mission_id: string;
  image_id: string;
  generated_at: string;
  source_model: string;
  is_ai_generated: boolean;
  observation_overview: {
    detected_concepts?: string[];
    terrain_classes_count?: number;
    dominant_terrain?: string;
    terrain_breakdown?: Record<string, string>;
    spatial_highlights?: string[];
  };
  navigation_assessment: {
    path_feasibility?: string;
    waypoints_count?: number;
    total_weighted_cost?: number;
    geometric_length_units?: number;
    search_complexity_nodes?: number;
    obstacle_avoidance?: string;
    influencing_factors?: string;
  };
  risk_and_uncertainty: {
    elevated_cost_regions?: string[];
    unknown_unmapped_regions?: string;
    monocular_limitations?: string[];
    recommended_operator_actions?: string[];
  };
  mission_takeaways: string[];
}

export interface ToolExecutionLog {
  tool_name: string;
  arguments: Record<string, any>;
  result: any;
}

export interface ChatMessage {
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp?: string;
  tool_calls?: ToolExecutionLog[];
}

export interface ChatResponse {
  image_id: string;
  conversation_id: string;
  reply: string;
  source_model: string;
  is_ai_generated: boolean;
  tool_calls_executed: ToolExecutionLog[];
}

export interface RouteComparisonResponse {
  image_id: string;
  original_cost: number;
  original_length: number;
  original_waypoints_count: number;
  alternative_cost: number;
  alternative_length: number;
  alternative_waypoints_count: number;
  cost_delta: number;
  length_delta: number;
  comparison_summary: string;
  alternative_path: [number, number][];
}

