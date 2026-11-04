import io
import json
import pytest
from unittest.mock import MagicMock, patch
from PIL import Image

from backend.app.core.config import settings
from backend.app.core.telemetry import api_telemetry
from backend.app.schemas.models import ChatRequest, FullAnalysisRequest
from backend.app.services.image_service import validate_and_store_image, clear_image_store
from backend.app.services.mission_context import store_analysis, clear_analysis_store
import backend.app.services.reasoning_service
from backend.app.services.sam_service import run_live_sam_segmentation
from backend.app.services.reasoning_service import (
    generate_live_mission_briefing,
    process_chat_turn,
    clear_conversation_store
)
from backend.app.services.analysis_orchestrator import run_full_analysis


@pytest.fixture(autouse=True)
def clean_stores_and_telemetry():
    orig_enabled = settings._external_api_enabled
    orig_dry_run = settings._external_api_dry_run
    settings._external_api_enabled = False
    settings._external_api_dry_run = True

    clear_image_store()
    clear_analysis_store()
    clear_conversation_store()
    api_telemetry.reset(reset_ledger=True)
    yield
    settings._external_api_enabled = orig_enabled
    settings._external_api_dry_run = orig_dry_run
    clear_image_store()
    clear_analysis_store()
    clear_conversation_store()
    api_telemetry.reset(reset_ledger=True)


def create_sample_analysis():
    buf = io.BytesIO()
    img = Image.new("RGB", (64, 64), color=(180, 80, 30))
    img.save(buf, format="PNG")
    meta = validate_and_store_image(buf.getvalue(), "mars_test.png")
    req = FullAnalysisRequest(image_id=meta.image_id, concepts=["rock", "sand", "obstacle"])
    analysis = run_full_analysis(req)
    store_analysis(analysis)
    return meta.image_id, analysis


# =============================================================================
# SCENARIOS 1 - 4: GLOBAL KILL SWITCH & LEDGER TRACKING
# =============================================================================

def test_1_kill_switch_blocks_sam(monkeypatch):
    """Scenario 1: EXTERNAL_API_ENABLED=false blocks live SAM requests."""
    monkeypatch.setattr(settings, "_external_api_enabled", False)
    monkeypatch.setattr(settings, "_meta_api_key", "mock_key")

    with pytest.raises(RuntimeError) as exc_info:
        run_live_sam_segmentation("data:image/png;base64,abc", ["rock"], 64, 64, 8, 8)
    assert "kill switch" in str(exc_info.value).lower()


def test_2_kill_switch_blocks_briefing(monkeypatch):
    """Scenario 2: EXTERNAL_API_ENABLED=false blocks live briefing and tags provenance."""
    image_id, _ = create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", False)
    monkeypatch.setattr(settings, "_meta_reasoning_api_key", "mock_key")

    briefing = generate_live_mission_briefing(image_id)
    assert briefing.source_model == "EXTERNAL INFERENCE DISABLED"
    assert briefing.is_ai_generated is False


def test_3_kill_switch_blocks_chat(monkeypatch):
    """Scenario 3: EXTERNAL_API_ENABLED=false blocks live chat and tags provenance."""
    image_id, _ = create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", False)
    monkeypatch.setattr(settings, "_meta_reasoning_api_key", "mock_key")

    req = ChatRequest(image_id=image_id, message="Explain the path")
    resp = process_chat_turn(req)
    assert resp.source_model == "EXTERNAL INFERENCE DISABLED"
    assert resp.is_ai_generated is False


def test_4_kill_switch_updates_ledger(monkeypatch):
    """Scenario 4: Kill switch activations increment blocked_kill_switch in ledger."""
    image_id, _ = create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", False)
    monkeypatch.setattr(settings, "_meta_reasoning_api_key", "mock_key")

    generate_live_mission_briefing(image_id)
    summary = api_telemetry.get_telemetry_summary()
    assert summary["ledger"]["reasoning_stats"]["blocked_kill_switch"] >= 1


# =============================================================================
# SCENARIOS 5 - 7: DRY RUN SIMULATION MODE
# =============================================================================

