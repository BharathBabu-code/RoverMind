import io
import uuid
import base64
import warnings
import threading
from collections import OrderedDict
from typing import Dict, Optional, Tuple, Any
from pathlib import Path
from PIL import Image, UnidentifiedImageError

from backend.app.schemas.models import ImageMetadata

# Set Pillow maximum pixel ceiling to 25 Megapixels to prevent decompression bombs (DoS)
MAX_IMAGE_PIXELS = 25_000_000
Image.MAX_IMAGE_PIXELS = MAX_IMAGE_PIXELS

# Maximum allowable file size (20 MB) and dimension (8192px)
MAX_FILE_SIZE = 20 * 1024 * 1024
MAX_DIMENSION = 8192

# Dual-bounded in-memory session image storage:
# 1. Entry limit: MAX_STORE_CAPACITY = 25 frames
# 2. Memory budget: MAX_TOTAL_STORE_BYTES = 100 MB aggregate RAM ceiling
MAX_STORE_CAPACITY = 25
MAX_TOTAL_STORE_BYTES = 100 * 1024 * 1024
_STORE_LOCK = threading.Lock()
_IMAGE_STORE: OrderedDict[str, Tuple[bytes, ImageMetadata]] = OrderedDict()


def validate_and_store_image(file_bytes: bytes, original_filename: str) -> ImageMetadata:
    """
    Validates uploaded image bytes using Pillow, extracts verified metadata,
    and stores it in the in-memory image registry with bounded LRU eviction.
    """
    if not file_bytes:
        raise ValueError("Uploaded file payload is empty.")

    if len(file_bytes) > MAX_FILE_SIZE:
        raise ValueError(f"File size ({len(file_bytes)} bytes) exceeds maximum limit of {MAX_FILE_SIZE} bytes.")

    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            # First pass: verify structure
            with Image.open(io.BytesIO(file_bytes)) as img:
                img.verify()
    except Image.DecompressionBombError:
        raise ValueError("Image pixel count exceeds maximum allowable decompression ceiling (decompression bomb detected).")
    except Image.DecompressionBombWarning:
        raise ValueError("Image pixel count triggers decompression bomb warning ceiling.")
    except UnidentifiedImageError:
        raise ValueError("File content is not a recognized or supported image format.")
    except Exception as e:
        raise ValueError(f"Image verification failed: {e}")

    # Second pass: read dimensions, format, and verify raster decodability
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(file_bytes)) as img:
                width, height = img.size
                img_format = img.format
                # Check for truncated or malformed scanline data
                img.load()
    except (Image.DecompressionBombError, Image.DecompressionBombWarning):
        raise ValueError("Image pixel count exceeds maximum allowable decompression ceiling (decompression bomb detected).")
    except (OSError, SyntaxError) as e:
        raise ValueError(f"Image data is corrupted or truncated: {e}")
    except Exception as e:
        raise ValueError(f"Could not read image properties: {e}")

    if width <= 0 or height <= 0:
        raise ValueError("Image dimensions must be positive integers.")

    if width > MAX_DIMENSION or height > MAX_DIMENSION:
        raise ValueError(f"Image dimension ({width}x{height}) exceeds maximum supported size ({MAX_DIMENSION}x{MAX_DIMENSION}).")

    format_to_mime = {
        "JPEG": "image/jpeg",
        "PNG": "image/png"
    }

    if img_format not in format_to_mime:
        raise ValueError(f"Unsupported image format: {img_format}. Only PNG and JPEG are supported.")

    mime_type = format_to_mime[img_format]
    image_id = str(uuid.uuid4())
    safe_filename = Path(original_filename).name.strip() or "rover_image.png"

    metadata = ImageMetadata(
        image_id=image_id,
        filename=safe_filename,
        width=width,
        height=height,
        mime_type=mime_type,
        file_size_bytes=len(file_bytes)
    )

    with _STORE_LOCK:
        # Enforce dual-bounded LRU eviction:
        # Evict oldest entries if capacity >= MAX_STORE_CAPACITY OR total bytes exceeds MAX_TOTAL_STORE_BYTES
        current_bytes = sum(len(item[0]) for item in _IMAGE_STORE.values())
        while _IMAGE_STORE and (
            len(_IMAGE_STORE) >= MAX_STORE_CAPACITY
            or (current_bytes + len(file_bytes)) > MAX_TOTAL_STORE_BYTES
        ):
            _, (evicted_bytes, _) = _IMAGE_STORE.popitem(last=False)
            current_bytes -= len(evicted_bytes)

        _IMAGE_STORE[image_id] = (file_bytes, metadata)

    return metadata


def get_image_bytes(image_id: str) -> Optional[bytes]:
    """Retrieves raw image bytes by image_id with LRU touch."""
    with _STORE_LOCK:
        item = _IMAGE_STORE.get(image_id)
        if item:
            _IMAGE_STORE.move_to_end(image_id)
            return item[0]
        return None


def get_image_metadata(image_id: str) -> Optional[ImageMetadata]:
    """Retrieves image metadata by image_id with LRU touch."""
    with _STORE_LOCK:
        item = _IMAGE_STORE.get(image_id)
        if item:
            _IMAGE_STORE.move_to_end(image_id)
            return item[1]
        return None


def get_image_data_url(image_id: str) -> str:
    """Returns Base64 data URL for an stored image."""
    with _STORE_LOCK:
        item = _IMAGE_STORE.get(image_id)
        if not item:
            raise KeyError(f"Image ID '{image_id}' not found.")
        _IMAGE_STORE.move_to_end(image_id)
        raw_bytes, meta = item
    b64 = base64.b64encode(raw_bytes).decode("utf-8")
    return f"data:{meta.mime_type};base64,{b64}"


def clear_image_store() -> None:
    """Clears in-memory storage."""
    with _STORE_LOCK:
        _IMAGE_STORE.clear()
