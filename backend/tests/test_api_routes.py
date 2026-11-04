import io
import pytest
from fastapi.testclient import TestClient
from PIL import Image
from backend.app.main import app

client = TestClient(app)


def test_health_route():
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert data["service"] == "RoverMind API"


def test_config_route():
    res = client.get("/config")
    assert res.status_code == 200
    data = res.json()
    assert "is_meta_api_configured" in data
    assert "offline_mode" in data
    assert "meta_model" in data


def test_load_sample_and_full_analysis():
    # Load sample image
    res = client.post("/images/load-sample")
    assert res.status_code == 200
    meta = res.json()["metadata"]
    image_id = meta["image_id"]
    assert meta["width"] == 1648
    assert meta["height"] == 1200

    # Run analysis
    analysis_res = client.post(
        "/analysis/run",
        json={
            "image_id": image_id,
            "grid_downsample_factor": 32,
            "allow_diagonal": True
        }
    )
    assert analysis_res.status_code == 200
    data = analysis_res.json()
    assert data["image_id"] == image_id
    assert "segmentation" in data
    assert "costmap" in data
    assert "path_result" in data
    assert data["path_result"]["is_success"] is True
    assert len(data["path_result"]["path"]) > 0


def test_find_path_direct_grid():
    grid = [
        [1.0, 1.0, 1.0],
        [None, None, 1.0],
        [1.0, 1.0, 1.0]
    ]
    res = client.post(
        "/planning/find-path",
        json={
            "cost_grid": grid,
            "start": [0, 0],
            "goal": [2, 0],
            "allow_diagonal": False
        }
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_success"] is True
    assert data["path"] == [[0, 0], [0, 1], [0, 2], [1, 2], [2, 2], [2, 1], [2, 0]]


def test_root_serves_frontend():
    res = client.get("/")
    assert res.status_code == 200
    assert "RoverMind" in res.text

