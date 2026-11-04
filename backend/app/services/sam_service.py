import math
import httpx
from typing import List, Tuple, Dict, Any, Optional

from backend.app.core.config import settings
from backend.app.core.telemetry import api_telemetry
from backend.app.core.budget import RequestBudget
from backend.app.core.sanitizer import sanitize_error
from backend.app.services.mask_reconstruction import (
    DecodedMask,
    decode_and_align_mask,
    reconstruct_grid_from_masks
)
from backend.app.services.terrain_interpreter import (
    get_concept_priority,
    build_normalized_segmentation,
    interpret_concept
)
from backend.app.services.segmentation_contract import SegmentationResult
from backend.app.schemas.models import MaskRecordDto

META_API_BASE_URL = "https://api.meta.ai/v1"


def run_live_sam_segmentation(
    image_data_url: str,
    concepts: List[str],
    image_width: int,
    image_height: int,
    grid_rows: int,
    grid_cols: int,
    budget: Optional[RequestBudget] = None
) -> Tuple[SegmentationResult, List[MaskRecordDto], List[str]]:
    """
    Executes visual segmentation against the Meta SAM 3.1 API.
    Guarded by:
    1. Global Kill Switch (EXTERNAL_API_ENABLED=false blocks all calls).
    2. Dry-Run Mode (EXTERNAL_API_DRY_RUN=true returns validated simulated segmentation without requiring keys).
    3. Operation Request Budget (tracked across the full analysis).
    4. Concurrency Semaphore (MAX_CONCURRENT_SAM_REQUESTS).
    5. Zero automatic retries (MAX_RETRIES=0) and explicit HTTP timeouts.
    6. Centralized Error Sanitization before telemetry and persistent ledger storage.
    """
    # 1. Global Kill Switch Check (must occur before any client creation or budget consumption)
    if not settings.external_api_enabled:
        api_telemetry.record_sam_blocked("Blocked by kill switch: EXTERNAL_API_ENABLED is False")
        raise RuntimeError("External API calls are disabled via EXTERNAL_API_ENABLED kill switch. Live SAM segmentation is blocked.")

    # 2. Dry-Run Mode Execution (Validates parameters locally without requiring API key)
    if settings.external_api_dry_run:
        api_telemetry.record_sam_dry_run()
        seg_res, masks, diags = generate_synthetic_offline_segmentation(
            image_width=image_width,
            image_height=image_height,
            grid_rows=grid_rows,
            grid_cols=grid_cols
        )
        diags.insert(0, "[DRY RUN] Meta SAM 3.1 request validated without external network transmission.")
        return seg_res, masks, diags

    # 3. Credential Verification for Live Mode
    if not settings.is_meta_api_configured or not settings.meta_api_key:
        raise RuntimeError("META_API_KEY is not configured in the environment. Live SAM segmentation is unavailable.")

    # 4. Initialize or bind per-operation Request Budget
    active_budget = budget or RequestBudget(settings.max_sam_requests_per_analysis, operation_name="sam_segmentation")

    # 5. Concurrency Semaphore Guard
    acquired = api_telemetry.sam_semaphore.acquire(timeout=settings.connect_timeout_seconds)
    if not acquired:
        err_msg = "SAM request concurrency cap reached."
        api_telemetry.record_sam_concurrency_rejected(err_msg)
        raise RuntimeError(f"SAM request concurrency limit exceeded ({settings.max_concurrent_sam_requests} max). Please retry shortly.")

    try:
        import openai
        import meta_sam_parser as sam

        client = openai.OpenAI(
            base_url=settings.meta_api_base_url,
            api_key=settings.meta_api_key,
            timeout=httpx.Timeout(settings.read_timeout_seconds, connect=settings.connect_timeout_seconds),
            max_retries=settings.max_retries
        )

        all_decoded_masks: List[DecodedMask] = []
        mask_dtos: List[MaskRecordDto] = []
        diagnostics: List[str] = []

        valid_concepts = [c.strip() for c in concepts if c.strip()]
        if not valid_concepts:
            valid_concepts = ["rock"]

        # Safety-First Prioritization: Sort concepts by hazard priority so high-risk concepts (obstacles, rocks)
        # are evaluated first when the request budget is bounded.
        valid_concepts.sort(key=lambda c: get_concept_priority(c), reverse=True)

        for concept in valid_concepts:
            prompt = concept.strip()
            if not prompt:
                continue

            # Check and consume request budget BEFORE attempting external API call
            if not active_budget.record_request():
                exhaust_msg = (
                    f"Budget enforcement: Request budget exhausted ({active_budget.limit} limit reached). "
                    f"Skipping concept '{prompt}'."
                )
                api_telemetry.record_sam_budget_exhausted(exhaust_msg)
                diagnostics.append(exhaust_msg)
                break

            try:
                api_telemetry.record_sam_start()
                response = client.responses.create(
                    model="sam-3.1",
                    input=[
                        {
                            "type": "message",
                            "role": "user",
                            "content": [
                                {"type": "input_text", "text": prompt},
                                {"type": "input_image", "image_url": image_data_url},
                            ],
                        },
                    ],
                )
            except Exception as e:
                sanitized_err = sanitize_error(e)
                api_telemetry.record_sam_failure(sanitized_err, was_started=True)
                diagnostics.append(f"API request failed for concept '{prompt}': {sanitized_err}")
                continue

            # Extract response text safely
            response_text = ""
            if hasattr(response, "output_text") and response.output_text is not None:
                response_text = response.output_text
            elif hasattr(response, "output") and response.output:
                try:
                    response_text = response.output[0].content[0].text
                except (IndexError, AttributeError):
                    pass

            if not response_text:
                err_msg = f"No response text received for concept '{prompt}'"
                api_telemetry.record_sam_failure(err_msg, was_started=True)
                diagnostics.append(err_msg)
                continue

            # Parse tokenized stream using meta-sam-parser
            try:
                response_format = sam.image_segmentation_format()
                parser = response_format.create_parser()
                parser.push(response_text)
                finished = parser.finish(sam.CompletedOutcome())
                result = finished.result
                api_telemetry.record_sam_success()
            except Exception as e:
                sanitized_err = sanitize_error(e)
                api_telemetry.record_sam_failure(f"Parser failed for '{prompt}': {sanitized_err}", was_started=True)
                diagnostics.append(f"Parser failed on tokens for concept '{prompt}': {sanitized_err}")
                continue

            records = getattr(result, "records", [])
            target_type = getattr(sam, "SegmentationMaskRecord", None)
            if isinstance(target_type, type):
                mask_records = [r for r in records if isinstance(r, target_type)]
            else:
                mask_records = records

            for r in mask_records:
                try:
                    decoded = decode_and_align_mask(r, prompt, image_width, image_height)
                except Exception as dec_err:
                    diagnostics.append(f"Warning: Failed to decode individual mask record: {sanitize_error(dec_err)}")
                    decoded = None

                if decoded is not None:
                    all_decoded_masks.append(decoded)
                    
                    fg_pixels = sum(decoded.raster)
                    bx0, by0, bx1, by1 = decoded.bounds or (0, 0, image_width, image_height)
                    
                    mask_dtos.append(
                        MaskRecordDto(
                            object_id=decoded.object_id,
                            concept=prompt,
                            bounds={"left": bx0, "top": by0, "right": bx1, "bottom": by1},
                            area_pixels=fg_pixels,
                            confidence=decoded.confidence
                        )
                    )

        # Reconstruct discrete spatial grid with uncertainty semantics
        concept_priorities = {c: get_concept_priority(c) for c in valid_concepts}
        if not all_decoded_masks:
            diagnostics.append(
                "Zero usable segmentation masks detected from SAM; preserving uncertainty semantics with unclassified 'unknown' terrain."
            )
            raw_grid = reconstruct_grid_from_masks(
                masks=all_decoded_masks,
                image_width=image_width,
                image_height=image_height,
                grid_rows=grid_rows,
                grid_cols=grid_cols,
                concept_priorities=concept_priorities,
                default_concept="unknown"
            )
        else:
            raw_grid = reconstruct_grid_from_masks(
                masks=all_decoded_masks,
                image_width=image_width,
                image_height=image_height,
                grid_rows=grid_rows,
                grid_cols=grid_cols,
                concept_priorities=concept_priorities,
                default_concept="clear"
            )

        # Translate through normalized segmentation contract
        seg_result = build_normalized_segmentation(
            raw_concept_grid=raw_grid,
            image_width=image_width,
            image_height=image_height,
            source_model="sam-3.1"
        )

        return seg_result, mask_dtos, diagnostics

    finally:
        api_telemetry.sam_semaphore.release()


