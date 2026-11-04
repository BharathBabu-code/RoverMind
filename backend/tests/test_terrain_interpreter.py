import pytest
from backend.app.services.terrain_interpreter import (
    interpret_concept,
    get_concept_priority,
    build_normalized_segmentation,
    DEFAULT_TERRAIN_COSTS
)
from backend.app.services.segmentation_contract import SegmentationResult


def test_interpret_concept_known_mappings():
    assert interpret_concept("rock") == "rocky"
    assert interpret_concept("boulder") == "rocky"
    assert interpret_concept("sand") == "loose"
    assert interpret_concept("loose sand") == "loose"
    assert interpret_concept("bedrock") == "clear"
    assert interpret_concept("crater") == "obstacle"
    assert interpret_concept("rover") == "obstacle"


def test_interpret_concept_unknown():
    assert interpret_concept("alien_artifact") == "unknown"
    assert interpret_concept("unknown_feature_xyz") == "unknown"


def test_concept_priority_ordering():
    # Obstacle (100) > rocky (70) > loose (50) > unknown (30) > clear (10)
    assert get_concept_priority("obstacle") > get_concept_priority("rock")
    assert get_concept_priority("rock") > get_concept_priority("sand")
    assert get_concept_priority("sand") > get_concept_priority("unknown_feature")
    assert get_concept_priority("unknown_feature") > get_concept_priority("clear")


def test_build_normalized_segmentation_success():
    raw_grid = [
        ["bedrock", "rock"],
        ["sand", "crater"]
    ]
    res = build_normalized_segmentation(raw_grid, 640, 480, "test-model")
    assert isinstance(res, SegmentationResult)
    assert res.terrain_grid == [
        ["clear", "rocky"],
        ["loose", "obstacle"]
    ]
    assert res.image_width == 640
    assert res.image_height == 480
    assert res.source_model == "test-model"


def test_default_terrain_costs_structure():
    assert DEFAULT_TERRAIN_COSTS["clear"] == 1.0
    assert DEFAULT_TERRAIN_COSTS["rocky"] == 3.0
    assert DEFAULT_TERRAIN_COSTS["loose"] == 5.0
    assert DEFAULT_TERRAIN_COSTS["obstacle"] is None  # Impassable
