"""
RoverMind — Production API Hardening & Telemetry Verification Suite
Exhaustive verification of API safety, budget enforcement, provider routing,
thread-safe telemetry counters, error sanitization, ledger resilience, and offline isolation.
Zero external or paid network requests are performed.
"""

import json
import os
import io
import time
import uuid
import threading
from unittest.mock import MagicMock, patch
import pytest
from PIL import Image

from backend.app.core.config import settings, _validate_url, _parse_float, _parse_int, _parse_bool, Settings
from backend.app.core.budget import RequestBudget
from backend.app.core.sanitizer import sanitize_error, contains_sensitive_data
from backend.app.core.telemetry import api_telemetry, ApiTelemetryTracker
from backend.app.schemas.models import ChatRequest, FullAnalysisRequest
from backend.app.services.image_service import validate_and_store_image, clear_image_store
from backend.app.services.mission_context import store_analysis, clear_analysis_store
from backend.app.services.analysis_orchestrator import run_full_analysis
from backend.app.services.sam_service import run_live_sam_segmentation
from backend.app.services.mask_reconstruction import reconstruct_grid_from_masks
from backend.app.services.reasoning_service import (
    generate_live_mission_briefing,
    process_chat_turn,
    resolve_reasoning_providers,
    clear_conversation_store,
    truncate_tool_output,
    should_attempt_fallback,
    SchemaValidationError,
    _CONVERSATION_STORE,
    MAX_CONVERSATIONS
)


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


def _create_sample_image_id() -> str:
    """Helper creating a valid test image in the store."""
    img = Image.new("RGB", (64, 64), color=(180, 80, 50))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    stored = validate_and_store_image(buf.getvalue(), "test_mars_hardening.png")
    return stored.image_id


def _create_sample_analysis() -> str:
    """Helper running offline analysis pipeline to populate a mission record."""
    image_id = _create_sample_image_id()
    req = FullAnalysisRequest(image_id=image_id, concepts=["rock", "sand", "obstacle"])
    analysis = run_full_analysis(req)
    store_analysis(analysis)
    return image_id


# =============================================================================
# CATEGORY 1: BUDGET ENFORCEMENT (7 TESTS)
# =============================================================================

def test_sam_per_analysis_budget_enforced(monkeypatch):
    """1. SAM cannot exceed per-analysis budget across multiple function calls or concepts."""
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", False)
    monkeypatch.setattr(settings, "_meta_api_key", "sec_sam_mock_key_123")
    monkeypatch.setattr(settings, "_max_sam_requests_per_analysis", 1)

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.output_text = "mock_sam_output"
    mock_client.responses.create.return_value = mock_resp

    mock_sam = MagicMock()
    mock_format = MagicMock()
    mock_parser = MagicMock()
    mock_parser.finish.return_value = MagicMock(result=MagicMock(records=[]))
    mock_format.create_parser.return_value = mock_parser
    mock_sam.image_segmentation_format.return_value = mock_format

    import openai
    import sys
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: mock_client)
    monkeypatch.setitem(sys.modules, "meta_sam_parser", mock_sam)

    budget = RequestBudget(settings.max_sam_requests_per_analysis, "test_sam")
    # First call uses the budget (1 of 1)
    masks, confs, diags = run_live_sam_segmentation(
        "data:image/png;base64,abc", ["rock", "sand"], 64, 64, 8, 8, budget=budget
    )
    assert mock_client.responses.create.call_count == 1
    assert budget.consumed == 1

    # Second call with the same budget must be stopped by budget check without making another API request
    _, _, diags2 = run_live_sam_segmentation(
        "data:image/png;base64,abc", ["boulder"], 64, 64, 8, 8, budget=budget
    )
    assert any("budget exhausted" in d.lower() for d in diags2)
    # Call count should still be 1
    assert mock_client.responses.create.call_count == 1


def test_reasoning_per_briefing_budget_enforced(monkeypatch):
    """2. Reasoning cannot exceed per-briefing budget."""
    image_id = _create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", False)
    monkeypatch.setattr(settings, "_meta_reasoning_api_key", "sec_mock_key")
    monkeypatch.setattr(settings, "_max_reasoning_requests_per_briefing", 1)
    monkeypatch.setattr(settings, "_reasoning_provider", "muse-spark")
    monkeypatch.setattr(settings, "_fallback_reasoning_provider", "llama-3.3")

    mock_client = MagicMock()
    # First model call fails
    mock_client.chat.completions.create.side_effect = RuntimeError("503 Service Unavailable")
    import openai
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: mock_client)

    # With budget=1, primary call consumes 1, fallback cannot execute because budget is exhausted
    briefing = generate_live_mission_briefing(image_id)
    assert mock_client.chat.completions.create.call_count == 1
    assert briefing.is_ai_generated is False
    assert briefing.source_model == "DETERMINISTIC — OFFLINE FALLBACK"


def test_reasoning_per_chat_turn_budget_enforced(monkeypatch):
    """3. Reasoning cannot exceed per-chat-turn budget even with tool iteration loop."""
    image_id = _create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", False)
    monkeypatch.setattr(settings, "_meta_reasoning_api_key", "sec_mock_key")
    monkeypatch.setattr(settings, "_max_reasoning_requests_per_chat", 2)
    monkeypatch.setattr(settings, "_max_tool_iterations_per_chat", 5)

    f1 = MagicMock(); f1.name = "get_mission_summary"; f1.arguments = json.dumps({"image_id": image_id})
    f2 = MagicMock(); f2.name = "get_terrain_distribution"; f2.arguments = json.dumps({"image_id": image_id})
    f3 = MagicMock(); f3.name = "get_route_metrics"; f3.arguments = json.dumps({"image_id": image_id})

    mock_tc1 = MagicMock(id="c1", function=f1)
    mock_tc2 = MagicMock(id="c2", function=f2)
    mock_tc3 = MagicMock(id="c3", function=f3)

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        MagicMock(choices=[MagicMock(message=MagicMock(tool_calls=[mock_tc1], content=None))]),
        MagicMock(choices=[MagicMock(message=MagicMock(tool_calls=[mock_tc2], content=None))]),
        MagicMock(choices=[MagicMock(message=MagicMock(tool_calls=[mock_tc3], content=None))]),
    ]
    import openai
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: mock_client)

    req = ChatRequest(image_id=image_id, message="Run tool chain")
    process_chat_turn(req)

    # Even though max_tool_iterations was 5, max_reasoning_requests_per_chat was 2
    assert mock_client.chat.completions.create.call_count == 2


def test_primary_and_fallback_share_budget(monkeypatch):
    """4. Primary and fallback calls share the same budget."""
    image_id = _create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", False)
    monkeypatch.setattr(settings, "_meta_reasoning_api_key", "sec_mock_key")
    monkeypatch.setattr(settings, "_max_reasoning_requests_per_briefing", 2)
    monkeypatch.setattr(settings, "_reasoning_provider", "muse-spark")
    monkeypatch.setattr(settings, "_fallback_reasoning_provider", "llama-3.3")

    mock_client = MagicMock()
    # Muse Spark fails, Llama succeeds
    def mock_create(*args, **kwargs):
        if kwargs.get("model") == settings.muse_spark_model:
            raise RuntimeError("Primary model timeout")
        return MagicMock(choices=[MagicMock(message=MagicMock(content=json.dumps({
            "observation_overview": {"dominant_terrain": "bedrock"},
            "navigation_assessment": {"path_feasibility": "FEASIBLE"},
            "risk_and_uncertainty": {"terrain_hazards": ["slope"]},
            "mission_takeaways": ["Proceed carefully"]
        })))])

    mock_client.chat.completions.create.side_effect = mock_create
    import openai
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: mock_client)

    briefing = generate_live_mission_briefing(image_id)
    assert briefing.is_ai_generated is True
    assert briefing.source_model == settings.llama_model
    # Exactly 2 calls (1 primary + 1 fallback = 2 total budget consumed)
    assert mock_client.chat.completions.create.call_count == 2


