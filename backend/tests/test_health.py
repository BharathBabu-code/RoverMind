import pytest
from fastapi.testclient import TestClient
from backend.app.main import app

# Create a test client that interacts with the FastAPI app in-memory
client = TestClient(app)

def test_health_check_returns_200_ok() -> None:
    """Verify the health endpoint is reachable and returns HTTP 200."""
    response = client.get("/health")
    assert response.status_code == 200

def test_health_check_returns_expected_json() -> None:
    """Verify the health payload structure and content."""
    response = client.get("/health")
    data = response.json()
    
    assert "status" in data
    assert "service" in data
    assert data["status"] == "ok"
    assert data["service"] == "RoverMind API"

def test_health_check_does_not_leak_secrets(monkeypatch: pytest.MonkeyPatch) -> None:
    """
    Ensure the health endpoint does not accidentally dump environment variables.
    
    Testing Limitation: This tests the application logic via TestClient in-memory. 
    It does not test network-level or infrastructure-level leaks (like an Nginx proxy 
    misconfiguration returning 500 pages with environment traces).
    """
    dummy_secret = "DUMMY_SECRET_SUPER_SECRET_KEY_12345"
    
    # Inject the dummy secret into the environment
    monkeypatch.setenv("META_API_KEY", dummy_secret)
    
    # Make the request
    response = client.get("/health")
    
    # Assert the exact dummy secret is not present in the raw string response
    assert dummy_secret not in response.text