def test_5_dry_run_sam(monkeypatch):
    """Scenario 5: Dry-run mode validates SAM parameters without dispatching network calls."""
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", True)
    monkeypatch.setattr(settings, "_meta_api_key", "mock_key")

    seg, masks, diags = run_live_sam_segmentation("data:image/png;base64,abc", ["rock"], 64, 64, 8, 8)
    assert any("[DRY RUN]" in d for d in diags)
    assert len(masks) > 0


def test_6_dry_run_briefing(monkeypatch):
    """Scenario 6: Dry-run mode returns validated briefing tagged with DRY RUN."""
    image_id, _ = create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", True)
    monkeypatch.setattr(settings, "_meta_reasoning_api_key", "mock_key")

    briefing = generate_live_mission_briefing(image_id)
    assert briefing.source_model == "DRY RUN"
    assert briefing.is_ai_generated is False


def test_7_dry_run_chat(monkeypatch):
    """Scenario 7: Dry-run mode returns validated chat reply tagged with DRY RUN."""
    image_id, _ = create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", True)
    monkeypatch.setattr(settings, "_meta_reasoning_api_key", "mock_key")

    req = ChatRequest(image_id=image_id, message="Count obstacles")
    resp = process_chat_turn(req)
    assert resp.source_model == "DRY RUN"
    assert "[DRY RUN SIMULATION]" in resp.reply


# =============================================================================
# SCENARIOS 8 - 9: MISSING CREDENTIALS RESILIENCE
# =============================================================================

def test_8_missing_sam_key_fallback(monkeypatch):
    """Scenario 8: Missing SAM key raises clean RuntimeError caught by orchestrator."""
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", False)
    monkeypatch.setattr(settings, "_meta_api_key", None)

    with pytest.raises(RuntimeError) as exc_info:
        run_live_sam_segmentation("data:image/png;base64,abc", ["rock"], 64, 64, 8, 8)
    assert "not configured" in str(exc_info.value).lower()


def test_9_missing_reasoning_key_fallback(monkeypatch):
    """Scenario 9: Missing reasoning key falls back cleanly to deterministic briefing."""
    image_id, _ = create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", False)
    monkeypatch.setattr(settings, "_meta_reasoning_api_key", None)
    monkeypatch.setattr(settings, "_meta_api_key", None)

    briefing = generate_live_mission_briefing(image_id)
    assert briefing.is_ai_generated is False
    assert briefing.source_model in ("deterministic-rule-engine", "DETERMINISTIC — OFFLINE FALLBACK")


# =============================================================================
# SCENARIOS 10 - 12: BUDGET ENFORCEMENT & RATE CAPS
# =============================================================================

def test_10_sam_concept_budget_truncation(monkeypatch):
    """Scenario 10: SAM concepts list is truncated to MAX_SAM_REQUESTS_PER_ANALYSIS."""
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", False)
    monkeypatch.setattr(settings, "_meta_api_key", "mock_key")
    monkeypatch.setattr(settings, "_max_sam_requests_per_analysis", 1)

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.output_text = "mock_output"
    mock_client.responses.create.return_value = mock_resp

    import openai
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: mock_client)

    # Provide 4 concepts; should only send 1
    mock_sam = MagicMock()
    mock_format = MagicMock()
    mock_parser = MagicMock()
    mock_parser.finish.return_value = MagicMock(result=MagicMock(records=[]))
    mock_format.create_parser.return_value = mock_parser
    mock_sam.image_segmentation_format.return_value = mock_format

    import sys
    monkeypatch.setitem(sys.modules, "meta_sam_parser", mock_sam)

    _, _, diags = run_live_sam_segmentation("data:image/png;base64,abc", ["rock", "sand", "soil", "crater"], 64, 64, 8, 8)
    assert mock_client.responses.create.call_count == 1
    assert any("Budget enforcement" in d for d in diags)


def test_11_briefing_request_single_call(monkeypatch):
    """Scenario 11: Briefing executes exactly 1 completion request."""
    image_id, _ = create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", False)
    monkeypatch.setattr(settings, "_meta_reasoning_api_key", "mock_key")

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value.choices = [
        MagicMock(message=MagicMock(content=json.dumps({
            "observation_overview": {"dominant_terrain": "bedrock"},
            "navigation_assessment": {"path_feasibility": "FEASIBLE"},
            "risk_and_uncertainty": {"terrain_hazards": []},
            "mission_takeaways": ["Single call briefing"]
        })))
    ]
    import openai
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: mock_client)

    generate_live_mission_briefing(image_id)
    assert mock_client.chat.completions.create.call_count == 1


