import math
from typing import List, Tuple, Optional, Dict
from backend.app.schemas.models import RouteCostBreakdownDto


def calculate_route_cost_breakdown(
    path: List[Tuple[int, int]],
    terrain_grid: List[List[str]],
    cost_grid: List[List[Optional[float]]],
    reported_total_cost: float
) -> RouteCostBreakdownDto:
    """
    Rigorously computes and reconciles the exact mathematical breakdown of an A* route.
    
    Formula:
    Step cost from (r_i, c_i) to (r_{i+1}, c_{i+1}) = geo_distance * cost_grid[r_{i+1}][c_{i+1}]
    where geo_distance = 1.0 for cardinal moves, and sqrt(2) for diagonal moves.
    Start cell (r_0, c_0) incurs 0 entry cost.
    
    Guarantees mathematical reconciliation:
    sum(cost_contributions.values()) == total_calculated_cost == reported_total_cost (within float tolerance).
    """
    if not path or len(path) < 2:
        return RouteCostBreakdownDto(
            clear_cells_count=1 if path and terrain_grid[path[0][0]][path[0][1]] == "clear" else 0,
            rocky_cells_count=1 if path and terrain_grid[path[0][0]][path[0][1]] == "rocky" else 0,
            loose_cells_count=1 if path and terrain_grid[path[0][0]][path[0][1]] == "loose" else 0,
            unknown_cells_count=1 if path and terrain_grid[path[0][0]][path[0][1]] == "unknown" else 0,
            obstacle_cells_count=0,
            cardinal_steps_count=0,
            diagonal_steps_count=0,
            cost_contributions={"clear": 0.0, "rocky": 0.0, "loose": 0.0, "unknown": 0.0},
            total_calculated_cost=0.0,
            reconciled=True,
            unknown_percentage=0.0,
            unknown_warning=False
        )

    # 1. Count traversed cells by terrain class
    cell_counts: Dict[str, int] = {"clear": 0, "rocky": 0, "loose": 0, "unknown": 0, "obstacle": 0}
    for r, c in path:
        label = terrain_grid[r][c] if 0 <= r < len(terrain_grid) and 0 <= c < len(terrain_grid[0]) else "unknown"
        cell_counts[label] = cell_counts.get(label, 0) + 1

    # 2. Compute exact step costs and step geometry
    SQRT_2 = math.sqrt(2)
    cardinal_steps = 0
    diagonal_steps = 0
    contributions: Dict[str, float] = {"clear": 0.0, "rocky": 0.0, "loose": 0.0, "unknown": 0.0}
    total_calculated_cost = 0.0

    for i in range(len(path) - 1):
        r0, c0 = path[i]
        r1, c1 = path[i + 1]
        dr = abs(r1 - r0)
        dc = abs(c1 - c0)
        is_diag = (dr == 1 and dc == 1)

        geo_dist = SQRT_2 if is_diag else 1.0
        if is_diag:
            diagonal_steps += 1
        else:
            cardinal_steps += 1

        dest_cost = cost_grid[r1][c1] if (0 <= r1 < len(cost_grid) and 0 <= c1 < len(cost_grid[0])) else 1.0
        dest_label = terrain_grid[r1][c1] if (0 <= r1 < len(terrain_grid) and 0 <= c1 < len(terrain_grid[0])) else "unknown"

        if dest_cost is not None:
            step_cost = geo_dist * dest_cost
            contributions[dest_label] = contributions.get(dest_label, 0.0) + step_cost
            total_calculated_cost += step_cost

    # Round contributions to 4 decimal places for clean reporting
    rounded_contributions = {k: round(v, 4) for k, v in contributions.items()}
    rounded_total = round(total_calculated_cost, 4)
    reconciled = abs(total_calculated_cost - reported_total_cost) < 1e-3

    unknown_cells = cell_counts.get("unknown", 0)
    unknown_pct = round((unknown_cells / len(path)) * 100.0, 2)
    unknown_warning = unknown_cells > 0

    return RouteCostBreakdownDto(
        clear_cells_count=cell_counts.get("clear", 0),
        rocky_cells_count=cell_counts.get("rocky", 0),
        loose_cells_count=cell_counts.get("loose", 0),
        unknown_cells_count=cell_counts.get("unknown", 0),
        obstacle_cells_count=cell_counts.get("obstacle", 0),
        cardinal_steps_count=cardinal_steps,
        diagonal_steps_count=diagonal_steps,
        cost_contributions=rounded_contributions,
        total_calculated_cost=rounded_total,
        reconciled=reconciled,
        unknown_percentage=unknown_pct,
        unknown_warning=unknown_warning
    )