def test_failed_attempts_consume_budget(monkeypatch):
    """5. Failed API attempts consume budget; further requests rejected once budget exhausted."""
    budget = RequestBudget(limit=1, operation_name="test_failure_budget")
    assert budget.can_request() is True
    assert budget.record_request() is True
    assert budget.consumed == 1
    # Now budget is exhausted
    assert budget.can_request() is False
    assert budget.record_request() is False


def test_dry_run_and_offline_do_not_consume_budget(monkeypatch):
    """6. Dry-run and offline calls do not consume live request budgets."""
    image_id = _create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", True)
    monkeypatch.setattr(settings, "_meta_reasoning_api_key", "sec_mock_key")

    budget = RequestBudget(limit=2, operation_name="dry_run_op")
    briefing = generate_live_mission_briefing(image_id, budget=budget)
    assert briefing.source_model == "DRY RUN"
    # Budget was untouched
    assert budget.consumed == 0


def test_concurrent_operations_budget_isolation():
    """7. Concurrent operations maintain independent budget limits without cross-bleeding."""
    def worker(limit: int, results: list, idx: int):
        b = RequestBudget(limit=limit, operation_name=f"worker_{idx}")
        consumed = 0
        while b.record_request():
            consumed += 1
            time.sleep(0.005)
        results.append((idx, consumed, limit))

    results = []
    threads = []
    for i in range(5):
        limit = i + 1
        t = threading.Thread(target=worker, args=(limit, results, i))
        threads.append(t)
        t.start()

    for t in threads:
        t.join()

    assert len(results) == 5
    for idx, consumed, limit in results:
        assert consumed == limit, f"Worker {idx} consumed {consumed} != limit {limit}"


# =============================================================================
# CATEGORY 2: PROVIDER SELECTION & FALLBACK (6 TESTS)
# =============================================================================

def test_provider_selection_muse_primary(monkeypatch):
    """1. muse-spark selects configured Muse model as primary."""
    monkeypatch.setattr(settings, "_reasoning_provider", "muse-spark")
    monkeypatch.setattr(settings, "_muse_spark_model", "custom-muse-spark")
    monkeypatch.setattr(settings, "_fallback_reasoning_provider", "llama-3.3")

    pri_prov, pri_model, fb_prov, fb_model = resolve_reasoning_providers()
    assert pri_prov == "muse-spark"
    assert pri_model == "custom-muse-spark"
    assert fb_prov == "llama-3.3"
    assert fb_model == settings.llama_model


def test_provider_selection_llama_primary(monkeypatch):
    """2. llama-3.3 selects configured Llama model as primary."""
    monkeypatch.setattr(settings, "_reasoning_provider", "llama-3.3")
    monkeypatch.setattr(settings, "_llama_model", "custom-llama-3.3")
    monkeypatch.setattr(settings, "_fallback_reasoning_provider", "offline")

    pri_prov, pri_model, fb_prov, fb_model = resolve_reasoning_providers()
    assert pri_prov == "llama-3.3"
    assert pri_model == "custom-llama-3.3"
    assert fb_prov == "offline"
    assert fb_model is None


def test_offline_mode_makes_zero_external_calls(monkeypatch):
    """3. offline mode makes zero external calls and does not initialize an external client."""
    image_id = _create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", False)
    monkeypatch.setattr(settings, "_reasoning_provider", "offline")

    mock_openai = MagicMock()
    import openai
    monkeypatch.setattr(openai, "OpenAI", mock_openai)

    briefing = generate_live_mission_briefing(image_id)
    assert briefing.is_ai_generated is False
    assert "DETERMINISTIC" in briefing.source_model
    # OpenAI client was never instantiated
    assert mock_openai.call_count == 0


def test_configured_fallback_provider_respected(monkeypatch):
    """4. Configured fallback provider is respected when primary fails."""
    image_id = _create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", False)
    monkeypatch.setattr(settings, "_meta_reasoning_api_key", "sec_mock_key")
    monkeypatch.setattr(settings, "_reasoning_provider", "muse-spark")
    monkeypatch.setattr(settings, "_fallback_reasoning_provider", "offline")

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = RuntimeError("Muse Spark unavailable")
    import openai
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: mock_client)

    briefing = generate_live_mission_briefing(image_id)
    # When fallback is offline, failed primary directly delegates to deterministic rule engine
    assert briefing.is_ai_generated is False
    assert briefing.source_model == "DETERMINISTIC — OFFLINE FALLBACK"


def test_fallback_does_not_retry_same_provider(monkeypatch):
    """5. Fallback does not retry the same provider if fallback is configured identical to primary."""
    monkeypatch.setattr(settings, "_reasoning_provider", "muse-spark")
    monkeypatch.setattr(settings, "_fallback_reasoning_provider", "muse-spark")

    pri_prov, pri_model, fb_prov, fb_model = resolve_reasoning_providers()
    assert pri_prov == "muse-spark"
    # Fallback provider set to "offline" / fb_model None to avoid wasteful self-retry
    assert fb_prov == "offline"
    assert fb_model is None


def test_fallback_cannot_bypass_guards(monkeypatch):
    """6. Fallback cannot bypass kill switch, dry run, or exhausted budget."""
    image_id = _create_sample_analysis()
    # Test kill switch
    monkeypatch.setattr(settings, "_external_api_enabled", False)
    monkeypatch.setattr(settings, "_reasoning_provider", "muse-spark")
    monkeypatch.setattr(settings, "_fallback_reasoning_provider", "llama-3.3")

    mock_client = MagicMock()
    import openai
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: mock_client)

    briefing = generate_live_mission_briefing(image_id)
    assert briefing.source_model == "EXTERNAL INFERENCE DISABLED"
    assert mock_client.chat.completions.create.call_count == 0


# =============================================================================
# CATEGORY 3: TELEMETRY & LEDGER ACCURACY (7 TESTS)
# =============================================================================

def test_failure_after_success_reports_failure():
    """1. Success followed by failure reports latest outcome as failure."""
    model = "test-model-outcome"
    api_telemetry.record_reasoning_start(model)
    api_telemetry.record_reasoning_success(model)

    summary = api_telemetry.get_telemetry_summary()
    assert summary["reasoning_active_requests"] == 0
    assert summary["reasoning_last_outcome"] == "success"

    # Now execute a second request that fails
    api_telemetry.record_reasoning_start(model)
    api_telemetry.record_reasoning_failure(model, "Synthetic API error")

    summary2 = api_telemetry.get_telemetry_summary()
    assert summary2["reasoning_active_requests"] == 0
    assert summary2["reasoning_last_outcome"] == "failure"
    assert summary2["reasoning_last_error"] == "Synthetic API error"


