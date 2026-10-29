import pytest
import math
import heapq
from typing import List, Tuple, Optional
from backend.app.services.path_planner import find_path, PathResult

# --- Test Helpers ---

def verify_valid_path(
    grid: List[List[Optional[float]]],
    result: PathResult,
    start: Tuple[int, int],
    goal: Tuple[int, int],
    allow_diagonal: bool,
    expected_weighted_cost: Optional[float] = None,
    expected_geometric_length: Optional[float] = None
) -> None:
    """Helper to rigorously verify path invariants for successful routes."""
    assert result.is_success is True
    assert len(result.path) >= 1
    assert result.path[0] == start
    assert result.path[-1] == goal

    recalculated_cost = 0.0
    recalculated_geo_len = 0.0
    SQRT_2 = math.sqrt(2)

    for i in range(len(result.path) - 1):
        r1, c1 = result.path[i]
        r2, c2 = result.path[i + 1]

        # Bounds and blocked checks
        assert 0 <= r1 < len(grid) and 0 <= c1 < len(grid[0])
        assert 0 <= r2 < len(grid) and 0 <= c2 < len(grid[0])
        assert grid[r1][c1] is not None
        assert grid[r2][c2] is not None

        dr = r2 - r1
        dc = c2 - c1
        
        is_cardinal = (abs(dr) + abs(dc) == 1)
        is_diagonal = (abs(dr) == 1 and abs(dc) == 1)

        if not allow_diagonal:
            assert is_cardinal, f"Illegal diagonal move from {(r1, c1)} to {(r2, c2)}"
        else:
            assert is_cardinal or is_diagonal, f"Illegal jump from {(r1, c1)} to {(r2, c2)}"

        if is_diagonal:
            # Check corner cutting invariant
            assert grid[r1 + dr][c1] is not None, "Corner cut detected!"
            assert grid[r1][c1 + dc] is not None, "Corner cut detected!"
            geo_dist = SQRT_2
        else:
            geo_dist = 1.0

        dest_cost = grid[r2][c2]
        recalculated_geo_len += geo_dist
        recalculated_cost += geo_dist * dest_cost

    assert math.isclose(result.geometric_length, recalculated_geo_len)
    assert math.isclose(result.total_weighted_cost, recalculated_cost)
    
    if expected_weighted_cost is not None:
        assert math.isclose(result.total_weighted_cost, expected_weighted_cost)
    if expected_geometric_length is not None:
        assert math.isclose(result.geometric_length, expected_geometric_length)

def run_dijkstra_reference(
    grid: List[List[Optional[float]]], 
    start: Tuple[int, int], 
    goal: Tuple[int, int], 
    allow_diagonal: bool
) -> float:
    """Independent Dijkstra implementation for optimality cross-checking."""
    rows, cols = len(grid), len(grid[0])
    pq = [(0.0, 0, start)]
    g_score = {start: 0.0}
    tie = 0
    SQRT_2 = math.sqrt(2)

    while pq:
        cost, _, current = heapq.heappop(pq)
        
        if cost > g_score.get(current, float('inf')):
            continue
        if current == goal:
            return cost
            
        r, c = current
        neighbors = []
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = r + dr, c + dc
            if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] is not None:
                neighbors.append((nr, nc, 1.0))
                
        if allow_diagonal:
            for dr, dc in [(-1, -1), (-1, 1), (1, -1), (1, 1)]:
                nr, nc = r + dr, c + dc
                if 0 <= nr < rows and 0 <= nc < cols and grid[nr][nc] is not None:
                    if grid[r+dr][c] is not None and grid[r][c+dc] is not None:
                        neighbors.append((nr, nc, SQRT_2))

        for nr, nc, geo_dist in neighbors:
            dest_cost = grid[nr][nc]
            new_cost = cost + (geo_dist * dest_cost)
            if new_cost < g_score.get((nr, nc), float('inf')):
                g_score[(nr, nc)] = new_cost
                tie += 1
                heapq.heappush(pq, (new_cost, tie, (nr, nc)))
                
    return float('inf')

