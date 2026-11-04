from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Query

from backend.app.schemas.models import (
    MissionContextDto,
    MissionBriefing,
    ChatRequest,
    ChatResponse,
    RouteComparisonRequest,
    RouteComparisonResponse
)
from backend.app.services.mission_context import get_analysis, build_mission_context
from backend.app.services.mission_tools import tool_compare_routes
from backend.app.services.reasoning_service import (
    generate_live_mission_briefing,
    generate_deterministic_briefing,
    process_chat_turn,
    get_conversation_history
)
from backend.app.core.config import settings

router = APIRouter(prefix="/mission", tags=["Mission Intelligence & Reasoning"])


@router.get("/capabilities", response_model=Dict[str, Any])
async def get_mission_capabilities() -> Dict[str, Any]:
    """Returns AI model status, available tools, and runtime configurations."""
    from backend.app.core.telemetry import api_telemetry
    return {
        "external_api_enabled": settings.external_api_enabled,
        "external_api_dry_run": settings.external_api_dry_run,
        "visual_segmentation": {
            "model": "sam-3.1",
            "is_configured": settings.is_meta_api_configured,
            "mode": (
                "disabled" if not settings.external_api_enabled
                else ("dry-run" if settings.external_api_dry_run
                      else ("live" if settings.is_meta_api_configured else "offline-synthetic"))
            )
        },
        "mission_reasoning": {
            "provider": settings.reasoning_provider,
            "primary_model": settings.muse_spark_model,
            "fallback_model": settings.llama_model,
            "model": settings.meta_reasoning_model,
            "is_configured": settings.is_reasoning_api_configured,
            "mode": api_telemetry.get_reasoning_provenance()
        },
        "available_tools": [
            "get_mission_summary",
            "get_terrain_distribution",
            "get_region_details",
            "get_route_metrics",
            "compare_routes",
            "get_analysis_diagnostics"
        ]
    }


@router.get("/{image_id}/context", response_model=MissionContextDto)
async def get_active_mission_context(image_id: str) -> MissionContextDto:
    """Retrieves structured, bounded telemetry context for an active mission image."""
    analysis = get_analysis(image_id)
    if not analysis:
        raise HTTPException(
            status_code=404,
            detail=f"Active mission context for image '{image_id}' not found. Please analyze an image first."
        )
    return build_mission_context(analysis)


@router.get("/{image_id}/briefing", response_model=MissionBriefing)
async def get_or_generate_briefing(
    image_id: str,
    force_deterministic: bool = Query(default=False)
) -> MissionBriefing:
    """
    Returns an observation briefing for the active mission.
    Uses the Meta reasoning model when configured; falls back deterministically.
    """
    analysis = get_analysis(image_id)
    if not analysis:
        raise HTTPException(
            status_code=404,
            detail=f"Active mission for image '{image_id}' not found. Please run analysis first."
        )

    try:
        if force_deterministic:
            return generate_deterministic_briefing(image_id)
        return generate_live_mission_briefing(image_id)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception:
        # Guarantee non-crashing fallback
        return generate_deterministic_briefing(image_id)


@router.post("/{image_id}/briefing/generate", response_model=MissionBriefing)
async def generate_briefing_post(image_id: str) -> MissionBriefing:
    """Explicitly triggers generation of a fresh mission observation briefing."""
    return await get_or_generate_briefing(image_id, force_deterministic=False)


@router.post("/chat", response_model=ChatResponse)
async def submit_chat_message(request: ChatRequest) -> ChatResponse:
    """
    Submits an operator question to the contextual mission chatbot.
    Queries verified backend data using controlled tools with mission isolation.
    """
    try:
        return process_chat_turn(request)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Mission intelligence service encountered an unexpected error."
        )


@router.get("/chat/{conversation_id}/history", response_model=List[Dict[str, Any]])
async def get_chat_history(conversation_id: str) -> List[Dict[str, Any]]:
    """Retrieves conversation message history for a specific conversation ID."""
    return get_conversation_history(conversation_id)


@router.post("/compare-routes", response_model=RouteComparisonResponse)
async def compare_alternative_route(request: RouteComparisonRequest) -> RouteComparisonResponse:
    """
    Non-destructively recalculates path metrics using alternative terrain traversal costs.
    The original mission trajectory remains unchanged.
    """
    try:
        return tool_compare_routes(
            image_id=request.image_id,
            alternative_terrain_costs=request.alternative_terrain_costs,
            allow_diagonal=request.allow_diagonal
        )
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=500,
            detail="Route comparison simulation encountered an unexpected error."
        )
