import io
import pytest
from PIL import Image
from fastapi.testclient import TestClient

from backend.app.main import app, ALLOWED_ORIGINS
from backend.app.services.image_service import (
    validate_and_store_image,
    get_image_metadata,
    clear_image_store,
    MAX_STORE_CAPACITY,
    MAX_IMAGE_PIXELS
)
from backend.app.services.mask_reconstruction import (
    decode_and_align_mask,
    MAX_MASK_DIMENSION,
    MAX_MASK_PIXELS
)


@pytest.fixture(autouse=True)
def clean_store():
    clear_image_store()
    yield
    clear_image_store()


def create_test_image(width: int = 64, height: int = 64, fmt: str = "PNG") -> bytes:
    buf = io.BytesIO()
    img = Image.new("RGB", (width, height), color=(200, 100, 50))
    img.save(buf, format=fmt)
    return buf.getvalue()


def test_cors_security_headers():
    client = TestClient(app)
    # Test with an allowed origin
    resp = client.options(
        "/api/health",
        headers={
            "Origin": "http://localhost:5173",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert resp.status_code == 200
    assert resp.headers.get("access-control-allow-origin") == "http://localhost:5173"
    assert resp.headers.get("access-control-allow-credentials") == "true"

    # Verify origin is in explicitly defined allowed origins list
    assert "http://localhost:5173" in ALLOWED_ORIGINS
    assert "*" not in ALLOWED_ORIGINS


def test_filename_path_traversal_sanitization():
    raw = create_test_image(32, 32)
    meta = validate_and_store_image(raw, "../../../etc/shadow.png")
    assert "/" not in meta.filename
    assert "\\" not in meta.filename
    assert meta.filename == "shadow.png"

    meta2 = validate_and_store_image(raw, "..\\..\\windows\\system32\\cmd.png")
    assert meta2.filename == "cmd.png"


def test_image_store_lru_capacity_bounded():
    raw = create_test_image(32, 32)
    image_ids = []

    # Insert more than MAX_STORE_CAPACITY images
    for i in range(MAX_STORE_CAPACITY + 5):
        meta = validate_and_store_image(raw, f"test_{i}.png")
        image_ids.append(meta.image_id)

    # First 5 images should have been evicted
    for evicted_id in image_ids[:5]:
        assert get_image_metadata(evicted_id) is None

    # Last MAX_STORE_CAPACITY images should still be present
    for retained_id in image_ids[5:]:
        assert get_image_metadata(retained_id) is not None


def test_decompression_bomb_prevention(monkeypatch):
    raw = create_test_image(32, 32)
    # Lower the pixel ceiling temporarily to test decompression bomb protection
    import backend.app.services.image_service as img_svc
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 500)

    with pytest.raises(ValueError, match="decompression bomb"):
        validate_and_store_image(raw, "bomb.png")


def test_mask_reconstruction_dimension_ceiling():
    class MockMask:
        width = MAX_MASK_DIMENSION + 100
        height = 100

    class MockRecord:
        mask = MockMask()
        object_id = "malicious_obj"

    # Should safely reject oversized mask without memory explosion
    decoded = decode_and_align_mask(MockRecord(), "obstacle", 100, 100)
    assert decoded is None


def test_internal_error_sanitization():
    client = TestClient(app)
    # Upload an empty / corrupt payload
    resp = client.post("/api/images/upload", files={"file": ("corrupt.png", b"", "image/png")})
    assert resp.status_code == 400
    assert "empty" in resp.json()["detail"].lower()


def test_http_security_headers():
    client = TestClient(app)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


def test_image_store_byte_budget_eviction(monkeypatch):
    import backend.app.services.image_service as img_svc
    raw = create_test_image(32, 32)
    # Set byte budget to hold only ~2 images of size len(raw)
    monkeypatch.setattr(img_svc, "MAX_TOTAL_STORE_BYTES", int(len(raw) * 2.5))

    meta1 = validate_and_store_image(raw, "img1.png")
    meta2 = validate_and_store_image(raw, "img2.png")
    # Both should fit
    assert get_image_metadata(meta1.image_id) is not None
    assert get_image_metadata(meta2.image_id) is not None

    # Storing a 3rd image must evict img1 to stay under byte budget
    meta3 = validate_and_store_image(raw, "img3.png")
    assert get_image_metadata(meta1.image_id) is None
    assert get_image_metadata(meta2.image_id) is not None
    assert get_image_metadata(meta3.image_id) is not None


def test_truncated_image_rejection():
    raw = create_test_image(64, 64)
    # Truncate image bytes midway through scanline data
    truncated = raw[: len(raw) // 2]
    with pytest.raises(ValueError, match="(?i)corrupted|truncated|not a recognized|verification failed"):
        validate_and_store_image(truncated, "truncated.png")