def test_12_chat_tool_iterations_capped(monkeypatch):
    """Scenario 12: Tool loop does not exceed MAX_TOOL_ITERATIONS_PER_CHAT."""
    image_id, _ = create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", False)
    monkeypatch.setattr(settings, "_meta_reasoning_api_key", "mock_key")
    monkeypatch.setattr(settings, "_max_tool_iterations_per_chat", 2)
    monkeypatch.setattr(settings, "_max_reasoning_requests_per_chat", 5)

    # Make the model continuously request different tool calls
    f1 = MagicMock()
    f1.name = "get_mission_summary"
    f1.arguments = json.dumps({"image_id": image_id})
    mock_tc1 = MagicMock(id="c1", function=f1)

    f2 = MagicMock()
    f2.name = "get_terrain_distribution"
    f2.arguments = json.dumps({"image_id": image_id})
    mock_tc2 = MagicMock(id="c2", function=f2)

    f3 = MagicMock()
    f3.name = "get_route_metrics"
    f3.arguments = json.dumps({"image_id": image_id})
    mock_tc3 = MagicMock(id="c3", function=f3)

    mock_msg1 = MagicMock(tool_calls=[mock_tc1], content=None)
    mock_msg2 = MagicMock(tool_calls=[mock_tc2], content=None)
    mock_msg3 = MagicMock(tool_calls=[mock_tc3], content=None)

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        MagicMock(choices=[MagicMock(message=mock_msg1)]),
        MagicMock(choices=[MagicMock(message=mock_msg2)]),
        MagicMock(choices=[MagicMock(message=mock_msg3)])
    ]
    import openai
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: mock_client)

    req = ChatRequest(image_id=image_id, message="Run tools continuously")
    process_chat_turn(req)
    assert mock_client.chat.completions.create.call_count == 2  # Hard capped at 2


# =============================================================================
# SCENARIOS 13 - 16: LOOP BREAKERS & BOUNDED CONTEXT
# =============================================================================

def test_13_duplicate_tool_call_breaker(monkeypatch):
    """Scenario 13: Duplicate tool call signature breaks loop immediately."""
    image_id, _ = create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", False)
    monkeypatch.setattr(settings, "_meta_reasoning_api_key", "mock_key")
    monkeypatch.setattr(settings, "_max_tool_iterations_per_chat", 4)
    monkeypatch.setattr(settings, "_max_reasoning_requests_per_chat", 5)

    # Model requests IDENTICAL tool call twice in row
    f_dup = MagicMock()
    f_dup.name = "get_mission_summary"
    f_dup.arguments = json.dumps({"image_id": image_id})
    mock_tc = MagicMock(id="call_dup", function=f_dup)
    mock_msg = MagicMock(tool_calls=[mock_tc], content=None)

    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = MagicMock(choices=[MagicMock(message=mock_msg)])
    import openai
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: mock_client)

    req = ChatRequest(image_id=image_id, message="Loop identical tool")
    resp = process_chat_turn(req)
    # The duplicate call breaker stops the loop after 2nd attempt
    assert mock_client.chat.completions.create.call_count <= 2


