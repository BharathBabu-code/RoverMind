from typing import Dict, List, Tuple, Optional
from backend.app.services.segmentation_adapter import normalize_segmentation
from backend.app.services.segmentation_contract import SegmentationResult

# Canonical normalized terrain labels supported by RoverMind
CANONICAL_TERRAIN_LABELS = {
    "clear",
    "rocky",
    "loose",
    "obstacle",
    "unknown"
}

# Standard concept-to-terrain mapping rules
# Visual concepts detected by AI models are mapped explicitly to normalized operational labels
CONCEPT_TO_TERRAIN_MAP: Dict[str, str] = {
    # Rocky terrain
    "rock": "rocky",
    "rocks": "rocky",
    "boulder": "rocky",
    "boulders": "rocky",
    "stone": "rocky",
    "stones": "rocky",
    "outcrop": "rocky",
    "bedrock outcrop": "rocky",

    # Loose / slippery / soft ground
    "loose": "loose",
    "loose sand": "loose",
    "sand": "loose",
    "dune": "loose",
    "drift": "loose",
    "sand drift": "loose",
    "ripple": "loose",

    # Clear / traversable ground
    "clear": "clear",
    "bedrock": "clear",
    "flat ground": "clear",
    "hard ground": "clear",
    "soil": "clear",
    "firm soil": "clear",
    "terrain": "clear",
    "smooth": "clear",

    # Obstacles / severe hazards / rover body parts
    "obstacle": "obstacle",
    "crater": "obstacle",
    "crater rim": "obstacle",
    "cliff": "obstacle",
    "dropoff": "obstacle",
    "rover": "obstacle",
    "wheel": "obstacle",
    "chassis": "obstacle",
    "solar panel": "obstacle",
    "shadow": "unknown",
}

# Deterministic hazard priority (higher value overrides lower value in case of overlap)
TERRAIN_PRIORITY: Dict[str, int] = {
    "obstacle": 100,  # Safety first: impassable features take precedence
    "rocky": 70,     # Elevated traversal cost
    "loose": 50,     # Moderately elevated traversal cost
    "unknown": 30,   # Unclassified features
    "clear": 10      # Baseline ground
}

DEFAULT_TERRAIN_COSTS: Dict[str, Optional[float]] = {
    "clear": 1.0,
    "rocky": 3.0,
    "loose": 5.0,
    "unknown": 2.0,
    "obstacle": None  # Impassable
}


def interpret_concept(concept: str) -> str:
    """
    Translates a visual concept string into a normalized terrain label.
    Returns 'unknown' if the concept is unmapped.
    """
    normalized_key = concept.strip().lower()
    return CONCEPT_TO_TERRAIN_MAP.get(normalized_key, "unknown")


def get_concept_priority(concept: str) -> int:
    """Returns the priority score for a visual concept based on its mapped terrain label."""
    label = interpret_concept(concept)
    return TERRAIN_PRIORITY.get(label, 10)


def build_normalized_segmentation(
    raw_concept_grid: List[List[str]],
    image_width: int,
    image_height: int,
    source_model: str
) -> SegmentationResult:
    """
    Converts a grid of concept strings into a normalized SegmentationResult
    using the existing normalize_segmentation adapter and contract.
    """
    # 1. Translate each cell's concept to normalized terrain label
    # 2. Assign unique region IDs to distinct terrain labels
    label_to_id: Dict[str, int] = {}
    id_to_label: Dict[int, str] = {}
    
    current_id = 0
    for label in sorted(CANONICAL_TERRAIN_LABELS):
        label_to_id[label] = current_id
        id_to_label[current_id] = label
        current_id += 1

    region_grid: List[List[int]] = []
    for row in raw_concept_grid:
        int_row = []
        for cell in row:
            terrain_label = interpret_concept(cell)
            int_row.append(label_to_id[terrain_label])
        region_grid.append(int_row)

    # Invoke the project's existing segmentation adapter
    return normalize_segmentation(
        region_grid=region_grid,
        region_labels=id_to_label,
        image_width=image_width,
        image_height=image_height,
        source_model=source_model
    )
