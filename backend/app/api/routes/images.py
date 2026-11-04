import io
from pathlib import Path
from fastapi import APIRouter, UploadFile, File, HTTPException, Response
from backend.app.schemas.models import ImageUploadResponse, ImageMetadata
from backend.app.services.image_service import (
    validate_and_store_image,
    get_image_bytes,
    get_image_metadata
)
from backend.app.core.config import ROOT_DIR

router = APIRouter(prefix="/images", tags=["Images"])


@router.post("/upload", response_model=ImageUploadResponse)
async def upload_image(file: UploadFile = File(...)) -> ImageUploadResponse:
    """
    Accepts an uploaded Mars rover image (JPEG or PNG), validates format, dimensions,
    and integrity, and registers it in the backend memory store.
    """
    try:
        content = await file.read()
        metadata = validate_and_store_image(content, file.filename or "upload.png")
        return ImageUploadResponse(
            success=True,
            metadata=metadata,
            message="Image successfully validated and stored."
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception:
        raise HTTPException(status_code=500, detail="Image upload and validation encountered an internal server error.")


@router.get("/{image_id}/metadata", response_model=ImageMetadata)
async def get_metadata(image_id: str) -> ImageMetadata:
    """Retrieves image dimensions and properties for an active image ID."""
    meta = get_image_metadata(image_id)
    if not meta:
        raise HTTPException(status_code=404, detail=f"Image ID '{image_id}' not found.")
    return meta


@router.get("/{image_id}/raw")
async def get_raw_image(image_id: str) -> Response:
    """Streams the raw binary bytes of the active image."""
    raw = get_image_bytes(image_id)
    meta = get_image_metadata(image_id)
    if not raw or not meta:
        raise HTTPException(status_code=404, detail=f"Image ID '{image_id}' not found.")
    return Response(content=raw, media_type=meta.mime_type)


@router.post("/load-sample", response_model=ImageUploadResponse)
async def load_sample_rover_image() -> ImageUploadResponse:
    """Loads the authentic sample rover image from repository root for instant exploration."""
    sample_path = ROOT_DIR / "rover_image.png"
    if not sample_path.exists():
        raise HTTPException(status_code=404, detail="Default sample rover image not found on disk.")
    
    with open(sample_path, "rb") as f:
        content = f.read()

    try:
        metadata = validate_and_store_image(content, "rover_image.png")
        return ImageUploadResponse(
            success=True,
            metadata=metadata,
            message="Sample rover image loaded and validated."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed loading sample image: {str(e)}")
