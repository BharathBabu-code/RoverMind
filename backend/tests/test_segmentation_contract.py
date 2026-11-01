import pytest
import copy
from backend.app.services.segmentation_contract import SegmentationResult

# --- Success Path Tests ---

def test_valid_segmentation_result_creation() -> None:
    """Verifies that a valid result initializes correctly and preserves data."""
    grid = [
        ["clear", "rocky"],
        ["loose", "clear"]
    ]
    result = SegmentationResult(
        terrain_grid=grid,
        image_width=1920,
        image_height=1080,
        source_model="meta-sam-3.1-hackathon"
    )
    
    assert result.terrain_grid == grid
    assert result.image_width == 1920
    assert result.image_height == 1080
    assert result.source_model == "meta-sam-3.1-hackathon"

def test_valid_single_cell_grid() -> None:
    result = SegmentationResult([["rocky"]], 100, 100, "test-model")
    assert result.terrain_grid == [["rocky"]]

def test_valid_single_row_grid() -> None:
    result = SegmentationResult([["rocky", "clear", "loose"]], 300, 100, "test-model")
    assert len(result.terrain_grid) == 1
    assert len(result.terrain_grid[0]) == 3

def test_valid_single_column_grid() -> None:
    result = SegmentationResult([["rocky"], ["clear"], ["loose"]], 100, 300, "test-model")
    assert len(result.terrain_grid) == 3
    assert len(result.terrain_grid[0]) == 1

def test_no_mutation_of_original_grid() -> None:
    """Ensures the dataclass validation does not alter the input reference."""
    original_grid = [["clear", "rocky"]]
    grid_copy = copy.deepcopy(original_grid)
    
    SegmentationResult(original_grid, 1024, 768, "model-x")
    assert original_grid == grid_copy

# --- Validation Tests ---

def test_empty_grids() -> None:
    with pytest.raises(ValueError, match="non-empty list"):
        SegmentationResult([], 100, 100, "model")
        
def test_empty_rows() -> None:
    with pytest.raises(ValueError, match="at least one row and one column"):
        SegmentationResult([[]], 100, 100, "model")

def test_ragged_grids() -> None:
    grid = [
        ["clear", "clear"],
        ["clear"]
    ]
    with pytest.raises(ValueError, match="Ragged grid"):
        SegmentationResult(grid, 100, 100, "model")

def test_malformed_rows() -> None:
    with pytest.raises(ValueError, match="not a valid list"):
        SegmentationResult([["clear"], "not-a-list"], 100, 100, "model") # type: ignore

def test_invalid_terrain_labels() -> None:
    with pytest.raises(ValueError, match="must be a non-empty string"):
        SegmentationResult([["clear", "   "]], 100, 100, "model")
        
    with pytest.raises(ValueError, match="must be a non-empty string"):
        SegmentationResult([["clear", 123]], 100, 100, "model") # type: ignore

def test_invalid_image_dimensions() -> None:
    valid_grid = [["clear"]]
    
    # Zero or negative
    with pytest.raises(ValueError, match="must be a positive integer"):
        SegmentationResult(valid_grid, 0, 100, "model")
    with pytest.raises(ValueError, match="must be a positive integer"):
        SegmentationResult(valid_grid, 100, -5, "model")
        
    # Floats
    with pytest.raises(ValueError, match="must be a positive integer"):
        SegmentationResult(valid_grid, 100.5, 100, "model") # type: ignore
        
    # Booleans
    with pytest.raises(ValueError, match="must be a positive integer"):
        SegmentationResult(valid_grid, True, 100, "model") # type: ignore
    with pytest.raises(ValueError, match="must be a positive integer"):
        SegmentationResult(valid_grid, 100, False, "model") # type: ignore

def test_invalid_source_model() -> None:
    valid_grid = [["clear"]]
    
    with pytest.raises(ValueError, match="cannot be empty"):
        SegmentationResult(valid_grid, 100, 100, "")
        
    with pytest.raises(ValueError, match="cannot be empty"):
        SegmentationResult(valid_grid, 100, 100, "   ")
        
    with pytest.raises(ValueError, match="must be a string"):
        SegmentationResult(valid_grid, 100, 100, 123) # type: ignore

def test_result_is_independent_of_original_grid() -> None:
    original_grid = [["clear", "rocky"]]

    result = SegmentationResult(
        original_grid, 1024, 768, "model-x"
    )

    original_grid[0][0] = ""
    original_grid.append(["invalid"])

    assert result.terrain_grid == [["clear", "rocky"]]