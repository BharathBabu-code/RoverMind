import pytest
import copy
from backend.app.services.segmentation_adapter import normalize_segmentation
from backend.app.services.segmentation_contract import SegmentationResult

# --- Success Path Tests ---

def test_successful_conversion_of_region_ids() -> None:
    region_grid = [
        [0, 0, 1, 1],
        [0, 2, 2, 1],
        [0, 0, 1, 1]
    ]
    region_labels = {
        0: "clear",
        1: "rocky",
        2: "loose"
    }
    
    result = normalize_segmentation(region_grid, region_labels, 1920, 1080, "test-model")
    
    expected_grid = [
        ["clear", "clear", "rocky", "rocky"],
        ["clear", "loose", "loose", "rocky"],
        ["clear", "clear", "rocky", "rocky"]
    ]
    
    assert isinstance(result, SegmentationResult)
    assert result.terrain_grid == expected_grid
    assert result.image_width == 1920
    assert result.image_height == 1080
    assert result.source_model == "test-model"

def test_single_cell_grid() -> None:
    result = normalize_segmentation([[5]], {5: "rocky"}, 100, 100, "test")
    assert result.terrain_grid == [["rocky"]]

def test_single_row_grid() -> None:
    result = normalize_segmentation([[0, 1, 0]], {0: "clear", 1: "rocky"}, 100, 100, "test")
    assert result.terrain_grid == [["clear", "rocky", "clear"]]

def test_single_column_grid() -> None:
    result = normalize_segmentation([[0], [1], [0]], {0: "clear", 1: "rocky"}, 100, 100, "test")
    assert result.terrain_grid == [["clear"], ["rocky"], ["clear"]]

def test_no_mutation_of_inputs() -> None:
    grid = [[0, 1]]
    labels = {0: "clear", 1: "rocky"}
    grid_copy = copy.deepcopy(grid)
    labels_copy = copy.deepcopy(labels)
    
    _ = normalize_segmentation(grid, labels, 100, 100, "test")
    
    assert grid == grid_copy
    assert labels == labels_copy

# --- Grid Validation Tests ---

def test_empty_region_grid() -> None:
    with pytest.raises(ValueError, match="non-empty list"):
        normalize_segmentation([], {0: "clear"}, 100, 100, "test")

def test_empty_rows() -> None:
    with pytest.raises(ValueError, match="at least one row and one column"):
        normalize_segmentation([[]], {0: "clear"}, 100, 100, "test")

def test_ragged_grid() -> None:
    with pytest.raises(ValueError, match="Ragged grid"):
        normalize_segmentation([[0, 0], [0]], {0: "clear"}, 100, 100, "test")

def test_invalid_region_grid_types() -> None:
    with pytest.raises(ValueError, match="is not a valid list"):
        normalize_segmentation([[0], "not-a-list"], {0: "clear"}, 100, 100, "test") # type: ignore

def test_negative_region_ids() -> None:
    with pytest.raises(ValueError, match="non-negative integer"):
        normalize_segmentation([[-1]], {-1: "clear"}, 100, 100, "test")

def test_float_region_ids() -> None:
    with pytest.raises(ValueError, match="non-negative integer"):
        normalize_segmentation([[1.5]], {1.5: "clear"}, 100, 100, "test") # type: ignore

def test_boolean_region_ids() -> None:
    with pytest.raises(ValueError, match="non-negative integer"):
        normalize_segmentation([[True]], {1: "clear"}, 100, 100, "test") # type: ignore
    with pytest.raises(ValueError, match="non-negative integer"):
        normalize_segmentation([[False]], {0: "clear"}, 100, 100, "test") # type: ignore

# --- Mapping Validation Tests ---

def test_empty_mapping() -> None:
    with pytest.raises(ValueError, match="non-empty dictionary mapping"):
        normalize_segmentation([[0]], {}, 100, 100, "test")

def test_invalid_mapping_type() -> None:
    with pytest.raises(ValueError, match="non-empty dictionary mapping"):
        normalize_segmentation([[0]], ["clear"], 100, 100, "test") # type: ignore

def test_missing_region_id_mapping() -> None:
    with pytest.raises(ValueError, match="no corresponding terrain label mapping"):
        normalize_segmentation([[0, 1]], {0: "clear"}, 100, 100, "test")

def test_invalid_mapping_keys() -> None:
    with pytest.raises(ValueError, match="non-negative integers"):
        normalize_segmentation([[0]], {"0": "clear"}, 100, 100, "test") # type: ignore

def test_boolean_mapping_keys() -> None:
    with pytest.raises(ValueError, match="non-negative integers"):
        normalize_segmentation([[0]], {False: "clear"}, 100, 100, "test") # type: ignore

def test_empty_or_non_string_terrain_labels() -> None:
    with pytest.raises(ValueError, match="non-empty strings"):
        normalize_segmentation([[0]], {0: "   "}, 100, 100, "test")
    with pytest.raises(ValueError, match="non-empty strings"):
        normalize_segmentation([[0]], {0: 123}, 100, 100, "test") # type: ignore

# --- Metadata Delegation Tests ---

def test_invalid_metadata_rejected_by_segmentation_result() -> None:
    # Ensure that malformed metadata passed through the adapter triggers the dataclass post_init
    valid_grid = [[0]]
    valid_labels = {0: "clear"}
    
    with pytest.raises(ValueError, match="must be a positive integer"):
        normalize_segmentation(valid_grid, valid_labels, -5, 100, "test")
        
    with pytest.raises(ValueError, match="must be a string"):
        normalize_segmentation(valid_grid, valid_labels, 100, 100, 42) # type: ignore