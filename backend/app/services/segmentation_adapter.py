from typing import Any
from backend.app.services.segmentation_contract import SegmentationResult

def normalize_segmentation(
    region_grid: Any, 
    region_labels: Any, 
    image_width: Any, 
    image_height: Any, 
    source_model: Any
) -> SegmentationResult:
    """
    Converts a 2D grid of region IDs into a normalized SegmentationResult.
    
    Args:
        region_grid: A 2D list of non-negative integer region IDs.
        region_labels: A mapping from region ID (int) to normalized terrain label (str).
        image_width: Original image width in pixels.
        image_height: Original image height in pixels.
        source_model: Identifier for the segmentation model.
        
    Returns:
        A validated SegmentationResult containing the translated terrain string labels.
        
    Raises:
        ValueError: If grid or mapping structures are malformed, contain invalid types 
                    (like booleans or negative IDs), or if a region ID is unmapped.
    """
    # 1. Validate the region_labels mapping
    if not isinstance(region_labels, dict) or not region_labels:
        raise ValueError("region_labels must be a non-empty dictionary mapping.")
        
    for key, label in region_labels.items():
        if type(key) is bool or not isinstance(key, int) or key < 0:
            raise ValueError(f"Mapping keys must be non-negative integers, got {type(key).__name__} {key}")
        if not isinstance(label, str) or not label.strip():
            raise ValueError(f"Terrain labels must be non-empty strings, got {type(label).__name__}")

    # 2. Validate the region_grid structure
    if not isinstance(region_grid, list) or not region_grid:
        raise ValueError("region_grid must be a non-empty list.")
        
    if not isinstance(region_grid[0], list) or not region_grid[0]:
        raise ValueError("region_grid must contain at least one row and one column.")
        
    cols = len(region_grid[0])
    terrain_grid = []

    # 3. Process the grid and map to string labels
    for r_idx, row in enumerate(region_grid):
        if not isinstance(row, list):
            raise ValueError(f"Row {r_idx} is not a valid list.")
        if len(row) != cols:
            raise ValueError(f"Ragged grid: row {r_idx} has length {len(row)}, expected {cols}.")
            
        new_row = []
        for c_idx, cell in enumerate(row):
            if type(cell) is bool or not isinstance(cell, int) or cell < 0:
                raise ValueError(
                    f"Region ID at ({r_idx}, {c_idx}) must be a non-negative integer, got {type(cell).__name__}."
                )
            
            if cell not in region_labels:
                raise ValueError(
                    f"Region ID {cell} at ({r_idx}, {c_idx}) has no corresponding terrain label mapping."
                )
                
            new_row.append(region_labels[cell])
            
        terrain_grid.append(new_row)

    # 4. Construct and return the result 
    # (SegmentationResult handles metadata validation internally)
    return SegmentationResult(
        terrain_grid=terrain_grid,
        image_width=image_width,
        image_height=image_height,
        source_model=source_model
    )