import math
from typing import List, Dict, Optional, Any

def build_cost_map(terrain_grid: Any, terrain_costs: Any) -> List[List[Optional[float]]]:
    """
    Converts a 2D grid of terrain string labels into a 2D grid of numeric traversal costs.
    
    Args:
        terrain_grid: A non-empty, rectangular 2D list of non-empty string terrain labels.
        terrain_costs: A mapping from string terrain labels to non-negative finite numeric 
                       costs, or None for impassable terrain.
                       
    Returns:
        A new 2D list of floating-point costs (or None) corresponding to the input grid.
        
    Raises:
        ValueError: If inputs are malformed, empty, ragged, contain invalid types (like bools), 
                    contain invalid numbers (NaN, inf, negative), or if a label is missing.
    """
    # 1. Validate the terrain_costs mapping
    if not isinstance(terrain_costs, dict) or not terrain_costs:
        raise ValueError("terrain_costs must be a non-empty dictionary mapping.")

    for key, value in terrain_costs.items():
        if not isinstance(key, str) or not key.strip():
            raise ValueError(f"terrain_costs keys must be non-empty strings, got: {key!r}")
        
        if value is not None:
            # Reject booleans explicitly (since Python treats bool as a subclass of int)
            if type(value) is bool:
                raise ValueError(f"Cost for '{key}' cannot be a boolean. Got: {value}")
            if not isinstance(value, (int, float)):
                raise ValueError(f"Cost for '{key}' must be numeric or None. Got type: {type(value).__name__}")
            try:
                numeric_cost = float(value)
            except (OverflowError, TypeError, ValueError):
                raise ValueError(
                    f"Cost for '{key}' must be a non-negative finite number. Got: {value}"
                ) from None

            if not math.isfinite(numeric_cost) or numeric_cost < 0:
                raise ValueError(
                    f"Cost for '{key}' must be a non-negative finite number. Got: {value}"
                )
    # 2. Validate the terrain_grid structure
    if not isinstance(terrain_grid, list) or not terrain_grid:
        raise ValueError("terrain_grid must be a non-empty list.")
    
    if not isinstance(terrain_grid[0], list) or not terrain_grid[0]:
        raise ValueError("terrain_grid must contain at least one row and one column.")

    cols = len(terrain_grid[0])
    result_grid = []

    # 3. Process the grid and validate cells
    for r_idx, row in enumerate(terrain_grid):
        if not isinstance(row, list):
            raise ValueError(f"Row {r_idx} is not a valid list.")
        if len(row) != cols:
            raise ValueError(f"Ragged grid: row {r_idx} has length {len(row)}, expected {cols}.")
        
        new_row = []
        for c_idx, label in enumerate(row):
            if not isinstance(label, str) or not label.strip():
                raise ValueError(f"Invalid terrain label at ({r_idx}, {c_idx}): must be a non-empty string.")
            
            if label not in terrain_costs:
                raise ValueError(f"Terrain label '{label}' at ({r_idx}, {c_idx}) is missing from terrain_costs mapping.")
            
            raw_cost = terrain_costs[label]
            # Ensure safe conversion to float if it's a valid integer, keeping None as None
            mapped_cost = float(raw_cost) if raw_cost is not None else None
            new_row.append(mapped_cost)
            
        result_grid.append(new_row)

    return result_grid