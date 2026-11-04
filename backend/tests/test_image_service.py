import io
import pytest
from PIL import Image
from backend.app.services.image_service import (
    validate_and_store_image,
    get_image_bytes,
    get_image_metadata,
    clear_image_store
)


def test_validate_and_store_png():
    clear_image_store()
    img = Image.new("RGB", (64, 48), color="red")
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    content = buf.getvalue()

    meta = validate_and_store_image(content, "test.png")
    assert meta.width == 64
    assert meta.height == 48
    assert meta.mime_type == "image/png"
    assert meta.filename == "test.png"

    retrieved = get_image_bytes(meta.image_id)
    assert retrieved == content


def test_validate_and_store_jpeg():
    clear_image_store()
    img = Image.new("RGB", (32, 32), color="blue")
    buf = io.BytesIO()
    img.save(buf, format="JPEG")
    content = buf.getvalue()

    meta = validate_and_store_image(content, "mars.jpg")
    assert meta.width == 32
    assert meta.height == 32
    assert meta.mime_type == "image/jpeg"


def test_reject_unsupported_format():
    clear_image_store()
    img = Image.new("RGB", (16, 16), color="green")
    buf = io.BytesIO()
    img.save(buf, format="BMP")
    content = buf.getvalue()

    with pytest.raises(ValueError, match="Unsupported image format"):
        validate_and_store_image(content, "test.bmp")


def test_reject_corrupt_data():
    clear_image_store()
    with pytest.raises(ValueError, match="not a recognized or supported"):
        validate_and_store_image(b"not an image", "test.png")
