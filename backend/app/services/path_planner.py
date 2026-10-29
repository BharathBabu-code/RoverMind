import math
import heapq
from dataclasses import dataclass
from typing import List, Tuple, Optional, Dict, Any

@dataclass
class PathResult:
    """Explicit representation of the pathfinding result."""
    is_success: bool
    path: List[Tuple[int, int]]
    total_weighted_cost: float
    geometric_length: float
    expanded_nodes: int

def _validate_grid_and_get_min_cost(grid: Any) -> float:
    """
    Validates grid structure and values, returning the minimum traversable cost.
    Raises ValueError on malformed grids or invalid costs.
    """
    if not isinstance(grid, list) or not grid:
        raise ValueError("Grid must be a non-empty list.")
    if not isinstance(grid[0], list) or not grid[0]:
        raise ValueError("Grid must contain at least one row and one column.")
    
    rows = len(grid)
    cols = len(grid[0])
    min_cost = float('inf')
    
    for r, row in enumerate(grid):
        if not isinstance(row, list) or len(row) != cols:
            raise ValueError(f"Ragged grid: row {r} has length {len(row) if isinstance(row, list) else 'invalid'}, expected {cols}.")
        for c, val in enumerate(row):
            if val is not None:
                # Explicitly reject bool as it is a subclass of int in Python
                if type(val) is bool or not isinstance(val, (int, float)):
                    raise ValueError(f"Invalid cost type at ({r}, {c}): {type(val).__name__}.")
                if math.isnan(val) or math.isinf(val) or val < 0:
                    raise ValueError(f"Invalid numeric cost value at ({r}, {c}): {val}.")
                if val < min_cost:
                    min_cost = float(val)
                    
    return 0.0 if min_cost == float('inf') else min_cost

def _validate_coord(grid: List[List[Optional[float]]], coord: Any, name: str) -> None:
    """Validates that a coordinate is structurally valid, within bounds, and traversable."""
    if not isinstance(coord, (tuple, list)) or len(coord) != 2:
        raise ValueError(f"{name} coordinate must be a sequence of exactly two elements.")
    
    r, c = coord
    # Explicitly reject bools
    if type(r) is bool or type(c) is bool or not isinstance(r, int) or not isinstance(c, int):
        raise ValueError(f"{name} coordinate must contain only integers.")
        
    if not (0 <= r < len(grid) and 0 <= c < len(grid[0])):
        raise ValueError(f"{name} coordinate {coord} is out of bounds.")
    if grid[r][c] is None:
        raise ValueError(f"{name} coordinate {coord} is blocked.")

def _calculate_heuristic(r: int, c: int, goal_r: int, goal_c: int, min_cost: float, allow_diagonal: bool) -> float:
    """Calculates the admissible heuristic based on movement constraints."""
    if min_cost == 0.0:
        return 0.0
        
    dr = abs(r - goal_r)
    dc = abs(c - goal_c)
    
    if allow_diagonal:
        # Octile distance
        geo_dist = max(dr, dc) + (math.sqrt(2) - 1) * min(dr, dc)
    else:
        # Manhattan distance
        geo_dist = dr + dc
        
    return geo_dist * min_cost

def find_path(
    cost_grid: List[List[Optional[float]]], 
    start: Tuple[int, int], 
    goal: Tuple[int, int], 
    allow_diagonal: bool = False
) -> PathResult:
    """
    Finds the optimal route from start to goal using A*.
    Returns a PathResult explicitly detailing success, path, and cost metrics.
    """
    min_cost = _validate_grid_and_get_min_cost(cost_grid)
    _validate_coord(cost_grid, start, "Start")
    _validate_coord(cost_grid, goal, "Goal")

    # Fix 1: Normalize validated coordinates to hashable tuples for dictionary use
    start = (start[0], start[1])
    goal = (goal[0], goal[1])

    # Fix 2: Strictly validate the movement mode parameter
    if type(allow_diagonal) is not bool:
        raise ValueError(f"allow_diagonal must be a boolean, got {type(allow_diagonal).__name__}")

    if start == goal:
        return PathResult(
            is_success=True, 
            path=[start], 
            total_weighted_cost=0.0, 
            geometric_length=0.0, 
            expanded_nodes=0
        )

    rows, cols = len(cost_grid), len(cost_grid[0])
    
    # Priority Queue tuple: (f_score, h_score, tie_breaker, (r, c), g_score_at_insertion)
    open_set = []
    tie_breaker = 0
    
    start_h = _calculate_heuristic(start[0], start[1], goal[0], goal[1], min_cost, allow_diagonal)
    heapq.heappush(open_set, (start_h, start_h, tie_breaker, start, 0.0))
    
    g_score: Dict[Tuple[int, int], float] = {start: 0.0}
    # Track parent pointers: destination -> (parent, geometric_distance, destination_cost)
    came_from: Dict[Tuple[int, int], Tuple[Tuple[int, int], float, float]] = {}
    
    expanded_nodes = 0
    SQRT_2 = math.sqrt(2)

    while open_set:
        current_f, current_h, _, current, current_g = heapq.heappop(open_set)
        
        # Stale priority queue entry check using explicitly stored g_score
        if current_g > g_score.get(current, float('inf')):
            continue
            
        if current == goal:
            break
            
        expanded_nodes += 1
        r, c = current

        neighbors = []
        # 1. Cardinal movements
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and cost_grid[nr][nc] is not None:
                neighbors.append((nr, nc, 1.0, cost_grid[nr][nc]))
                
        # 2. Diagonal movements
        if allow_diagonal:
            for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and cost_grid[nr][nc] is not None:
                    # Prevent corner cutting: adjacent cardinals must be valid
                    if cost_grid[r+dr][c] is not None and cost_grid[r][c+dc] is not None:
                        neighbors.append((nr, nc, SQRT_2, cost_grid[nr][nc]))

        for nr, nc, geo_dist, dest_cost in neighbors:
            tentative_g = current_g + (geo_dist * dest_cost)
            neighbor_node = (nr, nc)
            
            if tentative_g < g_score.get(neighbor_node, float('inf')):
                came_from[neighbor_node] = (current, geo_dist, dest_cost)
                g_score[neighbor_node] = tentative_g
                h = _calculate_heuristic(nr, nc, goal[0], goal[1], min_cost, allow_diagonal)
                f = tentative_g + h
                
                tie_breaker += 1
                heapq.heappush(open_set, (f, h, tie_breaker, neighbor_node, tentative_g))

    if goal not in came_from:
        return PathResult(
            is_success=False,
            path=[],
            total_weighted_cost=0.0,
            geometric_length=0.0,
            expanded_nodes=expanded_nodes
        )

    # Path Reconstruction
    path = []
    current_node = goal
    total_geometric_len = 0.0
    
    while current_node != start:
        path.append(current_node)
        parent, geo_dist, _ = came_from[current_node]
        total_geometric_len += geo_dist
        current_node = parent
        
    path.append(start)
    path.reverse()

    return PathResult(
        is_success=True,
        path=path,
        total_weighted_cost=g_score[goal],
        geometric_length=total_geometric_len,
        expanded_nodes=expanded_nodes
    )