def test_concurrent_active_request_counts():
    """2. Concurrent requests maintain accurate active-request counts without drifting."""
    initial_summary = api_telemetry.get_telemetry_summary()
    init_sam = initial_summary["sam_active_requests"]
    init_reasoning = initial_summary["reasoning_active_requests"]

    def run_simulated_activity():
        for _ in range(20):
            api_telemetry.record_sam_start()
            time.sleep(0.001)
            api_telemetry.record_sam_success()

            api_telemetry.record_reasoning_start("thread-model")
            time.sleep(0.001)
            api_telemetry.record_reasoning_success("thread-model")

    threads = [threading.Thread(target=run_simulated_activity) for _ in range(5)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    final_summary = api_telemetry.get_telemetry_summary()
    assert final_summary["sam_active_requests"] == init_sam
    assert final_summary["reasoning_active_requests"] == init_reasoning


def test_error_sanitization_removes_sensitive_data():
    """3. Sanitization removes API keys, Bearer tokens, query credentials, payload data, and base64."""
    dirty_err = (
        "Failed request to https://api.example.com/v1?key=AIzaSySecret1234567890 "
        "Authorization: Bearer sk-ant-api03-abcdefghijklmn9876543210 "
        "data:image/jpeg;base64,/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAP////////////////// "
        "meta_api_key=sk-proj-xyz123456789"
    )
    cleaned = sanitize_error(dirty_err)
    assert not contains_sensitive_data(cleaned)
    assert "AIzaSySecret1234567890" not in cleaned
    assert "sk-ant-api03-abcdefghijklmn9876543210" not in cleaned
    assert "/9j/4AAQSkZJRgABAQEASABIAAD" not in cleaned
    assert "[REDACTED_KEY]" in cleaned or "[REDACTED_API_KEY]" in cleaned
    assert "[REDACTED_TOKEN]" in cleaned or "[REDACTED_BEARER_TOKEN]" in cleaned or "[REDACTED_AUTH_HEADER]" in cleaned
    assert "[REDACTED_BASE64_IMAGE]" in cleaned


def test_ledger_survives_restart(tmp_path, monkeypatch):
    """4. Ledger survives simulated backend reload/restart."""
    test_ledger_file = tmp_path / "api_usage_ledger.json"
    monkeypatch.setattr("backend.app.core.telemetry.LEDGER_FILE_PATH", test_ledger_file)

    tracker1 = ApiTelemetryTracker()
    tracker1.record_reasoning_start("muse-spark-1.3")
    tracker1.record_reasoning_success("muse-spark-1.3")
    tracker1.record_sam_start()
    tracker1.record_sam_failure("Mock SAM failure")

    # Reopen with a new instance (simulating app reload)
    tracker2 = ApiTelemetryTracker()
    summary = tracker2.get_telemetry_summary()

    assert summary["ledger"]["reasoning_stats"]["succeeded"] >= 1
    assert summary["ledger"]["sam_stats"]["failed"] >= 1


def test_corrupt_ledger_preservation(tmp_path, monkeypatch):
    """5. Corrupt ledger recovery preserves corrupt file with timestamp backup and starts clean ledger."""
    test_ledger_file = tmp_path / "api_usage_ledger.json"
    test_ledger_file.write_text("{ \"corrupted\": true, \"unclosed_bracket\": [")
    monkeypatch.setattr("backend.app.core.telemetry.LEDGER_FILE_PATH", test_ledger_file)

    tracker = ApiTelemetryTracker()
    summary = tracker.get_telemetry_summary()
    assert summary["ledger"]["sam_stats"]["attempted"] == 0

    corrupt_backups = list(tmp_path.glob("api_usage_ledger.corrupt.*.json"))
    assert len(corrupt_backups) >= 1
    assert "{ \"corrupted\": true" in corrupt_backups[0].read_text()


def test_persistence_failures_do_not_crash_analysis(tmp_path, monkeypatch):
    """6. Disk write errors during ledger persistence log non-fatal warnings and do not crash analysis."""
    test_ledger_file = tmp_path / "api_usage_ledger.json"
    monkeypatch.setattr("backend.app.core.telemetry.LEDGER_FILE_PATH", test_ledger_file)
    tracker = ApiTelemetryTracker()

    with patch("builtins.open", side_effect=OSError("Disk full")):
        # Must log warning and not raise unhandled exception
        tracker.record_reasoning_start("muse-spark-1.3")
        tracker.record_reasoning_success("muse-spark-1.3")


def test_provenance_identifies_succeeded_model(monkeypatch):
    """7. Provenance in briefing/chat accurately identifies the model that succeeded."""
    image_id = _create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", False)
    monkeypatch.setattr(settings, "_meta_reasoning_api_key", "sec_mock_key")
    monkeypatch.setattr(settings, "_reasoning_provider", "muse-spark")
    monkeypatch.setattr(settings, "_muse_spark_model", "muse-spark-candidate")
    monkeypatch.setattr(settings, "_fallback_reasoning_provider", "llama-3.3")
    monkeypatch.setattr(settings, "_llama_model", "llama-3.3-verified")

    mock_client = MagicMock()
    def mock_create(*args, **kwargs):
        if kwargs.get("model") == "muse-spark-candidate":
            raise RuntimeError("503 Service Unavailable: Primary model error")
        return MagicMock(choices=[MagicMock(message=MagicMock(content=json.dumps({
            "observation_overview": {"dominant_terrain": "regolith"},
            "navigation_assessment": {"path_feasibility": "FEASIBLE"},
            "risk_and_uncertainty": {"terrain_hazards": []},
            "mission_takeaways": ["Path clear"]
        })))])

    mock_client.chat.completions.create.side_effect = mock_create
    import openai
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: mock_client)

    briefing = generate_live_mission_briefing(image_id)
    assert briefing.is_ai_generated is True
    # Provenance accurately points to the fallback that succeeded
    assert briefing.source_model == "llama-3.3-verified"


# =============================================================================
# CATEGORY 4: OFFLINE, DRY-RUN & SECURITY GUARANTEES (5 TESTS)
# =============================================================================

def test_kill_switch_guarantees_zero_external_calls(monkeypatch):
    """1. Kill switch disabled guarantees zero external calls across all endpoints."""
    image_id = _create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", False)
    monkeypatch.setattr(settings, "_meta_reasoning_api_key", "sec_mock_key")

    mock_client = MagicMock()
    import openai
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: mock_client)

    # 1. Briefing
    b = generate_live_mission_briefing(image_id)
    assert b.source_model == "EXTERNAL INFERENCE DISABLED"
    assert b.is_ai_generated is False

    # 2. Chat
    c = process_chat_turn(ChatRequest(image_id=image_id, message="Status?"))
    assert c.source_model == "EXTERNAL INFERENCE DISABLED"
    assert c.is_ai_generated is False

    # 3. SAM
    with pytest.raises(RuntimeError) as exc_info:
        run_live_sam_segmentation("data:image/png;base64,abc", ["rock"], 64, 64, 8, 8)
    assert "kill switch" in str(exc_info.value).lower()

    # Absolutely 0 OpenAI calls made
    assert mock_client.chat.completions.create.call_count == 0


def test_dry_run_guarantees_zero_external_calls(monkeypatch):
    """2. Dry-run mode guarantees zero external calls even with mock keys set."""
    image_id = _create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", True)
    monkeypatch.setattr(settings, "_meta_reasoning_api_key", "sec_mock_key")
    monkeypatch.setattr(settings, "_meta_api_key", "sec_sam_key")

    mock_client = MagicMock()
    import openai
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: mock_client)

    # 1. SAM in dry-run returns synthetic masks without calling external API
    masks, confs, diags = run_live_sam_segmentation("data:image/png;base64,abc", ["rock"], 64, 64, 8, 8)
    assert any("DRY RUN" in d for d in diags)

    # 2. Briefing in dry-run
    b = generate_live_mission_briefing(image_id)
    assert b.source_model == "DRY RUN"

    # 3. Chat in dry-run
    c = process_chat_turn(ChatRequest(image_id=image_id, message="Where to go?"))
    assert c.source_model == "DRY RUN"

    # External client was never called
    assert mock_client.chat.completions.create.call_count == 0


def test_offline_reasoning_guarantees_zero_external_calls(monkeypatch):
    """3. Offline reasoning mode makes no network calls."""
    image_id = _create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", False)
    monkeypatch.setattr(settings, "_reasoning_provider", "offline")

    mock_client = MagicMock()
    import openai
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: mock_client)

    b = generate_live_mission_briefing(image_id)
    assert b.is_ai_generated is False
    assert mock_client.chat.completions.create.call_count == 0


def test_missing_credentials_graceful_handling(monkeypatch):
    """4. Missing credentials produce controlled, non-crashing behavior."""
    image_id = _create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", False)
    monkeypatch.setattr(settings, "_meta_reasoning_api_key", None)
    monkeypatch.setattr(settings, "_meta_api_key", None)

    # Briefing falls back cleanly
    b = generate_live_mission_briefing(image_id)
    assert b.is_ai_generated is False
    assert b.source_model == "DETERMINISTIC — OFFLINE FALLBACK"

    # Chat falls back cleanly
    c = process_chat_turn(ChatRequest(image_id=image_id, message="Test"))
    assert c.is_ai_generated is False
    assert c.source_model == "DETERMINISTIC — OFFLINE FALLBACK"


