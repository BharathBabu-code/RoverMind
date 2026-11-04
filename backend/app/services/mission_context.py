import threading
from collections import OrderedDict
from typing import Dict, Optional, Tuple, Any, List

from backend.app.schemas.models import (
    FullAnalysisResponse,
    MissionContextDto
)

# In-memory LRU store for completed analyses: image_id -> FullAnalysisResponse
MAX_ANALYSIS_STORE_CAPACITY = 25
_ANALYSIS_STORE: OrderedDict[str, FullAnalysisResponse] = OrderedDict()
_ANALYSIS_LOCK = threading.Lock()


def store_analysis(analysis: FullAnalysisResponse) -> None:
    """Stores or updates an analysis in the active mission context registry."""
    with _ANALYSIS_LOCK:
        while len(_ANALYSIS_STORE) >= MAX_ANALYSIS_STORE_CAPACITY:
            _ANALYSIS_STORE.popitem(last=False)
        _ANALYSIS_STORE[analysis.image_id] = analysis


def get_analysis(image_id: str) -> Optional[FullAnalysisResponse]:
    """Retrieves an active analysis by image_id with LRU touch."""
    with _ANALYSIS_LOCK:
        item = _ANALYSIS_STORE.get(image_id)
        if item:
            _ANALYSIS_STORE.move_to_end(image_id)
            return item
        return None


def clear_analysis_store() -> None:
    """Clears all stored mission analyses."""
    with _ANALYSIS_LOCK:
        _ANALYSIS_STORE.clear()


def build_mission_context(analysis: FullAnalysisResponse) -> MissionContextDto:
    """
    Constructs a compact, validated structured mission context from an analysis response.
    Computes cell distribution, percentages, route metrics, and scientific boundaries.
    """
    grid = analysis.segmentation.terrain_grid
    rows = analysis.segmentation.grid_height
    cols = analysis.segmentation.grid_width
    total_cells = rows * cols

    distribution: Dict[str, int] = {}
    for r in range(rows):
        for c in range(cols):
            label = grid[r][c]
            distribution[label] = distribution.get(label, 0) + 1

    percentages: Dict[str, float] = {
        label: round((count / total_cells) * 100.0, 2)
        for label, count in distribution.items()
    }

    unknown_count = distribution.get("unknown", 0)
    unknown_pct = percentages.get("unknown", 0.0)

    # Route metrics
    route_found = False
    waypoints_count = 0
    total_weighted_cost = 0.0
    geom_length = 0.0
    expanded_nodes = 0
    start_coord = None
    goal_coord = None

    if analysis.path_result and analysis.path_result.is_success:
        route_found = True
        waypoints_count = len(analysis.path_result.path)
        total_weighted_cost = round(analysis.path_result.total_weighted_cost, 2)
        geom_length = round(analysis.path_result.geometric_length, 2)
        expanded_nodes = analysis.path_result.expanded_nodes
        if analysis.path_result.path:
            start_coord = analysis.path_result.path[0]
            goal_coord = analysis.path_result.path[-1]

    # Unique detected concepts
    concepts = list({m.concept for m in analysis.segmentation.masks}) if analysis.segmentation.masks else ["rock", "sand", "obstacle"]

    limitations = [
        "Monocular 2D imagery does not establish physical elevation, slope gradient, or subsurface soil mechanics.",
        "Estimated traversal costs represent configured decision-support weights, not certified vehicle safety guarantees.",
        "Visual segmentation boundaries from SAM 3.1 represent semantic prompt matches, not verified geological strata.",
        "Unknown or unobserved regions carry conservative default traversal penalties."
    ]

    return MissionContextDto(
        mission_id=f"mission_{analysis.image_id[:8]}",
        image_id=analysis.image_id,
        image_filename=analysis.metadata.filename,
        image_dimensions=(analysis.metadata.width, analysis.metadata.height),
        grid_dimensions=(cols, rows),
        is_synthetic=analysis.segmentation.is_synthetic,
        source_model=analysis.segmentation.source_model,
        detection_concepts=concepts,
        terrain_distribution=distribution,
        terrain_percentages=percentages,
        total_cells=total_cells,
        unknown_cells=unknown_count,
        unknown_percentage=unknown_pct,
        terrain_costs=analysis.costmap.terrain_costs,
        start_coord=start_coord,
        goal_coord=goal_coord,
        route_found=route_found,
        waypoints_count=waypoints_count,
        total_weighted_cost=total_weighted_cost,
        geometric_length=geom_length,
        expanded_nodes=expanded_nodes,
        masks_count=len(analysis.segmentation.masks),
        diagnostics=analysis.diagnostics,
        limitations=limitations
    )


def format_context_for_prompt(context: MissionContextDto) -> str:
    """Formats a compact text prompt representing the ground truth of the active mission."""
    lines = [
        f"MISSION CONTEXT // IMAGE ID: {context.image_id}",
        f"Frame: {context.image_filename} ({context.image_dimensions[0]}x{context.image_dimensions[1]} px)",
        f"Segmentation Grid: {context.grid_dimensions[0]}x{context.grid_dimensions[1]} ({context.total_cells} total cells)",
        f"Segmentation Source: {context.source_model} (Synthetic fallback: {context.is_synthetic})",
        f"Detected Concepts: {', '.join(context.detection_concepts)} ({context.masks_count} segmented masks)",
        "",
        "TERRAIN DISTRIBUTION:",
    ]
    for label, count in sorted(context.terrain_distribution.items()):
        pct = context.terrain_percentages.get(label, 0.0)
        cost = context.terrain_costs.get(label, "N/A")
        cost_str = f"cost {cost}" if cost is not None else "BLOCKED/IMPASSABLE"
        lines.append(f"- {label.upper()}: {count} cells ({pct}%) [{cost_str}]")

    lines.extend([
        "",
        "A* NAVIGATION PLAN:",
        f"- Path Found: {context.route_found}",
        f"- Start Coordinate: {context.start_coord}",
        f"- Goal Coordinate: {context.goal_coord}",
        f"- Waypoints Count: {context.waypoints_count}",
        f"- Total Weighted Traversal Cost: {context.total_weighted_cost}",
        f"- Geometric Distance: {context.geometric_length} units",
        f"- Search Complexity (Expanded Nodes): {context.expanded_nodes}",
        "",
        "SCIENTIFIC HONESTY & OPERATIONAL BOUNDARIES:",
    ])
    for lim in context.limitations:
        lines.append(f"- {lim}")

    return "\n".join(lines)
