from fastapi import APIRouter, HTTPException
from backend.app.schemas.models import (
    PathPlanRequest,
    PathPlanResponse,
    RecomputePathRequest,
    RecomputePathResponse,
    CostmapResponse,
    FullAnalysisResponse,
    FullAnalysisRequest
)
from backend.app.services.path_planner import find_path, PathResult
from backend.app.services.analysis_orchestrator import run_full_analysis
from backend.app.services.mission_context import get_analysis, store_analysis
from backend.app.services.terrain_costmap import build_cost_map
from backend.app.services.route_breakdown import calculate_route_cost_breakdown

router = APIRouter(prefix="/planning", tags=["Path Planning"])


@router.post("/find-path", response_model=PathPlanResponse)
async def calculate_path(request: PathPlanRequest) -> PathPlanResponse:
    """
    Computes the lowest-cost A* path across the specified cost grid
    from start coordinate (row, col) to goal coordinate (row, col).
    """
    cost_grid = request.cost_grid

    if cost_grid is None and request.image_id is not None:
        # Generate costmap from the image
        analysis = run_full_analysis(
            FullAnalysisRequest(
                image_id=request.image_id,
                start=request.start,
                goal=request.goal,
                allow_diagonal=request.allow_diagonal
            )
        )
        if analysis.path_result is not None:
            return analysis.path_result
        cost_grid = analysis.costmap.cost_grid

    if cost_grid is None:
        raise HTTPException(
            status_code=400,
            detail="Either 'cost_grid' or 'image_id' must be provided to calculate route."
        )

    try:
        result: PathResult = find_path(
            cost_grid=cost_grid,
            start=request.start,
            goal=request.goal,
            allow_diagonal=request.allow_diagonal
        )
        return PathPlanResponse(
            is_success=result.is_success,
            path=result.path,
            total_weighted_cost=result.total_weighted_cost,
            geometric_length=result.geometric_length,
            expanded_nodes=result.expanded_nodes
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Path planning execution error: {str(e)}")


@router.post("/recompute", response_model=RecomputePathResponse)
async def recompute_path(request: RecomputePathRequest) -> RecomputePathResponse:
    """
    Dynamically recalculates terrain costmap and A* route with custom terrain weights or updated endpoints.
    Updates the active mission state in _ANALYSIS_STORE so telemetry, briefings, and chatbot reflect new route.
    """
    analysis = get_analysis(request.image_id)
    if not analysis:
        raise HTTPException(
            status_code=404,
            detail=f"No active analysis found for image_id '{request.image_id}'. Run analysis first."
        )

    # Validate and merge terrain costs
    merged_costs = dict(analysis.costmap.terrain_costs)
    if request.terrain_costs:
        for label, cost in request.terrain_costs.items():
            if label == "obstacle" and cost is not None:
                raise HTTPException(
                    status_code=400,
                    detail="Obstacle terrain cannot be made traversable in standard operations. Obstacles must remain impassable (null)."
                )
            if cost is not None:
                if not isinstance(cost, (int, float)) or cost <= 0:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Cost for '{label}' must be a strictly positive number (got {cost})."
                    )
                merged_costs[label] = float(cost)

    # Rebuild costmap using authoritative build_cost_map
    new_cost_grid = build_cost_map(
        terrain_grid=analysis.segmentation.terrain_grid,
        terrain_costs=merged_costs
    )

    rows = len(new_cost_grid)
    cols = len(new_cost_grid[0])

    # Determine start and goal
    start = request.start
    goal = request.goal

    if start is None:
        if analysis.path_result and analysis.path_result.path:
            start = analysis.path_result.path[0]
        else:
            start = (rows - 1, cols // 2)

    if goal is None:
        if analysis.path_result and analysis.path_result.path:
            goal = analysis.path_result.path[-1]
        else:
            goal = (0, cols // 2)

    # Validate coordinates
    if not (0 <= start[0] < rows and 0 <= start[1] < cols):
        raise HTTPException(status_code=400, detail=f"Start coordinate {start} is out of grid bounds ({rows}x{cols}).")
    if not (0 <= goal[0] < rows and 0 <= goal[1] < cols):
        raise HTTPException(status_code=400, detail=f"Goal coordinate {goal} is out of grid bounds ({rows}x{cols}).")
    if new_cost_grid[start[0]][start[1]] is None:
        raise HTTPException(status_code=400, detail=f"Start coordinate {start} is an impassable obstacle! Please select a traversable terrain cell.")
    if new_cost_grid[goal[0]][goal[1]] is None:
        raise HTTPException(status_code=400, detail=f"Goal coordinate {goal} is an impassable obstacle! Please select a traversable terrain cell.")

    try:
        path_res = find_path(
            cost_grid=new_cost_grid,
            start=start,
            goal=goal,
            allow_diagonal=request.allow_diagonal
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Path calculation failed: {str(e)}")

    breakdown = calculate_route_cost_breakdown(
        path=path_res.path,
        terrain_grid=analysis.segmentation.terrain_grid,
        cost_grid=new_cost_grid,
        reported_total_cost=path_res.total_weighted_cost
    )

    costmap_resp = CostmapResponse(
        image_id=request.image_id,
        grid_width=cols,
        grid_height=rows,
        cost_grid=new_cost_grid,
        terrain_costs=merged_costs
    )

    path_resp = PathPlanResponse(
        is_success=path_res.is_success,
        path=path_res.path,
        total_weighted_cost=path_res.total_weighted_cost,
        geometric_length=path_res.geometric_length,
        expanded_nodes=path_res.expanded_nodes
    )

    # Update active analysis in store
    updated_analysis = FullAnalysisResponse(
        image_id=analysis.image_id,
        metadata=analysis.metadata,
        segmentation=analysis.segmentation,
        costmap=costmap_resp,
        path_result=path_resp,
        breakdown=breakdown,
        diagnostics=analysis.diagnostics
    )
    store_analysis(updated_analysis)

    return RecomputePathResponse(
        image_id=request.image_id,
        costmap=costmap_resp,
        path_result=path_resp,
        breakdown=breakdown
    )