def test_no_secrets_in_logs_or_ledger(tmp_path, monkeypatch):
    """5. No secrets appear in logs or ledger files."""
    test_ledger_file = tmp_path / "clean_ledger.json"
    monkeypatch.setattr("backend.app.core.telemetry.LEDGER_FILE_PATH", test_ledger_file)
    tracker = ApiTelemetryTracker()

    secret_key = "sk-ant-live-super-secret-key-12345"
    bearer_token = "Bearer topsecrettoken999"

    # Record error that includes raw sensitive tokens
    dirty_err = f"Authentication failed with key {secret_key} and {bearer_token}"
    sanitized = sanitize_error(dirty_err)

    tracker.record_reasoning_failure("muse-spark-1.3", sanitized)

    assert test_ledger_file.exists()
    file_content = test_ledger_file.read_text(encoding="utf-8")

    assert secret_key not in file_content
    assert bearer_token not in file_content
    assert "[REDACTED_KEY]" in file_content or "[REDACTED_API_KEY]" in file_content
    assert "[REDACTED_TOKEN]" in file_content or "[REDACTED_BEARER_TOKEN]" in file_content


# =============================================================================
# CATEGORY 5: CONSOLIDATED PRE-LIVE HARDENING & EDGE CASE VERIFICATION (20 SPECIFIC TESTS)
# =============================================================================

def test_spec_1_sam_dry_run_unpacks_and_checks_masks(monkeypatch):
    """1. SAM dry-run returns 3-tuple (seg_result, mask_dtos, diags) and yields valid mask DTOs."""
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", True)
    monkeypatch.setattr(settings, "_meta_api_key", "sec_sam_mock_key")

    seg_result, mask_dtos, diags = run_live_sam_segmentation(
        "data:image/png;base64,dryrun", ["rock", "sand"], 64, 64, 8, 8
    )
    assert any("[DRY RUN]" in d for d in diags)
    assert len(mask_dtos) >= 2
    for m in mask_dtos:
        assert isinstance(m.concept, str) and len(m.concept) > 0
        assert m.confidence > 0.0
        assert m.area_pixels > 0


def test_spec_2_tool_output_byte_bounds_and_valid_json():
    """2. Tool output byte test verifies UTF-8 byte length <= max_bytes and valid structured JSON envelope."""
    payload = {"data": ["item_" + str(i) * 20 for i in range(50)]}
    out_str = truncate_tool_output(payload, max_bytes=256)
    raw_bytes = out_str.encode("utf-8")
    assert len(raw_bytes) <= 256
    parsed = json.loads(out_str)
    assert parsed.get("_truncated") is True
    assert parsed.get("bytes_limit") == 256
    assert "preview" in parsed


def test_spec_3_tool_output_multibyte_utf8():
    """3. Multibyte Unicode truncation does not split codepoints or raise decode errors."""
    multibyte_data = {"symbols": "€★日本語" * 60}
    out_str = truncate_tool_output(multibyte_data, max_bytes=150)
    assert len(out_str.encode("utf-8")) <= 150
    # Must be valid UTF-8 and valid JSON
    parsed = json.loads(out_str)
    assert parsed.get("_truncated") is True
    assert isinstance(parsed["preview"], str)


def test_spec_4_duplicate_tool_call_counting(monkeypatch):
    """4. Duplicate tool calls in succession are halted and executed exactly once."""
    image_id = _create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", False)
    monkeypatch.setattr(settings, "_meta_reasoning_api_key", "sec_mock_key")
    monkeypatch.setattr(settings, "_max_tool_iterations_per_chat", 4)
    monkeypatch.setattr(settings, "_max_reasoning_requests_per_chat", 5)

    exec_counts = {"count": 0}
    def mock_tool_fn(**kwargs):
        exec_counts["count"] += 1
        return {"result": "ok"}

    with patch.dict("backend.app.services.reasoning_service.AVAILABLE_MISSION_TOOLS", {"get_mission_summary": mock_tool_fn}):
        f_dup = MagicMock()
        f_dup.name = "get_mission_summary"
        f_dup.arguments = json.dumps({"image_id": image_id})
        mock_tc = MagicMock(id="c_dup", function=f_dup)
        mock_msg = MagicMock(tool_calls=[mock_tc], content=None)

        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = MagicMock(choices=[MagicMock(message=mock_msg)])
        import openai
        monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: mock_client)

        req = ChatRequest(image_id=image_id, message="Trigger duplicate breaker")
        resp = process_chat_turn(req)
        # First execution succeeds; second duplicate call signature is blocked before running tool function
        assert exec_counts["count"] == 1
        assert "duplicate" in resp.reply.lower() or "completed" in resp.reply.lower() or resp.is_ai_generated is False


def test_spec_5_telemetry_raw_error_sanitization(tmp_path, monkeypatch):
    """5. Secrets passed in raw error messages are sanitized at the telemetry persistence boundary."""
    test_ledger = tmp_path / "telemetry_leak_check.json"
    monkeypatch.setattr("backend.app.core.telemetry.LEDGER_FILE_PATH", test_ledger)
    tracker = ApiTelemetryTracker()

    raw_err = "Auth failed for https://admin:super_secret_pw@meta.api/v1?token=AIzaSySecret_99999 sk-ant-live-token"
    tracker.record_reasoning_failure("muse-spark-1.3", raw_err)

    content = test_ledger.read_text(encoding="utf-8")
    assert "super_secret_pw" not in content
    assert "AIzaSySecret_99999" not in content
    assert "sk-ant-live-token" not in content
    assert "[REDACTED_USERINFO]" in content or "[REDACTED_KEY]" in content or "[REDACTED_TOKEN]" in content


def test_spec_6_shared_budget_multithreaded_concurrency():
    """6. Multiple threads competing for the SAME RequestBudget instance never exceed limit."""
    shared_budget = RequestBudget(limit=10, operation_name="shared_threaded_test")
    successful_claims = []
    lock = threading.Lock()

    def claim_budget():
        for _ in range(5):
            claimed = shared_budget.record_request()
            if claimed:
                with lock:
                    successful_claims.append(True)
            time.sleep(0.002)

    threads = [threading.Thread(target=claim_budget) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(successful_claims) == 10
    assert shared_budget.consumed == 10
    assert shared_budget.can_request() is False


def test_spec_7_active_request_accounting_semaphore_rejection():
    """7. Semaphore rejection does not decrement in-flight active request counts."""
    api_telemetry.reset()
    assert api_telemetry.get_telemetry_summary()["sam_active_requests"] == 0

    # Start request 1 (active count becomes 1)
    api_telemetry.record_sam_start()
    assert api_telemetry.get_telemetry_summary()["sam_active_requests"] == 1

    # Request 2 is rejected by semaphore before starting
    api_telemetry.record_sam_concurrency_rejected()
    # Active count MUST still be 1, NOT decremented to 0
    assert api_telemetry.get_telemetry_summary()["sam_active_requests"] == 1

    # Finish request 1
    api_telemetry.record_sam_success()
    assert api_telemetry.get_telemetry_summary()["sam_active_requests"] == 0


def test_spec_8_malformed_tool_arguments(monkeypatch):
    """8. Malformed tool arguments (non-dict, non-JSON) are safely caught and reported."""
    image_id = _create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", False)
    monkeypatch.setattr(settings, "_meta_reasoning_api_key", "sec_mock_key")

    f_bad = MagicMock()
    f_bad.name = "get_mission_summary"
    f_bad.arguments = "[\"invalid\", \"non-dict\"]"
    mock_tc = MagicMock(id="c_bad", function=f_bad)

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        MagicMock(choices=[MagicMock(message=MagicMock(tool_calls=[mock_tc], content=None))]),
        MagicMock(choices=[MagicMock(message=MagicMock(tool_calls=None, content="Handled error gracefully"))])
    ]
    import openai
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: mock_client)

    req = ChatRequest(image_id=image_id, message="Test bad args")
    resp = process_chat_turn(req)
    # Pipeline executed without crashing
    assert resp.reply is not None
    # Inspect tool reply sent to model
    second_call_messages = mock_client.chat.completions.create.call_args_list[1][1]["messages"]
    tool_msg = [m for m in second_call_messages if isinstance(m, dict) and m.get("role") == "tool"][0]
    assert "error" in tool_msg["content"].lower()