def test_14_tool_output_truncation(monkeypatch):
    """Scenario 14: Oversized tool payloads are truncated to MAX_TOOL_OUTPUT_BYTES."""
    image_id, _ = create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", False)
    monkeypatch.setattr(settings, "_meta_reasoning_api_key", "mock_key")
    monkeypatch.setattr(settings, "_max_tool_output_bytes", 1024)

    # Tool returns massive diagnostic data
    giant_result = {"large_payload": "X" * 4000}
    with patch.dict("backend.app.services.reasoning_service.AVAILABLE_MISSION_TOOLS", {"get_mission_summary": lambda **k: giant_result}):
        mock_tc = MagicMock()
        mock_tc.id = "c_large"
        mock_tc.function = MagicMock()
        mock_tc.function.name = "get_mission_summary"
        mock_tc.function.arguments = json.dumps({"image_id": image_id})

        mock_msg1 = MagicMock(tool_calls=[mock_tc], content=None)
        mock_msg2 = MagicMock(tool_calls=None, content="Handled large payload")

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [
            MagicMock(choices=[MagicMock(message=mock_msg1)]),
            MagicMock(choices=[MagicMock(message=mock_msg2)])
        ]
        import openai
        monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: mock_client)

        req = ChatRequest(image_id=image_id, message="Run big tool")
        resp = process_chat_turn(req)
        # Verify the second call's messages list received truncated text
        second_call_messages = mock_client.chat.completions.create.call_args_list[1][1]["messages"]
        tool_reply_msg = [m for m in second_call_messages if isinstance(m, dict) and m.get("role") == "tool"][0]
        assert "truncated" in tool_reply_msg["content"].lower()
        assert len(tool_reply_msg["content"].encode("utf-8")) <= 1024
        parsed = json.loads(tool_reply_msg["content"])
        assert parsed.get("_truncated") is True


def test_15_input_text_length_bounded(monkeypatch):
    """Scenario 15: Chat messages exceeding MAX_INPUT_TEXT_LENGTH are truncated."""
    image_id, _ = create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", False)
    monkeypatch.setattr(settings, "_max_input_text_length", 50)

    long_prompt = "A" * 500
    req = ChatRequest(image_id=image_id, message=long_prompt)
    resp = process_chat_turn(req)
    # The history record should be bounded
    hist = backend.app.services.reasoning_service.get_conversation_history(resp.conversation_id)
    assert len(hist[0]["content"]) <= 50


def test_16_conversation_history_capped(monkeypatch):
    """Scenario 16: In-memory history retains at most MAX_CONVERSATION_HISTORY_MESSAGES."""
    image_id, _ = create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", False)
    monkeypatch.setattr(settings, "_max_conversation_history_messages", 4)

    conv_id = "test_bounded_history"
    for i in range(10):
        req = ChatRequest(image_id=image_id, message=f"Question {i}", conversation_id=conv_id)
        process_chat_turn(req)

    hist = backend.app.services.reasoning_service.get_conversation_history(conv_id)
    assert len(hist) <= 4


# =============================================================================
# SCENARIOS 17 - 18: CLIENT TIME-OUTS & RETRY SETTINGS
# =============================================================================

def test_17_zero_retries_configured(monkeypatch):
    """Scenario 17: OpenAI client is instantiated with max_retries=0."""
    image_id, _ = create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", False)
    monkeypatch.setattr(settings, "_meta_reasoning_api_key", "mock_key")
    monkeypatch.setattr(settings, "_max_retries", 0)

    captured_kwargs = {}
    def mock_openai_init(**kwargs):
        captured_kwargs.update(kwargs)
        mock_c = MagicMock()
        mock_c.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content="{}"))
        ]
        return mock_c

    import openai
    monkeypatch.setattr(openai, "OpenAI", mock_openai_init)

    generate_live_mission_briefing(image_id)
    assert captured_kwargs.get("max_retries") == 0


def test_18_explicit_timeouts_configured(monkeypatch):
    """Scenario 18: OpenAI client has connect and read timeouts explicitly set."""
    image_id, _ = create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", False)
    monkeypatch.setattr(settings, "_meta_reasoning_api_key", "mock_key")
    monkeypatch.setattr(settings, "_connect_timeout_seconds", 5.0)
    monkeypatch.setattr(settings, "_read_timeout_seconds", 25.0)

    captured_kwargs = {}
    def mock_openai_init(**kwargs):
        captured_kwargs.update(kwargs)
        mock_c = MagicMock()
        mock_c.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content="{}"))
        ]
        return mock_c

    import openai
    monkeypatch.setattr(openai, "OpenAI", mock_openai_init)

    generate_live_mission_briefing(image_id)
    timeout_obj = captured_kwargs.get("timeout")
    assert timeout_obj.connect == 5.0
    assert timeout_obj.read == 25.0


# =============================================================================
# SCENARIOS 19 - 20: CONCURRENCY CONSTRAINTS
# =============================================================================

