import pytest
from pathlib import Path
from backend.experiments.test_sam_integration import (
    process_local_image,
    count_foreground_pixels,
    extract_response_text
)

def test_process_local_image_png(tmp_path: Path) -> None:
    from PIL import Image
    img_path = tmp_path / "test.png"
    img = Image.new("RGB", (10, 5), color="red")
    img.save(img_path, format="PNG")
    
    result = process_local_image(str(img_path))
    assert result["width"] == 10
    assert result["height"] == 5
    assert result["mime_type"] == "image/png"

def test_process_local_image_mismatched_extension(tmp_path: Path) -> None:
    from PIL import Image
    # Save a PNG but name it .jpg
    img_path = tmp_path / "mismatch.jpg"
    img = Image.new("RGB", (10, 5), color="blue")
    img.save(img_path, format="PNG")
    
    result = process_local_image(str(img_path))
    assert result["mime_type"] == "image/png"

def test_process_local_image_unsupported_format(tmp_path: Path) -> None:
    from PIL import Image
    img_path = tmp_path / "test.bmp"
    img = Image.new("RGB", (10, 5), color="green")
    img.save(img_path, format="BMP")
    
    with pytest.raises(ValueError, match="Unsupported image format: BMP"):
        process_local_image(str(img_path))

def test_process_local_image_invalid_file(tmp_path: Path) -> None:
    file_path = tmp_path / "not_an_image.txt"
    file_path.write_text("This is text, not an image.")
    with pytest.raises(ValueError, match="not a valid or supported image"):
        process_local_image(str(file_path))

def test_count_foreground_pixels_success() -> None:
    # 4 bytes (2x2 mask): 2 background (0x00), 2 foreground (0x01)
    raster = b"\x00\x01\x00\x01"
    assert count_foreground_pixels(raster, expected_length=4) == 2

def test_count_foreground_pixels_non_binary() -> None:
    # Invalid raster containing 0xFF instead of 0x01
    raster = b"\x00\x01\x00\xff"
    with pytest.raises(ValueError, match="contains non-binary values"):
        count_foreground_pixels(raster, expected_length=4)

def test_count_foreground_pixels_dimension_mismatch() -> None:
    raster = b"\x00\x01"
    with pytest.raises(ValueError, match="does not match expected geometry"):
        count_foreground_pixels(raster, expected_length=4)

def test_extract_response_text_output_text() -> None:
    class MockResponse:
        output_text = "sam_tokens"
    assert extract_response_text(MockResponse()) == "sam_tokens"

def test_extract_response_text_empty_string() -> None:
    class MockResponse:
        output_text = "   "
    with pytest.raises(ValueError, match="non-empty response string"):
        extract_response_text(MockResponse())

def test_extract_response_text_invalid_type() -> None:
    class MockResponse:
        output_text = 12345
    with pytest.raises(ValueError, match="non-empty response string"):
        extract_response_text(MockResponse())