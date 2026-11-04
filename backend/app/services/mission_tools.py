import math
from typing import Dict, Any, Optional, List, Tuple

from backend.app.schemas.models import (
    FullAnalysisResponse,
    RouteComparisonResponse
)
from backend.app.services.mission_context import get_analysis, build_mission_context
from backend.app.services.terrain_costmap import build_cost_map
from backend.app.services.path_planner import find_path, PathResult


def tool_get_mission_summary(image_id: str) -> Dict[str, Any]:
    """Returns overview metadata, model provenance, and route feasibility for the active mission."""
    analysis = get_analysis(image_id)
    if not analysis:
        return {"error": f"Active mission for image '{image_id}' not found. Please run analysis first."}

    ctx = build_mission_context(analysis)
    return {
        "mission_id": ctx.mission_id,
        "image_id": ctx.image_id,
        "filename": ctx.image_filename,
        "resolution": f"{ctx.image_dimensions[0]}x{ctx.image_dimensions[1]}",
        "grid_resolution": f"{ctx.grid_dimensions[0]}x{ctx.grid_dimensions[1]}",
        "segmentation_model": ctx.source_model,
        "is_synthetic": ctx.is_synthetic,
        "route_found": ctx.route_found,
        "waypoints": ctx.waypoints_count,
        "total_cost": ctx.total_weighted_cost,
        "geometric_distance": ctx.geometric_length
    }


def tool_get_terrain_distribution(image_id: str) -> Dict[str, Any]:
    """Returns verified terrain class counts, percentages, and unknown/unclassified statistics."""
    analysis = get_analysis(image_id)
    if not analysis:
        return {"error": f"Active mission for image '{image_id}' not found."}

    ctx = build_mission_context(analysis)
    return {
        "image_id": ctx.image_id,
        "total_cells": ctx.total_cells,
        "cell_counts": ctx.terrain_distribution,
        "percentages": ctx.terrain_percentages,
        "unknown_cells": ctx.unknown_cells,
        "unknown_percentage": ctx.unknown_percentage,
        "configured_costs": ctx.terrain_costs
    }


def tool_get_region_details(image_id: str) -> Dict[str, Any]:
    """Returns segmented concept regions, bounding boxes, and pixel surface areas."""
    analysis = get_analysis(image_id)
    if not analysis:
        return {"error": f"Active mission for image '{image_id}' not found."}

    masks = analysis.segmentation.masks
    regions = [
        {
            "object_id": m.object_id,
            "concept": m.concept,
            "area_pixels": m.area_pixels,
            "bounds": m.bounds,
            "confidence": m.confidence
        }
        for m in masks[:20]  # Cap to first 20 records to bound payload size
    ]
    return {
        "image_id": analysis.image_id,
        "total_regions_count": len(masks),
        "regions": regions
    }


def tool_get_route_metrics(image_id: str) -> Dict[str, Any]:
    """Returns pathfinding telemetry, waypoints count, weighted cost, and search node complexity."""
    analysis = get_analysis(image_id)
    if not analysis:
        return {"error": f"Active mission for image '{image_id}' not found."}

    if not analysis.path_result or not analysis.path_result.is_success:
        return {
            "image_id": analysis.image_id,
            "is_success": False,
            "message": "No traversable route found between endpoints due to impassable obstacle barriers."
        }

    return {
        "image_id": analysis.image_id,
        "is_success": True,
        "waypoints_count": len(analysis.path_result.path),
        "total_weighted_cost": round(analysis.path_result.total_weighted_cost, 2),
        "geometric_length": round(analysis.path_result.geometric_length, 2),
        "expanded_nodes": analysis.path_result.expanded_nodes,
        "start": analysis.path_result.path[0] if analysis.path_result.path else None,
        "goal": analysis.path_result.path[-1] if analysis.path_result.path else None
    }


