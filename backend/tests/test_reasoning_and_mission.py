import io
import pytest
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.services.image_service import validate_and_store_image, clear_image_store
from backend.app.services.analysis_orchestrator import run_full_analysis
from backend.app.services.mission_context import (
    get_analysis,
    build_mission_context,
    clear_analysis_store
)
from backend.app.services.mission_tools import (
    tool_get_mission_summary,
    tool_get_terrain_distribution,
    tool_get_region_details,
    tool_get_route_metrics,
    tool_compare_routes,
    tool_get_analysis_diagnostics
)
from backend.app.services.reasoning_service import (
    generate_deterministic_briefing,
    process_chat_turn,
    get_conversation_history,
    clear_conversation_store
)
from backend.app.schemas.models import (
    FullAnalysisRequest,
    ChatRequest,
    RouteComparisonRequest
)
from PIL import Image


@pytest.fixture(autouse=True)
def setup_teardown():
    clear_image_store()
    clear_analysis_store()
    clear_conversation_store()
    yield
    clear_image_store()
    clear_analysis_store()
    clear_conversation_store()


def create_sample_analysis():
    # Helper to create a valid active analysis in the mission store
    buf = io.BytesIO()
    img = Image.new("RGB", (64, 48), color=(210, 105, 30))
    img.save(buf, format="PNG")
    meta = validate_and_store_image(buf.getvalue(), "jezero_test.png")

    req = FullAnalysisRequest(
        image_id=meta.image_id,
        grid_downsample_factor=4,
        allow_diagonal=True
    )
    analysis = run_full_analysis(req)
    return meta.image_id, analysis


def test_mission_context_builder():
    image_id, analysis = create_sample_analysis()
    ctx = build_mission_context(analysis)

    assert ctx.image_id == image_id
    assert ctx.total_cells > 0
    assert sum(ctx.terrain_distribution.values()) == ctx.total_cells
    assert ctx.route_found is True
    assert ctx.waypoints_count > 0
    assert len(ctx.limitations) >= 3


def test_deterministic_briefing_generation():
    image_id, _ = create_sample_analysis()
    briefing = generate_deterministic_briefing(image_id)

    assert briefing.image_id == image_id
    assert briefing.source_model == "deterministic-rule-engine"
    assert briefing.is_ai_generated is False
    assert "detected_concepts" in briefing.observation_overview
    assert briefing.navigation_assessment["path_feasibility"] == "FEASIBLE"
    assert len(briefing.mission_takeaways) >= 2


def test_mission_tools_execution():
    image_id, _ = create_sample_analysis()

    # 1. Summary
    summary = tool_get_mission_summary(image_id)
    assert summary["image_id"] == image_id
    assert summary["route_found"] is True

    # 2. Distribution
    dist = tool_get_terrain_distribution(image_id)
    assert "cell_counts" in dist
    assert "percentages" in dist

    # 3. Regions
    regions = tool_get_region_details(image_id)
    assert "regions" in regions

    # 4. Route metrics
    metrics = tool_get_route_metrics(image_id)
    assert metrics["is_success"] is True
    assert metrics["waypoints_count"] > 0

    # 5. Diagnostics
    diags = tool_get_analysis_diagnostics(image_id)
    assert "scientific_limitations" in diags


def test_tool_compare_routes_preserves_original():
    image_id, analysis = create_sample_analysis()
    orig_cost = analysis.path_result.total_weighted_cost

    # Run comparison with high penalty on rocky terrain
    alt_costs = {"clear": 1.0, "rocky": 25.0, "loose": 5.0, "unknown": 2.0, "obstacle": None}
    comp = tool_compare_routes(image_id, alt_costs, allow_diagonal=True)

    assert comp.original_cost == round(orig_cost, 2)
    assert comp.cost_delta >= 0
    assert len(comp.alternative_path) > 0

    # Verify original analysis in store was NOT mutated
    persisted = get_analysis(image_id)
    assert persisted.path_result.total_weighted_cost == orig_cost


def test_chat_turn_route_explanation():
    image_id, _ = create_sample_analysis()
    req = ChatRequest(
        image_id=image_id,
        message="Why did RoverMind select this route instead of going straight?"
    )
    res = process_chat_turn(req)

    assert res.image_id == image_id
    assert len(res.reply) > 50
    assert "A*" in res.reply or "obstacle" in res.reply.lower() or "cost" in res.reply.lower()
    assert len(res.tool_calls_executed) >= 1


def test_chat_turn_obstacle_count():
    image_id, _ = create_sample_analysis()
    req = ChatRequest(
        image_id=image_id,
        message="How many obstacle cells were detected in this frame?"
    )
    res = process_chat_turn(req)

    assert res.image_id == image_id
    assert "Obstacle" in res.reply or "cells" in res.reply.lower()
    assert any(log.tool_name == "get_terrain_distribution" for log in res.tool_calls_executed)