def generate_synthetic_offline_segmentation(
    image_width: int,
    image_height: int,
    grid_rows: int,
    grid_cols: int
) -> Tuple[SegmentationResult, List[MaskRecordDto], List[str]]:
    """
    Generates a labelled SYNTHETIC terrain grid for offline demonstration and testing.
    This does NOT represent real SAM model output and is explicitly marked as synthetic.
    """
    grid: List[List[str]] = [["clear" for _ in range(grid_cols)] for _ in range(grid_rows)]
    masks: List[MaskRecordDto] = []
    diagnostics: List[str] = [
        "Offline demonstration mode: Synthetic terrain layout generated for navigation demonstration."
    ]

    # Upper third: Rocky outcrops and boulders
    for r in range(grid_rows // 3):
        for c in range(grid_cols):
            if (r + c) % 4 == 0:
                grid[r][c] = "obstacle"
            elif (r + c) % 3 == 0:
                grid[r][c] = "rocky"

    # Middle third: Mix of sand drifts and navigable corridor
    for r in range(grid_rows // 3, 2 * grid_rows // 3):
        for c in range(grid_cols):
            if c in (grid_cols // 2 - 1, grid_cols // 2) and r not in (grid_rows // 2 - 1, grid_rows // 2):
                grid[r][c] = "obstacle"
            elif (r * c) % 5 == 0:
                grid[r][c] = "loose"

    # Lower third: Mostly clear path with isolated loose patches
    for r in range(2 * grid_rows // 3, grid_rows):
        for c in range(grid_cols):
            if (r + c) % 7 == 0:
                grid[r][c] = "loose"
            elif r == grid_rows - 1 and c == grid_cols - 1:
                grid[r][c] = "rocky"

    # Add synthetic mask records representing detected regions
    masks.append(
        MaskRecordDto(
            object_id="synth-rocky-outcrop-01",
            concept="rocky",
            bounds={"left": 0, "top": 0, "right": image_width, "bottom": image_height // 3},
            area_pixels=int(image_width * image_height * 0.25),
            confidence=0.92
        )
    )
    masks.append(
        MaskRecordDto(
            object_id="synth-obstacle-ridge-02",
            concept="obstacle",
            bounds={
                "left": int(image_width * 0.45),
                "top": int(image_height * 0.33),
                "right": int(image_width * 0.55),
                "bottom": int(image_height * 0.67)
            },
            area_pixels=int(image_width * image_height * 0.15),
            confidence=0.95
        )
    )
    masks.append(
        MaskRecordDto(
            object_id="synth-sand-drift-03",
            concept="loose",
            bounds={
                "left": int(image_width * 0.1),
                "top": int(image_height * 0.4),
                "right": int(image_width * 0.4),
                "bottom": int(image_height * 0.6)
            },
            area_pixels=int(image_width * image_height * 0.12),
            confidence=0.88
        )
    )

    seg_result = build_normalized_segmentation(
        raw_concept_grid=grid,
        image_width=image_width,
        image_height=image_height,
        source_model="offline-synthetic-fixture"
    )

    return seg_result, masks, diagnostics