# --- Tests ---

def test_1_empty_grid():
    with pytest.raises(ValueError, match="non-empty"):
        find_path([], (0, 0), (0, 0))

def test_2_empty_first_row():
    with pytest.raises(ValueError, match="one column"):
        find_path([[]], (0, 0), (0, 0))

def test_3_ragged_grid():
    with pytest.raises(ValueError, match="Ragged grid"):
        find_path([[1.0, 1.0], [1.0]], (0, 0), (0, 1))

def test_4_negative_traversal_cost():
    with pytest.raises(ValueError, match="Invalid numeric cost"):
        find_path([[1.0, -1.0]], (0, 0), (0, 1))

def test_5_nan_traversal_cost():
    with pytest.raises(ValueError, match="Invalid numeric cost"):
        find_path([[1.0, float('nan')]], (0, 0), (0, 1))

def test_6_infinity_costs():
    with pytest.raises(ValueError, match="Invalid numeric cost"):
        find_path([[1.0, float('inf')]], (0, 0), (0, 1))
    with pytest.raises(ValueError, match="Invalid numeric cost"):
        find_path([[1.0, float('-inf')]], (0, 0), (0, 1))

def test_7_boolean_traversal_cost():
    with pytest.raises(ValueError, match="Invalid cost type"):
        find_path([[1.0, True]], (0, 0), (0, 1)) # type: ignore

def test_8_malformed_coordinates():
    grid = [[1.0, 1.0]]
    with pytest.raises(ValueError, match="exactly two elements"):
        find_path(grid, (0, 0, 0), (0, 1)) # type: ignore

def test_9_non_integer_coordinates():
    grid = [[1.0, 1.0]]
    with pytest.raises(ValueError, match="contain only integers"):
        find_path(grid, (0, 0.0), (0, 1)) # type: ignore

def test_10_boolean_coordinates():
    grid = [[1.0, 1.0], [1.0, 1.0]]
    with pytest.raises(ValueError, match="contain only integers"):
        find_path(grid, (False, False), (0, 1)) # type: ignore

def test_11_blocked_start():
    with pytest.raises(ValueError, match="blocked"):
        find_path([[None, 1.0]], (0, 0), (0, 1))

def test_12_blocked_goal():
    with pytest.raises(ValueError, match="blocked"):
        find_path([[1.0, None]], (0, 0), (0, 1))

def test_13_all_blocked_cells():
    with pytest.raises(ValueError, match="blocked"):
        find_path([[None, None], [None, None]], (0, 0), (1, 1))

def test_14_four_way_route_around_obstacle():
    grid = [
        [1.0, None, 1.0],
        [1.0, 1.0, 1.0]
    ]
    result = find_path(grid, (0, 0), (0, 2), allow_diagonal=False)
    verify_valid_path(grid, result, (0, 0), (0, 2), False, expected_weighted_cost=4.0, expected_geometric_length=4.0)

def test_15_diagonal_corner_cutting_both_blocked():
    grid = [
        [1.0, None],
        [None, 1.0]
    ]
    result = find_path(grid, (0, 0), (1, 1), allow_diagonal=True)
    assert result.is_success is False

def test_16_diagonal_corner_cutting_one_blocked():
    grid = [
        [1.0, None],
        [1.0, 1.0]
    ]
    result = find_path(grid, (0, 0), (1, 1), allow_diagonal=True)
    # The direct diagonal (0,0)->(1,1) is forbidden because (0,1) is blocked.
    # It must take the L-shape (0,0)->(1,0)->(1,1)
    verify_valid_path(grid, result, (0, 0), (1, 1), True, expected_weighted_cost=2.0, expected_geometric_length=2.0)

def test_17_valid_diagonal_movement():
    grid = [
        [1.0, 2.0],
        [1.0, 1.0]
    ]
    result = find_path(grid, (0, 0), (1, 1), allow_diagonal=True)
    expected_cost = math.sqrt(2) * 1.0
    verify_valid_path(grid, result, (0, 0), (1, 1), True, expected_weighted_cost=expected_cost, expected_geometric_length=math.sqrt(2))