def test_19_sam_concurrency_semaphore(monkeypatch):
    """Scenario 19: Exceeding SAM semaphore raises concurrency limit exception."""
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", False)
    monkeypatch.setattr(settings, "_meta_api_key", "mock_key")
    monkeypatch.setattr(settings, "_connect_timeout_seconds", 0.05)

    # Exhaust the SAM semaphore
    api_telemetry.sam_semaphore.acquire()
    try:
        with pytest.raises(RuntimeError) as exc_info:
            run_live_sam_segmentation("data:image/png;base64,abc", ["rock"], 64, 64, 8, 8)
        assert "concurrency" in str(exc_info.value).lower()
    finally:
        api_telemetry.sam_semaphore.release()


def test_20_reasoning_concurrency_semaphore(monkeypatch):
    """Scenario 20: Exceeding reasoning semaphore falls back to deterministic briefing."""
    image_id, _ = create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", False)
    monkeypatch.setattr(settings, "_meta_reasoning_api_key", "mock_key")
    monkeypatch.setattr(settings, "_connect_timeout_seconds", 0.05)

    # Exhaust reasoning semaphore
    api_telemetry.reasoning_semaphore.acquire()
    try:
        briefing = generate_live_mission_briefing(image_id)
        assert briefing.is_ai_generated is False
        assert briefing.source_model == "DETERMINISTIC — OFFLINE FALLBACK"
    finally:
        api_telemetry.reasoning_semaphore.release()


# =============================================================================
# SCENARIOS 21 - 22: MUSE SPARK ROUTING & RESILIENT FALLBACK
# =============================================================================

def test_21_muse_spark_primary_fallback_to_llama(monkeypatch):
    """Scenario 21: Primary Muse Spark encounters 403/404, gracefully falls back to Llama 3.3."""
    image_id, _ = create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", False)
    monkeypatch.setattr(settings, "_meta_reasoning_api_key", "mock_key")
    monkeypatch.setattr(settings, "_reasoning_provider", "muse-spark")
    monkeypatch.setattr(settings, "_muse_spark_model", "muse-spark-1.3")
    monkeypatch.setattr(settings, "_llama_model", "llama-3.3-70b-instruct")

    mock_client = MagicMock()
    # Muse Spark call throws 403 Forbidden; Llama call succeeds
    def mock_create(*args, **kwargs):
        model = kwargs.get("model")
        if model == "muse-spark-1.3":
            raise RuntimeError("403 Forbidden: Model allowlist restricted")
        return MagicMock(choices=[MagicMock(message=MagicMock(content=json.dumps({
            "observation_overview": {"dominant_terrain": "sand"},
            "navigation_assessment": {"path_feasibility": "FEASIBLE"},
            "risk_and_uncertainty": {"terrain_hazards": []},
            "mission_takeaways": ["Llama fallback succeeded"]
        })))])

    mock_client.chat.completions.create.side_effect = mock_create
    import openai
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: mock_client)

    briefing = generate_live_mission_briefing(image_id)
    assert briefing.is_ai_generated is True
    assert briefing.source_model == "llama-3.3-70b-instruct"
    # Telemetry should record failure for muse-spark and success for llama
    summary = api_telemetry.get_telemetry_summary()
    assert summary["ledger"]["reasoning_stats"]["by_model"]["muse-spark-1.3"]["failed"] == 1
    assert summary["ledger"]["reasoning_stats"]["by_model"]["llama-3.3-70b-instruct"]["succeeded"] == 1


def test_22_fallback_to_deterministic_when_all_fail(monkeypatch):
    """Scenario 22: Both Muse Spark and Llama fail, pipeline falls back to deterministic rule engine."""
    image_id, _ = create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", False)
    monkeypatch.setattr(settings, "_meta_reasoning_api_key", "mock_key")
    monkeypatch.setattr(settings, "_reasoning_provider", "muse-spark")

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("All endpoints unreachable")
    import openai
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: mock_client)

    briefing = generate_live_mission_briefing(image_id)
    assert briefing.is_ai_generated is False
    assert briefing.source_model == "DETERMINISTIC — OFFLINE FALLBACK"
    assert briefing.observation_overview["terrain_classes_count"] > 0
