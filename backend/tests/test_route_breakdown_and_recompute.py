import pytest
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.services.route_breakdown import calculate_route_cost_breakdown
from backend.app.core.telemetry import api_telemetry
from backend.app.schemas.models import FullAnalysisRequest
from backend.app.services.analysis_orchestrator import run_full_analysis

client = TestClient(app)


def test_route_breakdown_reconciliation():
    """Verifies that calculate_route_cost_breakdown reconciles sum of contributions with total cost."""
    # 3x3 grid:
    # (0,0) clear=1.0, (0,1) rocky=3.0, (0,2) clear=1.0
    # (1,0) loose=5.0, (1,1) clear=1.0, (1,2) unknown=2.0
    # (2,0) clear=1.0, (2,1) clear=1.0, (2,2) clear=1.0
    terrain_grid = [
        ["clear", "rocky", "clear"],
        ["loose", "clear", "unknown"],
        ["clear", "clear", "clear"]
    ]
    cost_grid = [
        [1.0, 3.0, 1.0],
        [5.0, 1.0, 2.0],
        [1.0, 1.0, 1.0]
    ]
    # Path from (2, 0) -> (1, 1) [diagonal] -> (0, 2) [diagonal]
    import math
    path = [(2, 0), (1, 1), (0, 2)]
    # step 1: (2,0) to (1,1) is diagonal -> dist = sqrt(2), cost = 1.0 -> sqrt(2)*1.0 = 1.4142
    # step 2: (1,1) to (0,2) is diagonal -> dist = sqrt(2), cost = 1.0 -> sqrt(2)*1.0 = 1.4142
    expected_total = 2 * math.sqrt(2) * 1.0

    breakdown = calculate_route_cost_breakdown(
        path=path,
        terrain_grid=terrain_grid,
        cost_grid=cost_grid,
        reported_total_cost=expected_total
    )

    assert breakdown.reconciled is True
    assert breakdown.cardinal_steps_count == 0
    assert breakdown.diagonal_steps_count == 2
    assert breakdown.clear_cells_count == 3
    assert abs(breakdown.total_calculated_cost - expected_total) < 1e-3


def test_recompute_endpoint_flow():
    """Tests the /api/planning/recompute endpoint with custom terrain costs."""
    # 1. Ingest sample
    sample_resp = client.post("/api/images/load-sample")
    assert sample_resp.status_code == 200
    img_id = sample_resp.json()["metadata"]["image_id"]

    analysis = run_full_analysis(FullAnalysisRequest(
        image_id=img_id,
        grid_downsample_factor=24,
        allow_diagonal=True
    ))

    # 2. Recompute with elevated rocky terrain cost
    resp = client.post("/api/planning/recompute", json={
        "image_id": img_id,
        "terrain_costs": {
            "rocky": 12.0,
            "loose": 18.0
        },
        "allow_diagonal": True
    })

    assert resp.status_code == 200
    data = resp.json()
    assert data["image_id"] == img_id
    assert data["costmap"]["terrain_costs"]["rocky"] == 12.0
    assert data["costmap"]["terrain_costs"]["loose"] == 18.0
    assert data["path_result"]["is_success"] is True
    assert data["breakdown"]["reconciled"] is True


def test_recompute_endpoint_rejects_unblocking_obstacle():
    """Tests that unblocking obstacle terrain is rejected with a 400 error."""
    sample_resp = client.post("/api/images/load-sample")
    assert sample_resp.status_code == 200
    img_id = sample_resp.json()["metadata"]["image_id"]

    run_full_analysis(FullAnalysisRequest(image_id=img_id, grid_downsample_factor=24))

    resp = client.post("/api/planning/recompute", json={
        "image_id": img_id,
        "terrain_costs": {
            "obstacle": 1.0  # Invalid!
        }
    })

    assert resp.status_code == 400
    assert "Obstacle terrain cannot be made traversable" in resp.json()["detail"]


def test_config_status_reports_truthful_telemetry():
    """Tests that /api/config reports not_configured when keys are absent."""
    resp = client.get("/api/config")
    assert resp.status_code == 200
    data = resp.json()
    # When keys are absent, statuses must be 'not_configured'
    if not data["is_meta_api_configured"]:
        assert data["sam_status"] == "not_configured"
        assert data["active_segmentation_source"] == "offline-synthetic-fixture"
    if not data["is_reasoning_api_configured"]:
        assert data["reasoning_status"] == "not_configured"
        assert data["active_reasoning_source"] == "deterministic-rule-engine"