def test_18_zero_cost_traversal():
    grid = [[0.0, 0.0], [0.0, 0.0]]
    result = find_path(grid, (0, 0), (1, 1), allow_diagonal=False)
    verify_valid_path(grid, result, (0, 0), (1, 1), False, expected_weighted_cost=0.0, expected_geometric_length=2.0)

def test_19_start_equals_goal():
    grid = [[1.0]]
    result = find_path(grid, (0, 0), (0, 0))
    assert result.is_success is True
    assert result.path == [(0, 0)]
    assert result.total_weighted_cost == 0.0
    assert result.geometric_length == 0.0

def test_20_unreachable_goal():
    grid = [
        [1.0, None, 1.0],
        [1.0, None, 1.0],
        [1.0, None, 1.0]
    ]
    result = find_path(grid, (0, 0), (0, 2))
    assert result.is_success is False
    assert result.path == []
    assert result.total_weighted_cost == 0.0
    assert result.geometric_length == 0.0

def test_21_lower_cost_longer_geometric_path():
    grid = [
        [1.0, 1.0, 1.0],
        [50.0, 50.0, 1.0],
        [1.0, 1.0, 1.0]
    ]
    result = find_path(grid, (0, 0), (2, 0), allow_diagonal=False)
    # Expected U-shape path dodging the 50.0 costs
    verify_valid_path(grid, result, (0, 0), (2, 0), False, expected_weighted_cost=6.0, expected_geometric_length=6.0)

def test_22_independent_dijkstra_optimality():
    """Cross-checks A* weighted cost against an independent Dijkstra implementation."""
    grids = [
        (
            [
                [1.0, 2.0, 3.0],
                [4.0, 5.0, 1.0],
                [1.0, 1.0, 1.0]
            ], (0, 0), (2, 2)
        ),
        (
            [
                [1.0, None, 1.0, 1.0],
                [1.0, 10.0, 20.0, 1.0],
                [1.0, 1.0, 1.0, 1.0]
            ], (0, 0), (0, 3)
        )
    ]
    
    for grid, start, goal in grids:
        for allow_diagonal in [False, True]:
            a_star_result = find_path(grid, start, goal, allow_diagonal)
            dijkstra_cost = run_dijkstra_reference(grid, start, goal, allow_diagonal)
            
            assert math.isclose(a_star_result.total_weighted_cost, dijkstra_cost), \
                f"Optimality mismatch on grid {grid} with diagonal={allow_diagonal}"

def test_23_list_coordinates_successful_path():
    """Ensures start and goal coordinates provided as lists are seamlessly converted to tuples."""
    grid = [[1.0, 1.0, 1.0]]
    result = find_path(grid, [0, 0], [0, 2], allow_diagonal=False) # type: ignore
    assert result.is_success is True
    assert result.path == [(0, 0), (0, 1), (0, 2)]
    assert result.total_weighted_cost == 2.0

def test_24_list_coordinates_start_equals_goal():
    """Ensures list coordinates properly trigger the start == goal immediate return."""
    grid = [[1.0, 1.0]]
    result = find_path(grid, [0, 1], [0, 1], allow_diagonal=False) # type: ignore
    assert result.is_success is True
    assert result.path == [(0, 1)]
    assert result.total_weighted_cost == 0.0

def test_25_invalid_allow_diagonal_parameter():
    """Ensures the allow_diagonal parameter strictly rejects non-boolean truthy values like 'yes' or 1."""
    grid = [[1.0, 1.0]]
    with pytest.raises(ValueError, match="allow_diagonal must be a boolean"):
        find_path(grid, (0, 0), (0, 1), allow_diagonal=1) # type: ignore
        
    with pytest.raises(ValueError, match="allow_diagonal must be a boolean"):
        find_path(grid, (0, 0), (0, 1), allow_diagonal="yes") # type: ignore