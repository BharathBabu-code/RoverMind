import sys
import base64
from pathlib import Path
from typing import Any, Dict

from PIL import Image, UnidentifiedImageError

# Configuration encapsulation
from backend.app.core.config import settings

def process_local_image(image_path: str) -> Dict[str, Any]:
    """
    Loads an image, verifies its internal integrity using Pillow's format detector,
    determines the MIME type securely (ignoring file extensions), and converts to Base64.
    """
    path = Path(image_path)
    if not path.is_file():
        raise FileNotFoundError(f"Image not found: {image_path}")

    try:
        with Image.open(path) as img:
            img.verify()
    except UnidentifiedImageError:
        raise ValueError(f"File is not a valid or supported image: {image_path}")
    except Exception as e:
        raise ValueError(f"Error reading image file: {e}")

    # Re-open to read properties since verify() restricts the file pointer
    with Image.open(path) as img:
        width = img.width
        height = img.height
        img_format = img.format

    format_to_mime = {
        "JPEG": "image/jpeg",
        "PNG": "image/png"
    }
    
    if img_format not in format_to_mime:
        raise ValueError(f"Unsupported image format: {img_format}. Must be JPEG or PNG.")
        
    mime_type = format_to_mime[img_format]

    with open(path, "rb") as f:
        b64_data = base64.b64encode(f.read()).decode("utf-8")

    return {
        "width": width,
        "height": height,
        "mime_type": mime_type,
        "data_url": f"data:{mime_type};base64,{b64_data}"
    }

def extract_response_text(response: Any) -> str:
    """
    Safely extracts response text from the SDK response.
    Requires a non-empty string; rejects arbitrary objects.
    """
    text = ""
    if hasattr(response, "output_text") and response.output_text is not None:
        text = response.output_text
    elif hasattr(response, "output") and response.output:
        try:
            text = response.output[0].content[0].text
        except (IndexError, AttributeError):
            pass
            
    if not isinstance(text, str) or not text.strip():
        raise ValueError("Response text is empty or not a valid string.")
        
    return str(text)

def count_foreground_pixels(raster: bytes, expected_length: int) -> int:
    """
    Counts foreground pixels based on the verified 1-byte-per-pixel flat array.
    0 = background, non-zero = foreground.
    """
    if len(raster) != expected_length:
        raise ValueError(f"Raster length {len(raster)} does not match expected geometry ({expected_length}).")
    return sum(1 for byte in raster if byte != 0)

def run_experiment(image_path: str, prompt: str) -> None:
    try:
        import openai
        import meta_sam_parser as sam
    except ImportError as e:
        print(f"Error: Missing required API dependency. {e}")
        sys.exit(1)

    print("--- SAM 3.1 Integration Experiment ---")
    print(f"Target Image : {image_path}")
    print(f"Concept      : '{prompt}'")
    print(f"Model        : sam-3.1")

    if not settings.is_meta_api_configured or not settings.meta_api_key:
        print("Error: META_API_KEY is not configured in the root .env file.")
        sys.exit(1)

    try:
        img_info = process_local_image(image_path)
        print(f"Image Size   : {img_info['width']}w x {img_info['height']}h")
        print(f"MIME Type    : {img_info['mime_type']}")
    except Exception as e:
        print(f"Image Error  : {e}")
        sys.exit(1)

    client = openai.OpenAI(
        base_url="https://api.meta.ai/v1",
        api_key=settings.meta_api_key
    )

    print("\nStatus       : Sending request to SAM 3.1 (Non-streaming)...")
    try:
        response = client.responses.create(
            model="sam-3.1",
            input=[
                {
                    "type": "message",
                    "role": "user",
                    "content": [
                        {"type": "input_text", "text": prompt},
                        {"type": "input_image", "image_url": img_info['data_url']},
                    ],
                },
            ],
        )
        response_text = extract_response_text(response)
        print(f"Status       : Received response payload ({len(response_text)} chars).")
    except Exception as e:
        print(f"API Error    : Request failed - {e}")
        sys.exit(1)

    print("Status       : Parsing response...")
    try:
        response_format = sam.image_segmentation_format()
        parser = response_format.create_parser()
        parser.push(response_text)
        finished = parser.finish(sam.CompletedOutcome())
        result = finished.result
    except Exception as e:
        print(f"Parser Error : Failed to parse SAM tokens - {e}")
        sys.exit(1)

    print("\n--- Parsing Diagnostics ---")
    diagnostics = getattr(result, "diagnostics", [])
    print(f"Diagnostics  : {diagnostics if diagnostics else 'None'}")

    outcome = getattr(result, "outcome", None)
    outcome_status = getattr(outcome, "status", "unknown")
    print(f"Outcome      : {outcome_status}")
    
    if outcome_status != "completed":
        print("Error        : Parsing was unsuccessful. Halting evaluation.")
        sys.exit(1)

    records = getattr(result, "records", [])
    print(f"Total Records: {len(records)}")

    mask_records = [r for r in records if isinstance(r, sam.SegmentationMaskRecord)]
    print(f"Mask Records : {len(mask_records)}")

    if not mask_records:
        print("\nSummary      : Successfully parsed, but 0 masks were returned.")
        return

    decoded_success = 0
    decoded_failed = 0

    for idx, record in enumerate(mask_records):
        print(f"\n--- Mask {idx + 1} ---")
        obj_id = getattr(record, "object_id", "Unknown")
        print(f"Object ID    : {obj_id}")

        mask = getattr(record, "mask", None)
        if not mask:
            print("Decoding     : Failed (No mask token found on record)")
            decoded_failed += 1
            continue
            
        bounds = getattr(record, "bounds", None)
        frame = getattr(record, "frame", None)
        if bounds:
            print(f"Bounds       : {bounds}")
        if frame:
            print(f"Frame        : {frame}")

        try:
            m_width = getattr(mask, "width", None)
            m_height = getattr(mask, "height", None)

            if type(m_width) is bool or not isinstance(m_width, int) or m_width <= 0:
                raise ValueError(f"Invalid mask width: {m_width}")
            if type(m_height) is bool or not isinstance(m_height, int) or m_height <= 0:
                raise ValueError(f"Invalid mask height: {m_height}")

            print(f"Dimensions   : {m_width}w x {m_height}h")

            raster_bytes = sam.decode_mask_to_raster(mask)
            byte_len = len(raster_bytes)
            print(f"Raster size  : {byte_len} bytes")

            expected_len = m_width * m_height
            fg_pixels = count_foreground_pixels(raster_bytes, expected_len)
            print(f"Foreground   : {fg_pixels} pixels")
            
            confidence = getattr(record, "confidence", None)
            if confidence is not None:
                print(f"Confidence   : {confidence}")

            decoded_success += 1
        except Exception as e:
            print(f"Decoding Err : {e}")
            decoded_failed += 1

    print(f"\n--- Final Summary ---")
    print(f"Successfully decoded masks: {decoded_success}")
    print(f"Failed decodings          : {decoded_failed}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Test SAM 3.1 Segmentation Integration")
    parser.add_argument("image_path", help="Path to the local rover image")
    parser.add_argument("prompt", help="Noun phrase to segment")
    args = parser.parse_args()
    
    run_experiment(args.image_path, args.prompt)