import pytest
from backend.app.services.mask_reconstruction import (
    DecodedMask,
    reconstruct_grid_from_masks,
    decode_and_align_mask
)


def test_reconstruct_grid_empty_masks():
    grid = reconstruct_grid_from_masks(
        masks=[],
        image_width=100,
        image_height=100,
        grid_rows=4,
        grid_cols=4,
        concept_priorities={"rock": 70}
    )
    assert len(grid) == 4
    assert len(grid[0]) == 4
    # All cells should default to clear
    assert all(cell == "clear" for row in grid for cell in row)


def test_reconstruct_grid_single_mask():
    # 2x2 raster with foreground in cell (0, 0)
    raster = bytes([1, 1, 1, 1])
    mask = DecodedMask(
        object_id="obj_1",
        concept="rock",
        width=2,
        height=2,
        raster=raster,
        bounds=(0, 0, 50, 50),
        confidence=0.95
    )

    grid = reconstruct_grid_from_masks(
        masks=[mask],
        image_width=100,
        image_height=100,
        grid_rows=2,
        grid_cols=2,
        concept_priorities={"rock": 70}
    )

    # Cell (0, 0) is covered by mask, others are clear
    assert grid[0][0] == "rock"
    assert grid[0][1] == "clear"
    assert grid[1][0] == "clear"
    assert grid[1][1] == "clear"


def test_reconstruct_grid_overlapping_priority():
    # Mask 1: loose sand over (0, 0, 100, 100) (priority 50)
    # Mask 2: rock over (0, 0, 100, 100) (priority 70)
    all_fg = bytes([1] * 4)
    mask1 = DecodedMask("m1", "sand", 2, 2, all_fg, (0, 0, 100, 100))
    mask2 = DecodedMask("m2", "rock", 2, 2, all_fg, (0, 0, 100, 100))

    grid = reconstruct_grid_from_masks(
        masks=[mask1, mask2],
        image_width=100,
        image_height=100,
        grid_rows=2,
        grid_cols=2,
        concept_priorities={"sand": 50, "rock": 70}
    )

    # Higher priority (rock, 70) must win
    assert all(cell == "rock" for row in grid for cell in row)
