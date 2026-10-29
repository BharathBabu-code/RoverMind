import pytest
import math
import copy
from backend.app.services.terrain_costmap import build_cost_map

# --- Success Path Tests ---

def test_build_cost_map_success_standard_grid() -> None:
    """Verifies the core requirement using the provided example grid."""
    terrain_grid = [
        ["clear", "clear", "rocky"],
        ["loose", "rocky", "clear"]
    ]
    terrain_costs = {
        "clear": 1.0,
        "rocky": 3.0,
        "loose": 6.0,
        "cliff": None
    }
    
    expected = [
        [1.0, 1.0, 3.0],
        [6.0, 3.0, 1.0]
    ]
    
    result = build_cost_map(terrain_grid, terrain_costs)
    assert result == expected

def test_build_cost_map_preserves_none_as_impassable() -> None:
    """Verifies that None is correctly mapped to None (impassable)."""
    grid = [["clear", "cliff"]]
    costs = {"clear": 1.0, "cliff": None}
    assert build_cost_map(grid, costs) == [[1.0, None]]

def test_build_cost_map_single_cell() -> None:
    """Verifies behavior with the smallest possible valid grid (1x1)."""
    assert build_cost_map([["clear"]], {"clear": 1.0}) == [[1.0]]

def test_build_cost_map_single_column() -> None:
    """Verifies behavior with a 1D vertical grid."""
    grid = [["clear"], ["rocky"], ["clear"]]
    costs = {"clear": 1.0, "rocky": 3.0}
    assert build_cost_map(grid, costs) == [[1.0], [3.0], [1.0]]

def test_build_cost_map_no_mutation() -> None:
    """Ensures the function does not mutate the input grid or dictionary in place."""
    grid = [["clear", "rocky"]]
    costs = {"clear": 1.0, "rocky": 2.0}
    
    grid_copy = copy.deepcopy(grid)
    costs_copy = copy.deepcopy(costs)
    
    _ = build_cost_map(grid, costs)
    
    assert grid == grid_copy
    assert costs == costs_copy

# --- Validation and Edge Case Tests ---

def test_missing_label_in_mapping() -> None:
    grid = [["clear", "unknown_terrain"]]
    costs = {"clear": 1.0}
    with pytest.raises(ValueError, match="missing from terrain_costs mapping"):
        build_cost_map(grid, costs)

def test_empty_terrain_grid() -> None:
    with pytest.raises(ValueError, match="non-empty list"):
        build_cost_map([], {"clear": 1.0})

def test_empty_row_in_grid() -> None:
    with pytest.raises(ValueError, match="at least one row and one column"):
        build_cost_map([[]], {"clear": 1.0})

def test_ragged_grid() -> None:
    grid = [
        ["clear", "clear"],
        ["clear"]
    ]
    with pytest.raises(ValueError, match="Ragged grid"):
        build_cost_map(grid, {"clear": 1.0})

def test_invalid_terrain_labels() -> None:
    # Empty string label
    with pytest.raises(ValueError, match="must be a non-empty string"):
        build_cost_map([["clear", " "]], {"clear": 1.0})
    
    # Integer label inside grid
    with pytest.raises(ValueError, match="must be a non-empty string"):
        build_cost_map([["clear", 1]], {"clear": 1.0}) # type: ignore

def test_empty_or_invalid_cost_mapping() -> None:
    grid = [["clear"]]
    with pytest.raises(ValueError, match="non-empty dictionary mapping"):
        build_cost_map(grid, {})
    with pytest.raises(ValueError, match="non-empty dictionary mapping"):
        build_cost_map(grid, ["clear"]) # type: ignore

def test_invalid_cost_map_keys() -> None:
    grid = [["clear"]]
    with pytest.raises(ValueError, match="keys must be non-empty strings"):
        build_cost_map(grid, {1: 1.0}) # type: ignore
    with pytest.raises(ValueError, match="keys must be non-empty strings"):
        build_cost_map(grid, {" ": 1.0})

def test_negative_costs() -> None:
    with pytest.raises(ValueError, match="non-negative finite number"):
        build_cost_map([["clear"]], {"clear": -1.5})

def test_boolean_costs_rejected() -> None:
    # Python evaluates type(True) as bool and isinstance(True, int) as True.
    # We explicitly test that our function catches this and rejects it.
    with pytest.raises(ValueError, match="cannot be a boolean"):
        build_cost_map([["clear"]], {"clear": True}) # type: ignore
    with pytest.raises(ValueError, match="cannot be a boolean"):
        build_cost_map([["clear"]], {"clear": False}) # type: ignore

def test_nan_and_infinite_costs() -> None:
    with pytest.raises(ValueError, match="non-negative finite number"):
        build_cost_map([["clear"]], {"clear": float('inf')})
    with pytest.raises(ValueError, match="non-negative finite number"):
        build_cost_map([["clear"]], {"clear": float('-inf')})
    with pytest.raises(ValueError, match="non-negative finite number"):
        build_cost_map([["clear"]], {"clear": float('nan')})

def test_string_nonnumeric_costs() -> None:
    with pytest.raises(ValueError, match="must be numeric or None"):
        build_cost_map([["clear"]], {"clear": "1.0"}) # type: ignore