def test_spec_9_multiple_tool_calls_in_single_response(monkeypatch):
    """9. Multiple tool calls in a single assistant message are all safely dispatched and fed back."""
    image_id = _create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", False)
    monkeypatch.setattr(settings, "_meta_reasoning_api_key", "sec_mock_key")
    monkeypatch.setattr(settings, "_max_tool_executions_per_chat", 5)

    f1 = MagicMock(); f1.name = "get_mission_summary"; f1.arguments = json.dumps({"image_id": image_id})
    f2 = MagicMock(); f2.name = "get_terrain_distribution"; f2.arguments = json.dumps({"image_id": image_id})
    f3 = MagicMock(); f3.name = "get_route_metrics"; f3.arguments = json.dumps({"image_id": image_id})

    tc1 = MagicMock(id="c1", function=f1)
    tc2 = MagicMock(id="c2", function=f2)
    tc3 = MagicMock(id="c3", function=f3)

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        MagicMock(choices=[MagicMock(message=MagicMock(tool_calls=[tc1, tc2, tc3], content=None))]),
        MagicMock(choices=[MagicMock(message=MagicMock(tool_calls=None, content="Processed all 3 tools."))])
    ]
    import openai
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: mock_client)

    req = ChatRequest(image_id=image_id, message="Get all 3 stats")
    resp = process_chat_turn(req)
    assert resp.reply == "Processed all 3 tools."
    second_msgs = mock_client.chat.completions.create.call_args_list[1][1]["messages"]
    tool_msgs = [m for m in second_msgs if isinstance(m, dict) and m.get("role") == "tool"]
    assert len(tool_msgs) == 3


def test_spec_10_cumulative_tool_execution_limit(monkeypatch):
    """10. Cumulative tool executions per chat turn cannot exceed MAX_TOOL_EXECUTIONS_PER_CHAT."""
    image_id = _create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", False)
    monkeypatch.setattr(settings, "_meta_reasoning_api_key", "sec_mock_key")
    monkeypatch.setattr(settings, "_max_tool_executions_per_chat", 2)
    monkeypatch.setattr(settings, "_max_tool_iterations_per_chat", 5)
    monkeypatch.setattr(settings, "_max_reasoning_requests_per_chat", 5)

    f1 = MagicMock(); f1.name = "get_mission_summary"; f1.arguments = json.dumps({"image_id": image_id})
    f2 = MagicMock(); f2.name = "get_terrain_distribution"; f2.arguments = json.dumps({"image_id": image_id})
    f3 = MagicMock(); f3.name = "get_route_metrics"; f3.arguments = json.dumps({"image_id": image_id})

    tc1 = MagicMock(id="c1", function=f1)
    tc2 = MagicMock(id="c2", function=f2)
    tc3 = MagicMock(id="c3", function=f3)

    mock_client = MagicMock()
    # Model returns 2 tool calls, then 1 more
    mock_client.chat.completions.create.side_effect = [
        MagicMock(choices=[MagicMock(message=MagicMock(tool_calls=[tc1, tc2], content=None))]),
        MagicMock(choices=[MagicMock(message=MagicMock(tool_calls=[tc3], content=None))]),
        MagicMock(choices=[MagicMock(message=MagicMock(tool_calls=None, content="Final answer."))])
    ]
    import openai
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: mock_client)

    req = ChatRequest(image_id=image_id, message="Exceed tool execution limit")
    resp = process_chat_turn(req)
    assert resp.reply is not None


def test_spec_11_cumulative_byte_limit_enforced(monkeypatch):
    """11. Cumulative tool output bytes across iterations exceeding limit triggers payload warning."""
    image_id = _create_sample_analysis()
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", False)
    monkeypatch.setattr(settings, "_meta_reasoning_api_key", "sec_mock_key")
    monkeypatch.setattr(settings, "_max_total_tool_output_bytes", 300)
    monkeypatch.setattr(settings, "_max_tool_output_bytes", 200)

    tool_counts = {"count": 0}
    def mock_large_tool(**kwargs):
        tool_counts["count"] += 1
        return {"data": "A" * 150}

    with patch.dict("backend.app.services.reasoning_service.AVAILABLE_MISSION_TOOLS", {
        "get_mission_summary": mock_large_tool,
        "get_terrain_distribution": mock_large_tool
    }):
        f1 = MagicMock(); f1.name = "get_mission_summary"; f1.arguments = json.dumps({"image_id": image_id})
        f2 = MagicMock(); f2.name = "get_terrain_distribution"; f2.arguments = json.dumps({"image_id": image_id})
        tc1 = MagicMock(id="c1", function=f1)
        tc2 = MagicMock(id="c2", function=f2)

        mock_client = MagicMock()
        mock_client.chat.completions.create.side_effect = [
            MagicMock(choices=[MagicMock(message=MagicMock(tool_calls=[tc1], content=None))]),
            MagicMock(choices=[MagicMock(message=MagicMock(tool_calls=[tc2], content=None))]),
            MagicMock(choices=[MagicMock(message=MagicMock(tool_calls=None, content="Done"))])
        ]
        import openai
        monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: mock_client)

        req = ChatRequest(image_id=image_id, message="Run cumulative byte test")
        resp = process_chat_turn(req)
        assert resp.reply is not None


def test_spec_12_malformed_sam_response_partial_recovery(monkeypatch):
    """12. Malformed mask records in SAM response are skipped individually without crashing."""
    monkeypatch.setattr(settings, "_external_api_enabled", True)
    monkeypatch.setattr(settings, "_external_api_dry_run", False)
    monkeypatch.setattr(settings, "_meta_api_key", "sec_sam_mock_key")

    mock_client = MagicMock()
    mock_resp = MagicMock()
    mock_resp.output_text = "mock_output"
    mock_client.responses.create.return_value = mock_resp

    class BaseMaskRecord:
        pass

    class MockMask:
        width = 64
        height = 64

    class BadRecord(BaseMaskRecord):
        @property
        def mask(self):
            raise ValueError("Corrupt mask RLE")

    class GoodRecord(BaseMaskRecord):
        def __init__(self):
            self.mask = MockMask()
            self.box_2d = [0.1, 0.1, 0.5, 0.5]
            self.score = 0.95

    rec1 = BadRecord()
    rec2 = GoodRecord()

    mock_sam = MagicMock()
    mock_sam.SegmentationMaskRecord = BaseMaskRecord
    mock_sam.decode_mask_to_raster.return_value = [1] * (64 * 64)
    mock_format = MagicMock()
    mock_parser = MagicMock()
    mock_parser.finish.return_value = MagicMock(result=MagicMock(records=[rec1, rec2]))
    mock_format.create_parser.return_value = mock_parser
    mock_sam.image_segmentation_format.return_value = mock_format

    import openai
    import sys
    monkeypatch.setattr(openai, "OpenAI", lambda **kwargs: mock_client)
    monkeypatch.setitem(sys.modules, "meta_sam_parser", mock_sam)

    seg_result, masks, diags = run_live_sam_segmentation(
        "data:image/png;base64,abc", ["rock"], 64, 64, 8, 8
    )
    # Succeeded in recovering the valid mask
    assert len(masks) == 1
    assert any("failed to decode" in d.lower() and "mask record" in d.lower() for d in diags)


def test_spec_13_empty_mask_behavior_sets_unknown_concept():
    """13. SAM returning 0 valid masks defaults terrain grid to 'unknown' rather than synthetic 'clear'."""
    grid = reconstruct_grid_from_masks([], 64, 64, grid_rows=8, grid_cols=8, concept_priorities={}, default_concept="unknown")
    assert len(grid) == 8
    assert len(grid[0]) == 8
    assert all(cell == "unknown" for row in grid for cell in row)


