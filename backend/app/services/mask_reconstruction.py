import math
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass


MAX_MASK_DIMENSION = 8192
MAX_MASK_PIXELS = 25_000_000


@dataclass
class DecodedMask:
    """Decoded mask representation aligned with original image coordinate space."""
    object_id: str
    concept: str
    width: int
    height: int
    raster: bytes
    bounds: Optional[Tuple[int, int, int, int]] = None  # (left, top, right, bottom) in pixel coordinates
    confidence: Optional[float] = None


def decode_and_align_mask(
    record: Any,
    concept: str,
    image_width: int,
    image_height: int
) -> Optional[DecodedMask]:
    """
    Decodes a SAM record using meta-sam-parser and determines its alignment
    in the source-media (image) coordinate space.
    
    Supports both half-open source-media pixel bounds and normalized (0..1) bounds.
    """
    import meta_sam_parser as sam

    target_type = getattr(sam, "SegmentationMaskRecord", None)
    if isinstance(target_type, type) and not isinstance(record, target_type):
        return None

    mask = getattr(record, "mask", None)
    if mask is None:
        return None

    m_width = getattr(mask, "width", None)
    m_height = getattr(mask, "height", None)

    if type(m_width) is bool or not isinstance(m_width, int) or m_width <= 0 or m_width > MAX_MASK_DIMENSION:
        return None
    if type(m_height) is bool or not isinstance(m_height, int) or m_height <= 0 or m_height > MAX_MASK_DIMENSION:
        return None
    if (m_width * m_height) > MAX_MASK_PIXELS:
        return None

    try:
        raster = sam.decode_mask_to_raster(mask)
    except Exception:
        return None

    if len(raster) != m_width * m_height:
        return None

    object_id = str(getattr(record, "object_id", "unknown_object"))
    confidence = getattr(record, "confidence", None)
    if confidence is not None:
        try:
            confidence = float(confidence)
            if not math.isfinite(confidence):
                confidence = None
        except (ValueError, TypeError):
            confidence = None

    # Parse and validate bounds
    raw_bounds = getattr(record, "bounds", None)
    bounds_pixels = None

    if raw_bounds is not None:
        left = getattr(raw_bounds, "left", None)
        top = getattr(raw_bounds, "top", None)
        right = getattr(raw_bounds, "right", None)
        bottom = getattr(raw_bounds, "bottom", None)

        if all(isinstance(v, (int, float)) and math.isfinite(v) for v in (left, top, right, bottom)):
            # Check if bounds are normalized (all between 0.0 and 1.0)
            if 0.0 <= left <= 1.0 and 0.0 <= right <= 1.0 and 0.0 <= top <= 1.0 and 0.0 <= bottom <= 1.0 and (right > left or bottom > top):
                x0 = int(round(left * image_width))
                y0 = int(round(top * image_height))
                x1 = int(round(right * image_width))
                y1 = int(round(bottom * image_height))
            else:
                # Absolute pixel coordinates
                x0 = int(round(left))
                y0 = int(round(top))
                x1 = int(round(right))
                y1 = int(round(bottom))

            # Clamp to image boundaries
            x0 = max(0, min(image_width, x0))
            y0 = max(0, min(image_height, y0))
            x1 = max(0, min(image_width, x1))
            y1 = max(0, min(image_height, y1))

            if x1 > x0 and y1 > y0:
                bounds_pixels = (x0, y0, x1, y1)

    if bounds_pixels is None:
        # Default full-frame bounds if bounds omitted or degenerate
        bounds_pixels = (0, 0, image_width, image_height)

    return DecodedMask(
        object_id=object_id,
        concept=concept,
        width=m_width,
        height=m_height,
        raster=raster,
        bounds=bounds_pixels,
        confidence=confidence
    )


def reconstruct_grid_from_masks(
    masks: List[DecodedMask],
    image_width: int,
    image_height: int,
    grid_rows: int,
    grid_cols: int,
    concept_priorities: Dict[str, int],
    default_concept: str = "clear"
) -> List[List[str]]:
    """
    Projects all decoded masks onto a discrete (grid_rows x grid_cols) spatial grid.
    
    Overlaps are resolved deterministically using concept_priorities (higher priority wins).
    Uncovered cells receive default_concept (e.g. 'clear' when masks exist, 'unknown' if no masks detected).
    """
    grid = [[default_concept for _ in range(grid_cols)] for _ in range(grid_rows)]
    priority_grid = [[-1 for _ in range(grid_cols)] for _ in range(grid_rows)]

    cell_w = image_width / grid_cols
    cell_h = image_height / grid_rows

    for mask in masks:
        prio = concept_priorities.get(mask.concept.lower(), 0)
        bx0, by0, bx1, by1 = mask.bounds or (0, 0, image_width, image_height)
        bw = bx1 - bx0
        bh = by1 - by0

        if bw <= 0 or bh <= 0:
            continue

        # Find overlapping grid cells
        min_c = max(0, int(bx0 // cell_w))
        max_c = min(grid_cols, int(math.ceil(bx1 / cell_w)))
        min_r = max(0, int(by0 // cell_h))
        max_r = min(grid_rows, int(math.ceil(by1 / cell_h)))

        for r in range(min_r, max_r):
            # Center of the grid cell in image coordinates
            cy = (r + 0.5) * cell_h
            if not (by0 <= cy < by1):
                continue

            # Map cell center Y to mask local Y
            local_y = int(((cy - by0) / bh) * mask.height)
            if not (0 <= local_y < mask.height):
                continue

            row_offset = local_y * mask.width

            for c in range(min_c, max_c):
                cx = (c + 0.5) * cell_w
                if not (bx0 <= cx < bx1):
                    continue

                # Map cell center X to mask local X
                local_x = int(((cx - bx0) / bw) * mask.width)
                if not (0 <= local_x < mask.width):
                    continue

                # Check if foreground in raster
                if mask.raster[row_offset + local_x] == 1:
                    if prio > priority_grid[r][c]:
                        priority_grid[r][c] = prio
                        grid[r][c] = mask.concept

    return grid
