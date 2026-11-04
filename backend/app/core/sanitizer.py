import re
from typing import Any, Optional


def sanitize_error(error: Any, known_secrets: Optional[list[str]] = None) -> str:
    """
    Centralized error sanitization utility for RoverMind.
    Ensures that raw exception messages, HTTP headers, API keys, Bearer tokens,
    base64 image blobs, sensitive URLs, and complete prompts are never stored in
    in-memory telemetry, written to persistent ledgers, or leaked to UI diagnostics.
    
    Preserves critical diagnostic value:
    - HTTP status codes (e.g. 401, 403, 404, 429, 500, 503)
    - Error categories (e.g. RateLimitError, ConnectTimeout, ReadTimeout, ParserError)
    - Sanitized summary descriptions.
    """
    if error is None:
        return "Unknown error"

    text = str(error)

    # 1. Redact explicitly known secret values (e.g., loaded API keys)
    if known_secrets:
        for secret in known_secrets:
            if secret and len(secret.strip()) > 3:
                text = text.replace(secret.strip(), "[REDACTED_API_KEY]")

    # Also check settings for configured keys without creating circular imports
    try:
        from backend.app.core.config import settings
        if settings.meta_api_key and len(settings.meta_api_key.strip()) > 3:
            text = text.replace(settings.meta_api_key.strip(), "[REDACTED_API_KEY]")
        if settings.meta_reasoning_api_key and len(settings.meta_reasoning_api_key.strip()) > 3:
            text = text.replace(settings.meta_reasoning_api_key.strip(), "[REDACTED_API_KEY]")
    except Exception:
        pass

    # 2. Redact Authorization headers, Bearer tokens, Basic Auth, and key patterns
    text = re.sub(r"(?i)(['\"]?authorization['\"]?\s*[:=]\s*['\"]?)(?:Bearer|Basic)\s+[^\s,;'\"}]+([\"']?)", r"\1[REDACTED_AUTH_HEADER]\2", text)
    text = re.sub(r"(?i)(bearer\s+)[a-zA-Z0-9_\-\.]{6,}", r"\1[REDACTED_TOKEN]", text)
    text = re.sub(r"(?i)(basic\s+)[a-zA-Z0-9+/=]{6,}", r"\1[REDACTED_BASIC_AUTH]", text)
    text = re.sub(r"(?i)(https?://)([^:\s/@]+):([^@\s/]+)@", r"\1[REDACTED_USERINFO]@", text)
    text = re.sub(r"(?i)(api[-_]?key[\"']?\s*[:=]\s*[\"']?)[^\"'\s\r\n,;}]+([\"']?)", r"\1[REDACTED_KEY]\2", text)
    text = re.sub(r"(?i)(token[\"']?\s*[:=]\s*[\"']?)[^\"'\s\r\n,;}]+([\"']?)", r"\1[REDACTED_TOKEN]\2", text)
    text = re.sub(r"key-[a-zA-Z0-9_\-]{8,}", "[REDACTED_KEY]", text)
    text = re.sub(r"sk-[a-zA-Z0-9_\-]{8,}", "[REDACTED_KEY]", text)
    text = re.sub(r"AIza[0-9A-Za-z\-_]{30,}", "[REDACTED_KEY]", text)
    text = re.sub(r"(?i)\b(secret|password)[\"']?\s*[:= ]\s*[\"']?[^\"'\s\r\n,;}]+[\"']?", r"\1=[REDACTED_SECRET]", text)
    text = re.sub(r"(?i)(payload[\"']?\s*[:=]\s*[\"']?)\{[^}\r\n]+\}", r"\1[REDACTED_PAYLOAD]", text)

    # 3. Redact data URLs and base64 image rasters
    text = re.sub(r"data:image\/[a-zA-Z]+;base64,[a-zA-Z0-9+/=]{16,}", "data:image/[REDACTED_BASE64_IMAGE]", text)
    # Long base64 or hex strings (>60 chars)
    text = re.sub(r"[a-zA-Z0-9+/=]{60,}", "[REDACTED_PAYLOAD_DATA]", text)

    # 4. Redact query parameters in URLs to prevent credential or token exposure in query strings
    text = re.sub(r"(https?://[^\s\"'>?]+)\?[^\s\"'>]+", r"\1?[REDACTED_QUERY_PARAMS]", text)

    # 5. Collapse multiple whitespaces/newlines for clean single-line telemetry
    text = re.sub(r"\s+", " ", text).strip()

    # 6. Bound string length to 250 characters to prevent prompt echo/stack trace blowouts
    if len(text) > 250:
        text = text[:247] + "..."

    return text


def contains_sensitive_data(text: str, forbidden_strings: Optional[list[str]] = None) -> bool:
    """
    Diagnostic helper to test whether a sanitized string contains raw sensitive secrets.
    """
    if not text:
        return False

    if forbidden_strings:
        for s in forbidden_strings:
            if s and len(s.strip()) > 3 and s.strip() in text:
                return True

    # Regex test for unredacted Bearer tokens, Basic auth, userinfo, or API keys
    if re.search(r"(?i)bearer\s+(?!\[REDACTED)[a-zA-Z0-9_\-\.]{12,}", text):
        return True
    if re.search(r"(?i)basic\s+(?!\[REDACTED)[a-zA-Z0-9+/=]{12,}", text):
        return True
    if re.search(r"(?i)(https?://)(?!\[REDACTED)[^:\s/@]+:[^@\s/]+@", text):
        return True
    if re.search(r"sk-(?!\[REDACTED)[a-zA-Z0-9_\-]{12,}", text):
        return True
    if re.search(r"AIza(?!\[REDACTED)[0-9A-Za-z\-_]{30,}", text):
        return True

    return False