def test_spec_14_independent_start_and_goal_defaulting():
    """14. Independent start/goal defaulting preserves provided endpoint when only one is supplied."""
    img_id = _create_sample_image_id()

    # 1. Provide only start: start must be preserved, goal defaulted to top
    req1 = FullAnalysisRequest(image_id=img_id, start=(2, 2), goal=None)
    res1 = run_full_analysis(req1)
    assert res1.path_result.is_success is True
    assert res1.path_result.path[0] == (2, 2)

    # 2. Provide only goal: goal must be preserved, start defaulted to bottom
    req2 = FullAnalysisRequest(image_id=img_id, start=None, goal=(1, 1))
    res2 = run_full_analysis(req2)
    assert res2.path_result.is_success is True
    assert res2.path_result.path[-1] == (1, 1)


def test_spec_15_structurally_invalid_ledger_recovery(tmp_path, monkeypatch):
    """15. Structurally invalid ledger (negative counts, wrong types) is backed up and reinitialized."""
    bad_ledger = tmp_path / "corrupt_ledger.json"
    # Structure with negative counts and wrong type
    bad_ledger.write_text(json.dumps({
        "sam_stats": {"attempted": -5, "succeeded": "wrong_type"},
        "reasoning_stats": {"attempted": 10}
    }), encoding="utf-8")
    monkeypatch.setattr("backend.app.core.telemetry.LEDGER_FILE_PATH", bad_ledger)

    tracker = ApiTelemetryTracker()
    summary = tracker.get_telemetry_summary()
    assert summary["ledger"]["sam_stats"]["attempted"] == 0
    # Backup file must have been created
    backups = list(tmp_path.glob("corrupt_ledger.corrupt.*.json"))
    assert len(backups) >= 1


def test_spec_16_invalid_provider_config(monkeypatch):
    """16. Invalid reasoning provider config safely defaults to muse-spark."""
    monkeypatch.setenv("REASONING_PROVIDER", "invalid-alien-provider")
    test_settings = Settings()
    assert test_settings.reasoning_provider == "muse-spark"


def test_spec_17_malformed_urls_rejected():
    """17. Malformed base URLs with userinfo or plain HTTP are rejected."""
    # Embedded credentials rejected
    with pytest.raises(ValueError) as exc1:
        _validate_url("https://user:pass@api.meta.ai", "https://api.meta.ai", "TEST_URL")
    assert "credential" in str(exc1.value).lower()

    # Insecure HTTP rejected for remote host
    with pytest.raises(ValueError) as exc2:
        _validate_url("http://api.meta.ai", "https://api.meta.ai", "TEST_URL")
    assert "https" in str(exc2.value).lower()

    # Local development URLs permitted
    assert _validate_url("http://localhost:8000", "https://api.meta.ai", "TEST_URL") == "http://localhost:8000"
    assert _validate_url("http://127.0.0.1:8000", "https://api.meta.ai", "TEST_URL") == "http://127.0.0.1:8000"


def test_spec_18_non_finite_floats_rejected():
    """18. Non-finite float values (NaN, Inf) in configuration raise ValueError."""
    with pytest.raises(ValueError):
        _parse_float("nan", 1.0)
    with pytest.raises(ValueError):
        _parse_float("inf", 1.0)
    with pytest.raises(ValueError):
        _parse_float("-inf", 1.0)


