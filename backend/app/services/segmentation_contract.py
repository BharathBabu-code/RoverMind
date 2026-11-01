from dataclasses import dataclass
from typing import List

@dataclass
class SegmentationResult:
    """
    A provider-independent data contract for image segmentation results.
    
    This structure ensures that any upstream segmentation provider (such as Meta's models)
    delivers a consistent, validated representation of the terrain before it is passed 
    to the cost-mapping or pathfinding engines.
    """
    terrain_grid: List[List[str]]
    image_width: int
    image_height: int
    source_model: str

    def __post_init__(self) -> None:
        """
        Validates the contract immediately upon instantiation.
        Raises ValueError if any field violates the strict type or structural constraints.
        """
        # 1. Validate image dimensions
        for dim_name, dim_val in [("image_width", self.image_width), ("image_height", self.image_height)]:
            # Explicitly reject booleans since Python treats bool as a subclass of int
            if type(dim_val) is bool or not isinstance(dim_val, int):
                raise ValueError(f"{dim_name} must be a positive integer, got {type(dim_val).__name__}.")
            if dim_val <= 0:
                raise ValueError(f"{dim_name} must be a positive integer, got {dim_val}.")

        # 2. Validate source_model
        if not isinstance(self.source_model, str):
            raise ValueError(f"source_model must be a string, got {type(self.source_model).__name__}.")
        if not self.source_model.strip():
            raise ValueError("source_model cannot be empty or whitespace-only.")

        # 3. Validate terrain_grid
        if not isinstance(self.terrain_grid, list) or not self.terrain_grid:
            raise ValueError("terrain_grid must be a non-empty list.")
        
        if not isinstance(self.terrain_grid[0], list) or not self.terrain_grid[0]:
            raise ValueError("terrain_grid must contain at least one row and one column.")

        cols = len(self.terrain_grid[0])
        
        for r_idx, row in enumerate(self.terrain_grid):
            if not isinstance(row, list):
                raise ValueError(f"Row {r_idx} is not a valid list.")
            if len(row) != cols:
                raise ValueError(f"Ragged grid: row {r_idx} has length {len(row)}, expected {cols}.")
            
            for c_idx, label in enumerate(row):
                if not isinstance(label, str) or not label.strip():
                    raise ValueError(
                        f"Invalid terrain label at ({r_idx}, {c_idx}): must be a non-empty string."
                    )
                # Store a defensive copy so external changes to the input
        # grid cannot invalidate this result after construction.
        self.terrain_grid = [row.copy() for row in self.terrain_grid]