from fastapi import APIRouter
from backend.app.core.config import settings
from backend.app.core.telemetry import api_telemetry
from backend.app.schemas.models import HealthResponse, ConfigStatusResponse

router = APIRouter(tags=["Health & Status"])


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """Diagnostic endpoint to verify that the RoverMind API backend is alive."""
    return HealthResponse(
        status="ok",
        service="RoverMind API",
        version="0.1.0"
    )


@router.get("/config", response_model=ConfigStatusResponse)
async def get_config_status() -> ConfigStatusResponse:
    """Returns AI model configuration status without leaking sensitive credentials."""
    sam_configured = settings.is_meta_api_configured
    reasoning_configured = settings.is_reasoning_api_configured
    offline = not sam_configured and not reasoning_configured
    telemetry = api_telemetry.get_telemetry_summary()

    if not settings.external_api_enabled:
        msg = "EXTERNAL INFERENCE DISABLED (Kill Switch active: EXTERNAL_API_ENABLED=false). Operating in 100% offline verified mode."
    elif settings.external_api_dry_run:
        msg = f"DRY RUN MODE ACTIVE (EXTERNAL_API_DRY_RUN=true). Validating API flow with simulated responses (provider: {settings.reasoning_provider})."
    elif sam_configured and reasoning_configured:
        msg = f"Dual Meta AI credentials detected: SAM 3.1 visual perception and {settings.meta_reasoning_model} reasoning."
    elif sam_configured and not reasoning_configured:
        msg = "Meta SAM 3.1 credentials detected; reasoning layer operating in deterministic offline mode."
    elif not sam_configured and reasoning_configured:
        msg = f"SAM 3.1 operating in synthetic demonstration mode; Meta reasoning ({settings.meta_reasoning_model}) credentials detected."
    else:
        msg = "Operating in 100% offline demonstration mode with synthetic segmentation fixtures and deterministic reasoning engine."

    return ConfigStatusResponse(
        is_meta_api_configured=sam_configured,
        meta_model="sam-3.1",
        is_reasoning_api_configured=reasoning_configured,
        reasoning_model=settings.meta_reasoning_model,
        offline_mode=offline,
        message=msg,
        external_api_enabled=settings.external_api_enabled,
        external_api_dry_run=settings.external_api_dry_run,
        reasoning_provider=settings.reasoning_provider,
        muse_spark_model=settings.muse_spark_model,
        llama_model=settings.llama_model,
        provider_provenance=telemetry.get("provider_provenance", "EXTERNAL INFERENCE DISABLED"),
        sam_status=telemetry["sam_status"],
        sam_last_verified=telemetry["sam_last_verified"],
        reasoning_status=telemetry["reasoning_status"],
        reasoning_last_verified=telemetry["reasoning_last_verified"],
        active_segmentation_source=telemetry["active_segmentation_source"],
        active_reasoning_source=telemetry["active_reasoning_source"],
        ledger=telemetry.get("ledger")
    )