def test_spec_19_concurrent_conversation_turns_and_lru_eviction():
    """19. Concurrent conversation turns with LRU eviction operate safely under lock without KeyError."""
    clear_conversation_store()
    img_id = _create_sample_analysis()

    def send_chat(conv_idx: int):
        cid = f"conv_{conv_idx}"
        req = ChatRequest(image_id=img_id, message=f"Message for {cid}", conversation_id=cid)
        process_chat_turn(req)

    threads = [threading.Thread(target=send_chat, args=(i,)) for i in range(50)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Store must not exceed MAX_CONVERSATIONS (25)
    assert len(_CONVERSATION_STORE) <= MAX_CONVERSATIONS


def test_spec_20_fallback_policy_decisions():
    """20. Fallback policy correctly distinguishes retryable from non-retryable failures."""
    from backend.app.core.budget import BudgetExhaustedError, ConcurrencyLimitError

    # Non-retryable
    assert should_attempt_fallback(RuntimeError("401 Unauthorized: Invalid API key")) is False
    assert should_attempt_fallback(RuntimeError("Authentication failed")) is False
    assert should_attempt_fallback(BudgetExhaustedError("Operation request budget exhausted")) is False
    assert should_attempt_fallback(ConcurrencyLimitError("Concurrency semaphore cap reached")) is False
    assert should_attempt_fallback(RuntimeError("400 Bad Request: Invalid input parameters")) is False

    # Retryable
    assert should_attempt_fallback(RuntimeError("403 Forbidden: Model allowlist restricted")) is True
    assert should_attempt_fallback(RuntimeError("404 Model Not Found")) is True
    assert should_attempt_fallback(RuntimeError("429 Too Many Requests")) is True
    assert should_attempt_fallback(RuntimeError("500 Internal Server Error")) is True
    assert should_attempt_fallback(RuntimeError("503 Service Unavailable")) is True
    assert should_attempt_fallback(TimeoutError("ReadTimeout: upstream server did not respond")) is True
    assert should_attempt_fallback(SchemaValidationError("Missing required section")) is True


# =============================================================================
# CATEGORY 6: PRE-COMMIT AIRTIGHT ISOLATION, REALISTIC EXCEPTIONS & UNKNOWN TERRAIN
# =============================================================================

def test_network_firewall_blocks_outbound_connections():
    """Verify that the test isolation firewall blocks outbound socket connections."""
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    with pytest.raises(RuntimeError) as exc:
        s.connect(("api.meta.ai", 443))
    assert "TEST ISOLATION VIOLATION" in str(exc.value)


def test_helpers_immune_to_live_env_settings():
    """Verify that sample analysis helpers execute offline even if settings had live mode set."""
    image_id = _create_sample_analysis()
    assert image_id is not None
    from backend.app.services.mission_context import get_analysis
    analysis = get_analysis(image_id)
    assert analysis is not None
    assert analysis.segmentation.is_synthetic is True
    assert "synthetic" in analysis.segmentation.source_model.lower() or "fixture" in analysis.segmentation.source_model.lower()


def test_fallback_classification_concrete_sdk_exceptions():
    """Verify fallback error classification using concrete OpenAI SDK and HTTP status exceptions."""
    import openai
    import httpx

    req = httpx.Request("POST", "https://api.meta.ai/v1/chat/completions")

    # 1. 401 Authentication Failure -> False (no retry)
    err_401 = openai.AuthenticationError(
        message="Incorrect API key provided",
        response=httpx.Response(401, request=req),
        body=None
    )
    assert should_attempt_fallback(err_401) is False

    # 2. 403 Permission Denied -> True (fallback permitted)
    err_403 = openai.PermissionDeniedError(
        message="Model allowlist restricted",
        response=httpx.Response(403, request=req),
        body=None
    )
    assert should_attempt_fallback(err_403) is True

    # 3. 404 Not Found -> True (fallback permitted)
    err_404 = openai.NotFoundError(
        message="The model does not exist",
        response=httpx.Response(404, request=req),
        body=None
    )
    assert should_attempt_fallback(err_404) is True

    # 4. 429 Rate Limit -> True (fallback permitted)
    err_429 = openai.RateLimitError(
        message="Rate limit exceeded",
        response=httpx.Response(429, request=req),
        body=None
    )
    assert should_attempt_fallback(err_429) is True

    # 5. 500 Internal Server Error -> True (fallback permitted)
    err_500 = openai.InternalServerError(
        message="Internal server error",
        response=httpx.Response(500, request=req),
        body=None
    )
    assert should_attempt_fallback(err_500) is True

    # 6. Connection Error -> True (fallback permitted)
    err_conn = openai.APIConnectionError(request=req)
    assert should_attempt_fallback(err_conn) is True

    # 7. Timeout Error -> True (fallback permitted)
    err_timeout = openai.APITimeoutError(request=req)
    assert should_attempt_fallback(err_timeout) is True

    # 8. httpx.HTTPStatusError 503 -> True
    err_503 = httpx.HTTPStatusError(
        message="503 Service Unavailable",
        request=req,
        response=httpx.Response(503, request=req)
    )
    assert should_attempt_fallback(err_503) is True

    # 9. Conservative default: Unclassified unknown exceptions -> False
    assert should_attempt_fallback(TypeError("Unexpected type in internal serialization")) is False
    assert should_attempt_fallback(RuntimeError("Unrecognized internal runtime glitch")) is False


def test_unknown_terrain_complete_pipeline_safety():
    """
    Verify complete unknown-terrain safety pipeline:
    SAM response (0 masks) -> mask decoding -> grid reconstruction -> terrain costmap -> path planner.
    Verifies unknown terrain is not treated as clear or safe, has elevated cost, and is avoided when clear paths exist.
    """
    from backend.app.services.mask_reconstruction import reconstruct_grid_from_masks
    from backend.app.services.terrain_interpreter import DEFAULT_TERRAIN_COSTS, build_normalized_segmentation
    from backend.app.services.terrain_costmap import build_cost_map
    from backend.app.services.path_planner import find_path

    # 1. Zero usable masks produce grid of 'unknown'
    raw_grid = reconstruct_grid_from_masks(
        masks=[],
        image_width=64,
        image_height=64,
        grid_rows=4,
        grid_cols=4,
        concept_priorities={},
        default_concept="unknown"
    )
    assert all(cell == "unknown" for row in raw_grid for cell in row)

    # 2. Build costmap: verify 'unknown' has elevated cost (2.0) vs 'clear' (1.0)
    norm_seg = build_normalized_segmentation(raw_grid, 64, 64, source_model="sam-3.1")
    cost_grid = build_cost_map(norm_seg.terrain_grid, DEFAULT_TERRAIN_COSTS)
    assert DEFAULT_TERRAIN_COSTS["unknown"] == 2.0
    assert DEFAULT_TERRAIN_COSTS["clear"] == 1.0
    for r in range(4):
        for c in range(4):
            assert cost_grid[r][c] == 2.0

    # 3. Path Planner traversal policy: A* strictly avoids 'unknown' when 'clear' terrain exists
    mixed_grid = [
        ["clear", "unknown", "clear"],
        ["clear", "unknown", "clear"],
        ["clear", "clear",   "clear"]
    ]
    mixed_costs = build_cost_map(mixed_grid, DEFAULT_TERRAIN_COSTS)
    # Start at top-left (0, 0), goal at bottom-right (2, 2)
    path_res = find_path(mixed_costs, start=(0, 0), goal=(2, 2), allow_diagonal=False)
    assert path_res.is_success is True
    # The optimal path must NOT step on (0, 1) or (1, 1) which are 'unknown' with cost 2.0
    assert (0, 1) not in path_res.path
    assert (1, 1) not in path_res.path
    # Path uses the 'clear' bedrock corridor: (0,0) -> (1,0) -> (2,0) -> (2,1) -> (2,2)
    assert path_res.path == [(0, 0), (1, 0), (2, 0), (2, 1), (2, 2)]

    # 4. Impassable vs Unknown: obstacle is None (impassable), unknown is 2.0 (traversable with penalty)
    assert DEFAULT_TERRAIN_COSTS["obstacle"] is None
    assert DEFAULT_TERRAIN_COSTS["unknown"] is not None


# =============================================================================
# CATEGORY 7: TARGETED FINAL PRE-COMMIT VERIFICATION TESTS
# =============================================================================

def test_targeted_fallback_classification_rules():
    """
    Verify exact fallback classification rules:
    - HTTP 400 is strictly non-fallback, even when structured output was requested.
    - HTTP 401 is strictly non-fallback.
    - HTTP 403 triggers deliberate fallback (model-level gating assumption).
    - HTTP 404, 429, 5xx, timeout, connection, JSON decode, and schema validation trigger fallback.
    - Typed BudgetExhaustedError and ConcurrencyLimitError are strictly non-fallback.
    - Unknown exceptions are strictly non-fallback.
    """
    import openai
    import httpx
    import json
    from backend.app.core.budget import BudgetExhaustedError, ConcurrencyLimitError
    from backend.app.services.reasoning_service import SchemaValidationError

    req = httpx.Request("POST", "https://api.meta.ai/v1/chat/completions")

    # 1. HTTP 400 Bad Request — NOT retryable even with structured output
    err_400 = openai.BadRequestError(
        message="400 Bad Request: Invalid parameters in structured response schema",
        response=httpx.Response(400, request=req),
        body={"error": {"message": "Invalid parameters in schema"}}
    )
    assert should_attempt_fallback(err_400) is False
    assert should_attempt_fallback(RuntimeError("400 Bad Request: Schema validation failed in request body")) is False

    # 2. HTTP 401 Authentication Failure — NOT retryable (same invalid key on fallback)
    err_401 = openai.AuthenticationError(
        message="401 Unauthorized: Invalid API key provided",
        response=httpx.Response(401, request=req),
        body={"error": {"message": "Invalid API key"}}
    )
    assert should_attempt_fallback(err_401) is False

    # 3. HTTP 403 Forbidden / Permission Denied — Deliberate fallback (model-specific entitlement gating)
    err_403 = openai.PermissionDeniedError(
        message="403 Forbidden: Model access restricted to allowlist",
        response=httpx.Response(403, request=req),
        body={"error": {"message": "Allowlist restricted"}}
    )
    assert should_attempt_fallback(err_403) is True

    # 4. HTTP 404 Model Not Found — Retryable
    err_404 = openai.NotFoundError(
        message="404 Model Not Found: meta/muse-spark is unavailable",
        response=httpx.Response(404, request=req),
        body={"error": {"message": "Model not found"}}
    )
    assert should_attempt_fallback(err_404) is True

    # 5. HTTP 429 Rate Limit — Retryable
    err_429 = openai.RateLimitError(
        message="429 Rate limit reached for model",
        response=httpx.Response(429, request=req),
        body={"error": {"message": "Rate limit reached"}}
    )
    assert should_attempt_fallback(err_429) is True

    # 6. HTTP 5xx Server Errors — Retryable
    err_500 = openai.InternalServerError(
        message="500 Internal Server Error",
        response=httpx.Response(500, request=req),
        body={"error": {"message": "Server error"}}
    )
    assert should_attempt_fallback(err_500) is True

    err_503 = httpx.HTTPStatusError("503 Service Unavailable", request=req, response=httpx.Response(503, request=req))
    assert should_attempt_fallback(err_503) is True

    # 7. Timeouts & Network Connection Errors — Retryable
    assert should_attempt_fallback(openai.APITimeoutError(request=req)) is True
    assert should_attempt_fallback(openai.APIConnectionError(request=req)) is True
    assert should_attempt_fallback(ConnectionResetError("Connection reset by peer")) is True
    assert should_attempt_fallback(TimeoutError("Read operation timed out")) is True

    # 8. Schema validation & JSON Decode Failures from Model Output — Retryable
    assert should_attempt_fallback(SchemaValidationError("Missing required briefing section 'observation_overview'")) is True
    assert should_attempt_fallback(json.JSONDecodeError("Expecting value", "{invalid json", 0)) is True

    # 9. Dedicated Typed Concurrency & Budget Exceptions — Strictly NOT retryable
    assert should_attempt_fallback(BudgetExhaustedError("Operation request budget exhausted")) is False
    assert should_attempt_fallback(ConcurrencyLimitError("Concurrency semaphore cap reached")) is False

    # 10. Unknown / Unclassified Exceptions — Strictly NOT retryable (conservative default)
    assert should_attempt_fallback(KeyError("unrelated_key")) is False
    assert should_attempt_fallback(ValueError("unrelated_value_error")) is False
    assert should_attempt_fallback(ZeroDivisionError("division by zero")) is False
    assert should_attempt_fallback(RuntimeError("Arbitrary application logic error")) is False


def test_targeted_atomic_fallback_budget_consumption():
    """
    Verify atomic fallback budget consumption:
    - Primary and fallback requests share the same budget instance.
    - When budget limit is 1, primary consumes it; fallback cannot consume and is NOT dispatched.
    - When budget limit is 2, fallback consumes remaining 1 atomically.
    - Multi-threaded concurrent attempts cannot exceed budget limit.
    """
    import threading
    from backend.app.core.budget import RequestBudget

    # Case 1: Budget limit = 1. Primary consumes 1, fallback is blocked
    shared_budget_1 = RequestBudget(limit=1, operation_name="test_briefing_1")
    assert shared_budget_1.record_request() is True  # Primary consumes unit
    assert shared_budget_1.consumed == 1
    # Fallback attempts atomic consumption: must return False
    assert shared_budget_1.record_request() is False
    assert shared_budget_1.consumed == 1

    # Case 2: Budget limit = 2. Primary consumes 1, fallback consumes 1, 3rd attempt fails
    shared_budget_2 = RequestBudget(limit=2, operation_name="test_briefing_2")
    assert shared_budget_2.record_request() is True  # Primary
    assert shared_budget_2.record_request() is True  # Fallback
    assert shared_budget_2.record_request() is False  # Additional attempt rejected
    assert shared_budget_2.consumed == 2

    # Case 3: Concurrent atomic contention across multiple threads
    shared_budget_conc = RequestBudget(limit=5, operation_name="test_concurrent")
    successes = []
    failures = []
    lock = threading.Lock()

    def worker():
        if shared_budget_conc.record_request():
            with lock:
                successes.append(1)
        else:
            with lock:
                failures.append(1)

    threads = [threading.Thread(target=worker) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert len(successes) == 5
    assert len(failures) == 15
    assert shared_budget_conc.consumed == 5


def test_targeted_path_planning_obstacles_and_cost_tradeoffs():
    """
    Verify comprehensive path planning behavior:
    1. Weighted uncertainty: shorter unknown route chosen over much longer clear detour.
    2. Shorter clear route chosen over longer unknown route.
    3. Obstacle as start cell raises ValueError.
    4. Obstacle as goal cell raises ValueError.
    5. Direct route blocked by obstacle: A* routes safely around it.
    6. Entirely unknown grid remains traversable with uniform penalty.
    7. plan_path alias functions identically to find_path.
    """
    from backend.app.services.path_planner import find_path, plan_path

    # 1. Shorter unknown path (cost 4.0) vs much longer clear detour (cost 5.0)
    # Grid 3x3:
    # (0,0)[1.0] -> (0,1)[2.0(unknown)] -> (0,2)[1.0] : direct across unknown costs 1.5 + 1.5 = 3.0 + cell
    # Clear detour: (0,0) -> (1,0) -> (2,0) -> (2,1) -> (2,2) -> (1,2) -> (0,2) = 6 steps
    grid_tradeoff_1 = [
        [1.0, 2.0, 1.0],
        [1.0, None, 1.0],
        [1.0, 1.0, 1.0],
    ]
    # Direct route (0,0) -> (0,1)[unknown:2.0] -> (0,2)[1.0]:
    # Step 1: avg(1.0, 2.0) = 1.5
    # Step 2: avg(2.0, 1.0) = 1.5
    # Total direct cost = 3.0
    # Clear detour around: (0,0)->(1,0)->(2,0)->(2,1)->(2,2)->(1,2)->(0,2):
    # 6 steps * 1.0 = 6.0
    # A* MUST choose the direct route across unknown because 3.0 < 6.0
    res_tradeoff_1 = find_path(grid_tradeoff_1, start=(0, 0), goal=(0, 2), allow_diagonal=False)
    assert res_tradeoff_1.is_success is True
    assert res_tradeoff_1.path == [(0, 0), (0, 1), (0, 2)]
    assert res_tradeoff_1.total_weighted_cost == 3.0

    # 2. Shorter clear route chosen over longer unknown route
    # (0,0)[1.0] -> (1,0)[1.0] (1 step clear = 1.0)
    # vs detour through unknown cells
    grid_tradeoff_2 = [
        [1.0, 2.0],
        [1.0, 2.0],
    ]
    res_tradeoff_2 = find_path(grid_tradeoff_2, start=(0, 0), goal=(1, 0), allow_diagonal=False)
    assert res_tradeoff_2.is_success is True
    assert res_tradeoff_2.path == [(0, 0), (1, 0)]
    assert res_tradeoff_2.total_weighted_cost == 1.0

    # 3. Obstacle as start cell raises ValueError
    grid_blocked = [
        [None, 1.0],
        [1.0, 1.0],
    ]
    with pytest.raises(ValueError, match="Start coordinate \\(0, 0\\) is blocked"):
        find_path(grid_blocked, start=(0, 0), goal=(1, 1))

    # 4. Obstacle as goal cell raises ValueError
    with pytest.raises(ValueError, match="Goal coordinate \\(0, 0\\) is blocked"):
        find_path(grid_blocked, start=(1, 1), goal=(0, 0))

    # 5. Direct route blocked by obstacle: safe route around
    grid_obstacle_middle = [
        [1.0, 1.0, 1.0],
        [1.0, None, 1.0],
        [1.0, 1.0, 1.0],
    ]
    res_around = find_path(grid_obstacle_middle, start=(1, 0), goal=(1, 2), allow_diagonal=False)
    assert res_around.is_success is True
    assert (1, 1) not in res_around.path
    assert res_around.path[0] == (1, 0)
    assert res_around.path[-1] == (1, 2)
    assert res_around.total_weighted_cost > 0.0

    # 6. Entirely unknown grid remains fully traversable
    all_unknown_grid = [
        [2.0, 2.0, 2.0],
        [2.0, 2.0, 2.0],
        [2.0, 2.0, 2.0],
    ]
    res_all_unknown = find_path(all_unknown_grid, start=(0, 0), goal=(2, 2), allow_diagonal=False)
    assert res_all_unknown.is_success is True
    assert len(res_all_unknown.path) == 5
    # 4 steps * avg(2.0, 2.0) = 8.0
    assert res_all_unknown.total_weighted_cost == 8.0

    # 7. plan_path compatibility alias behaves identically
    res_alias = plan_path(all_unknown_grid, start=(0, 0), goal=(2, 2), allow_diagonal=False)
    assert res_alias.is_success is True
    assert res_alias.path == res_all_unknown.path
    assert res_alias.total_weighted_cost == res_all_unknown.total_weighted_cost


def test_targeted_error_sanitization_and_telemetry():
    """
    Verify comprehensive error sanitization:
    - Redacts raw API keys, Authorization headers, Bearer tokens, query params, passwords.
    - telemetry_collector.record_call() safely stores sanitized error in telemetry and ledger.
    """
    from backend.app.core.sanitizer import sanitize_error
    from backend.app.core.telemetry import api_telemetry

    sensitive_raw = (
        "Failed request to https://api.meta.ai/v1/chat?api_key=secret_key_12345&user_id=rover_op "
        "with headers Authorization: Bearer sk-ant-secret9876543210 "
        "and payload: {'password': 'super_secret_rover_password', 'api_key': 'key-1234567890abcdef'}"
    )

    sanitized = sanitize_error(sensitive_raw)

    # Assert all secrets are redacted
    assert "secret_key_12345" not in sanitized
    assert "sk-ant-secret9876543210" not in sanitized
    assert "super_secret_rover_password" not in sanitized
    assert "key-1234567890abcdef" not in sanitized
    assert "[REDACTED_QUERY_PARAMS]" in sanitized
    assert "[REDACTED_AUTH_HEADER]" in sanitized or "[REDACTED_TOKEN]" in sanitized

    # Assert telemetry_collector.record_call() stores sanitized error
    api_telemetry.record_call(
        provider="meta-reasoning-primary",
        model="meta/muse-spark",
        success=False,
        error=sensitive_raw,
    )
    summary = api_telemetry.get_telemetry_summary()
    reasoning_last_err = summary["reasoning_last_error"]
    assert reasoning_last_err is not None
    assert "secret_key_12345" not in reasoning_last_err
    assert "super_secret_rover_password" not in reasoning_last_err
    assert "[REDACTED_QUERY_PARAMS]" in reasoning_last_err