def test_chat_turn_safety_disclaimer():
    image_id, _ = create_sample_analysis()
    req = ChatRequest(
        image_id=image_id,
        message="Is this route guaranteed safe for a rover?"
    )
    res = process_chat_turn(req)

    assert "NOT guaranteed" in res.reply or "decision-support" in res.reply.lower()
    assert "monocular" in res.reply.lower()


def test_chat_turn_alternative_simulation():
    image_id, _ = create_sample_analysis()
    req = ChatRequest(
        image_id=image_id,
        message="What happens if rocky terrain has a traversal cost of 10?"
    )
    res = process_chat_turn(req)

    assert "Alternative" in res.reply or "Comparison" in res.reply
    assert any(log.tool_name == "compare_routes" for log in res.tool_calls_executed)


def test_chat_history_bounding():
    image_id, _ = create_sample_analysis()
    conv_id = "test_conv_bounded"

    # Send 25 messages
    for i in range(25):
        req = ChatRequest(
            image_id=image_id,
            conversation_id=conv_id,
            message=f"Query number {i}"
        )
        process_chat_turn(req)

    history = get_conversation_history(conv_id)
    # Must not exceed MAX_MESSAGES_PER_CONVERSATION (20)
    assert len(history) <= 20


def test_mission_api_endpoints():
    client = TestClient(app)
    image_id, _ = create_sample_analysis()

    # 1. Capabilities
    caps = client.get("/api/mission/capabilities")
    assert caps.status_code == 200
    assert "visual_segmentation" in caps.json()
    assert "mission_reasoning" in caps.json()

    # 2. Context
    ctx = client.get(f"/api/mission/{image_id}/context")
    assert ctx.status_code == 200
    assert ctx.json()["image_id"] == image_id

    # 3. Briefing
    briefing = client.get(f"/api/mission/{image_id}/briefing")
    assert briefing.status_code == 200
    assert "observation_overview" in briefing.json()

    # 4. Chat
    chat_resp = client.post("/api/mission/chat", json={
        "image_id": image_id,
        "message": "Summarize the observations in this image."
    })
    assert chat_resp.status_code == 200
    assert len(chat_resp.json()["reply"]) > 20

    # 5. Route Compare Endpoint
    comp_resp = client.post("/api/mission/compare-routes", json={
        "image_id": image_id,
        "alternative_terrain_costs": {"rocky": 12.0, "clear": 1.0}
    })
    assert comp_resp.status_code == 200
    assert "cost_delta" in comp_resp.json()


def test_mocked_live_reasoning_briefing(monkeypatch):
    import json
    from backend.app.core.config import settings
    from backend.app.services.reasoning_service import generate_live_mission_briefing

    image_id, _ = create_sample_analysis()
    monkeypatch.setattr(settings, "_meta_reasoning_api_key", "mock_key_123")
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", False)

    mock_json = json.dumps({
        "observation_overview": {"dominant_terrain": "bedrock", "detected_concepts": ["rock", "sand"]},
        "navigation_assessment": {"path_feasibility": "FEASIBLE", "waypoints_count": 42},
        "risk_and_uncertainty": {"elevated_cost_regions": ["sand drift"]},
        "mission_takeaways": ["Route verified by mock model"]
    })

    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = mock_json
    mock_client.chat.completions.create.return_value.choices = [mock_choice]

    import openai
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: mock_client)

    briefing = generate_live_mission_briefing(image_id)
    assert briefing.is_ai_generated is True
    assert briefing.source_model == settings.meta_reasoning_model
    assert briefing.observation_overview["dominant_terrain"] == "bedrock"


def test_mocked_live_reasoning_chat_tool_calling(monkeypatch):
    import json
    from backend.app.core.config import settings
    from backend.app.services.reasoning_service import process_chat_turn

    image_id, _ = create_sample_analysis()
    monkeypatch.setattr(settings, "_meta_reasoning_api_key", "mock_key_123")
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", False)

    # Step 1: Model requests a tool call to get_terrain_distribution
    mock_tc = MagicMock()
    mock_tc.id = "call_abc123"
    mock_tc.function.name = "get_terrain_distribution"
    mock_tc.function.arguments = json.dumps({"image_id": image_id})

    mock_msg1 = MagicMock()
    mock_msg1.tool_calls = [mock_tc]
    mock_msg1.content = None

    # Step 2: Model returns final text using tool result
    mock_msg2 = MagicMock()
    mock_msg2.tool_calls = None
    mock_msg2.content = "Verified terrain distribution: clear bedrock dominates the frame."

    mock_client = MagicMock()
    mock_choice1 = MagicMock(message=mock_msg1)
    mock_choice2 = MagicMock(message=mock_msg2)
    mock_client.chat.completions.create.side_effect = [
        MagicMock(choices=[mock_choice1]),
        MagicMock(choices=[mock_choice2])
    ]

    import openai
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: mock_client)

    req = ChatRequest(
        image_id=image_id,
        message="What is the dominant terrain?"
    )
    res = process_chat_turn(req)

    assert res.is_ai_generated is True
    assert "bedrock" in res.reply
    assert any(log.tool_name == "get_terrain_distribution" for log in res.tool_calls_executed)

