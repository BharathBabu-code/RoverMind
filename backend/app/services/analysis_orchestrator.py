import math
from typing import Dict, List, Optional, Tuple, Any

from backend.app.core.config import settings
from backend.app.core.sanitizer import sanitize_error
from backend.app.services.image_service import (
    get_image_metadata,
    get_image_data_url
)
from backend.app.services.terrain_costmap import build_cost_map
from backend.app.services.path_planner import find_path, PathResult
from backend.app.services.terrain_interpreter import DEFAULT_TERRAIN_COSTS
from backend.app.services.sam_service import (
    run_live_sam_segmentation,
    generate_synthetic_offline_segmentation
)
from backend.app.services.mission_context import store_analysis
from backend.app.services.route_breakdown import calculate_route_cost_breakdown
from backend.app.schemas.models import (
    FullAnalysisRequest,
    FullAnalysisResponse,
    SegmentationResponse,
    CostmapResponse,
    PathPlanResponse,
    MaskRecordDto
)


def run_full_analysis(request: FullAnalysisRequest) -> FullAnalysisResponse:
    """
    Orchestrates the entire planetary exploration pipeline for an uploaded image:
    Image -> Visual Segmentation -> Normalization -> Costmap -> A* Path Planning
    """
    metadata = get_image_metadata(request.image_id)
    if not metadata:
        raise KeyError(f"Image ID '{request.image_id}' not found. Please upload the image first.")

    # Calculate grid dimensions based on downsample factor
    downsample = request.grid_downsample_factor or 16
    grid_cols = max(4, min(120, metadata.width // downsample))
    grid_rows = max(4, min(120, metadata.height // downsample))

    concepts = request.concepts or ["rock", "sand", "obstacle"]
    terrain_costs = request.terrain_costs or DEFAULT_TERRAIN_COSTS

    # Visual Segmentation step
    diagnostics: List[str] = []
    is_synthetic = False

    # Instantiate per-analysis request budget
    from backend.app.core.budget import RequestBudget
    analysis_budget = RequestBudget(settings.max_sam_requests_per_analysis, operation_name="analysis_pipeline")

    # Determine mode: Offline (kill switch or unconfigured), Dry-Run, or Live
    if not settings.external_api_enabled or not settings.is_meta_api_configured:
        seg_contract_result, masks, synth_diags = generate_synthetic_offline_segmentation(
            image_width=metadata.width,
            image_height=metadata.height,
            grid_rows=grid_rows,
            grid_cols=grid_cols
        )
        diagnostics.extend(synth_diags)
        is_synthetic = True
    elif settings.external_api_dry_run:
        data_url = get_image_data_url(request.image_id)
        seg_contract_result, masks, sam_diags = run_live_sam_segmentation(
            image_data_url=data_url,
            concepts=concepts,
            image_width=metadata.width,
            image_height=metadata.height,
            grid_rows=grid_rows,
            grid_cols=grid_cols,
            budget=analysis_budget
        )
        diagnostics.extend(sam_diags)
        is_synthetic = True
    else:
        # LIVE MODE: Do NOT silently replace real SAM failures with synthetic data.
        data_url = get_image_data_url(request.image_id)
        seg_contract_result, masks, sam_diags = run_live_sam_segmentation(
            image_data_url=data_url,
            concepts=concepts,
            image_width=metadata.width,
            image_height=metadata.height,
            grid_rows=grid_rows,
            grid_cols=grid_cols,
            budget=analysis_budget
        )
        diagnostics.extend(sam_diags)
        is_synthetic = False

    seg_response = SegmentationResponse(
        image_id=request.image_id,
        grid_width=grid_cols,
        grid_height=grid_rows,
        terrain_grid=seg_contract_result.terrain_grid,
        masks=masks,
        source_model=seg_contract_result.source_model,
        is_synthetic=is_synthetic,
        diagnostics=diagnostics
    )

    # Costmap generation step (invoking existing terrain_costmap service)
    cost_grid = build_cost_map(
        terrain_grid=seg_contract_result.terrain_grid,
        terrain_costs=terrain_costs
    )

    costmap_response = CostmapResponse(
        image_id=request.image_id,
        grid_width=grid_cols,
        grid_height=grid_rows,
        cost_grid=cost_grid,
        terrain_costs=terrain_costs
    )

    # Path planning step (optional or default endpoints)
    path_plan_response: Optional[PathPlanResponse] = None

    start = request.start
    goal = request.goal

    # If only one of start/goal is missing, generate a default for only the missing endpoint.
    # Preserve the supplied endpoint.
    if start is None:
        default_start = (grid_rows - 1, grid_cols // 2)
        start = _find_nearest_traversable(cost_grid, default_start)
    else:
        start = _find_nearest_traversable(cost_grid, start)

    if goal is None:
        default_goal = (0, grid_cols // 2)
        goal = _find_nearest_traversable(cost_grid, default_goal)
    else:
        goal = _find_nearest_traversable(cost_grid, goal)

    if start is not None and goal is not None:
        try:
            path_result: PathResult = find_path(
                cost_grid=cost_grid,
                start=start,
                goal=goal,
                allow_diagonal=request.allow_diagonal
            )
            path_plan_response = PathPlanResponse(
                is_success=path_result.is_success,
                path=path_result.path,
                total_weighted_cost=path_result.total_weighted_cost,
                geometric_length=path_result.geometric_length,
                expanded_nodes=path_result.expanded_nodes
            )
        except Exception as e:
            path_plan_response = PathPlanResponse(
                is_success=False,
                path=[],
                total_weighted_cost=0.0,
                geometric_length=0.0,
                expanded_nodes=0,
                error_message=sanitize_error(e)
            )
    else:
        path_plan_response = PathPlanResponse(
            is_success=False,
            path=[],
            total_weighted_cost=0.0,
            geometric_length=0.0,
            expanded_nodes=0,
            error_message="No traversable start or goal endpoint exists in the evaluated cost grid."
        )

    breakdown = None
    if path_plan_response and path_plan_response.is_success and path_plan_response.path:
        breakdown = calculate_route_cost_breakdown(
            path=path_plan_response.path,
            terrain_grid=seg_response.terrain_grid,
            cost_grid=cost_grid,
            reported_total_cost=path_plan_response.total_weighted_cost
        )

    full_response = FullAnalysisResponse(
        image_id=request.image_id,
        metadata=metadata,
        segmentation=seg_response,
        costmap=costmap_response,
        path_result=path_plan_response,
        breakdown=breakdown,
        diagnostics=diagnostics
    )
    store_analysis(full_response)
    return full_response


def _find_nearest_traversable(cost_grid: List[List[Optional[float]]], target: Tuple[int, int]) -> Optional[Tuple[int, int]]:
    """Helper to find the nearest non-blocked coordinate within the grid bounds safely."""
    if not cost_grid or not cost_grid[0]:
        return None
    rows = len(cost_grid)
    cols = len(cost_grid[0])
    tr, tc = target

    tr = max(0, min(rows - 1, tr))
    tc = max(0, min(cols - 1, tc))

    if cost_grid[tr][tc] is not None:
        return (tr, tc)

    # Spiral / radius search
    for r_dist in range(1, max(rows, cols)):
        for dr in range(-r_dist, r_dist + 1):
            for dc in range(-r_dist, r_dist + 1):
                nr, nc = tr + dr, tc + dc
                if 0 <= nr < rows and 0 <= nc < cols and cost_grid[nr][nc] is not None:
                    return (nr, nc)
    return None