def tool_compare_routes(
    image_id: str,
    alternative_terrain_costs: Dict[str, Optional[float]],
    allow_diagonal: Optional[bool] = None
) -> RouteComparisonResponse:
    """
    Recalculates a simulated route using alternative terrain impedance weights without mutating the active mission state.
    """
    analysis = get_analysis(image_id)
    if not analysis:
        raise KeyError(f"Active mission for image '{image_id}' not found.")

    if not analysis.path_result or not analysis.path_result.path:
        raise ValueError("Original analysis does not have an active calculated path to compare against.")

    start = analysis.path_result.path[0]
    goal = analysis.path_result.path[-1]
    diag = allow_diagonal if allow_diagonal is not None else True

    # Merge alternative costs with existing costs to ensure complete label coverage
    merged_costs = dict(analysis.costmap.terrain_costs)
    merged_costs.update(alternative_terrain_costs)

    # Build simulated costmap with alternative costs
    alt_cost_grid = build_cost_map(
        terrain_grid=analysis.segmentation.terrain_grid,
        terrain_costs=merged_costs
    )

    alt_path_result: PathResult = find_path(
        cost_grid=alt_cost_grid,
        start=start,
        goal=goal,
        allow_diagonal=diag
    )

    orig_cost = round(analysis.path_result.total_weighted_cost, 2)
    orig_len = round(analysis.path_result.geometric_length, 2)
    orig_count = len(analysis.path_result.path)

    alt_cost = round(alt_path_result.total_weighted_cost, 2) if alt_path_result.is_success else math.inf
    alt_len = round(alt_path_result.geometric_length, 2) if alt_path_result.is_success else math.inf
    alt_count = len(alt_path_result.path) if alt_path_result.is_success else 0

    cost_delta = round(alt_cost - orig_cost, 2) if math.isfinite(alt_cost) else 9999.0
    len_delta = round(alt_len - orig_len, 2) if math.isfinite(alt_len) else 9999.0

    if not alt_path_result.is_success:
        summary = "Alternative parameters rendered all paths to the destination impassable."
    elif cost_delta > 0:
        summary = f"Alternative weights increased path impedance by +{cost_delta} (+{len_delta} length units)."
    elif cost_delta < 0:
        summary = f"Alternative weights reduced path impedance by {cost_delta} ({len_delta} length units change)."
    else:
        summary = "Alternative weights resulted in identical path impedance and geometry."

    return RouteComparisonResponse(
        image_id=image_id,
        original_cost=orig_cost,
        original_length=orig_len,
        original_waypoints_count=orig_count,
        alternative_cost=alt_cost if math.isfinite(alt_cost) else -1.0,
        alternative_length=alt_len if math.isfinite(alt_len) else -1.0,
        alternative_waypoints_count=alt_count,
        cost_delta=cost_delta,
        length_delta=len_delta,
        comparison_summary=summary,
        alternative_path=alt_path_result.path
    )


def tool_get_analysis_diagnostics(image_id: str) -> Dict[str, Any]:
    """Returns execution logs, model provenance, and scientific honesty boundaries."""
    analysis = get_analysis(image_id)
    if not analysis:
        return {"error": f"Active mission for image '{image_id}' not found."}

    ctx = build_mission_context(analysis)
    return {
        "image_id": ctx.image_id,
        "segmentation_model": ctx.source_model,
        "is_synthetic": ctx.is_synthetic,
        "diagnostics": ctx.diagnostics,
        "scientific_limitations": ctx.limitations
    }


# Map of available mission tools for the reasoning agent
AVAILABLE_MISSION_TOOLS = {
    "get_mission_summary": tool_get_mission_summary,
    "get_terrain_distribution": tool_get_terrain_distribution,
    "get_region_details": tool_get_region_details,
    "get_route_metrics": tool_get_route_metrics,
    "compare_routes": tool_compare_routes,
    "get_analysis_diagnostics": tool_get_analysis_diagnostics
}

# OpenAI/Meta tool definitions schema
MISSION_TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_mission_summary",
            "description": "Retrieves the active planetary mission summary, resolution, model provenance, and route status.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_id": {"type": "string", "description": "The active mission image ID."}
                },
                "required": ["image_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_terrain_distribution",
            "description": "Retrieves exact terrain cell counts, percentages, and unknown/unclassified statistics.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_id": {"type": "string", "description": "The active mission image ID."}
                },
                "required": ["image_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_region_details",
            "description": "Retrieves segmented concept regions, bounding box pixel coordinates, and surface areas.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_id": {"type": "string", "description": "The active mission image ID."}
                },
                "required": ["image_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_route_metrics",
            "description": "Retrieves pathfinding telemetry including waypoints count, weighted cost, and search node complexity.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_id": {"type": "string", "description": "The active mission image ID."}
                },
                "required": ["image_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "compare_routes",
            "description": "Simulates path planning with alternative terrain traversal costs without modifying original mission state.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_id": {"type": "string", "description": "The active mission image ID."},
                    "alternative_terrain_costs": {
                        "type": "object",
                        "description": "Map of terrain label to alternative cost multiplier (e.g. {'rocky': 10.0, 'loose': 4.0})."
                    }
                },
                "required": ["image_id", "alternative_terrain_costs"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_analysis_diagnostics",
            "description": "Retrieves model execution diagnostics, provenance, and scientific uncertainty boundaries.",
            "parameters": {
                "type": "object",
                "properties": {
                    "image_id": {"type": "string", "description": "The active mission image ID."}
                },
                "required": ["image_id"]
            }
        }
    }
]
