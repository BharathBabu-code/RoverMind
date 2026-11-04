import math
import os
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv

# Determine the repository root dynamically based on this file's location.
# __file__ is backend/app/core/config.py
# parents[0] = core, parents[1] = app, parents[2] = backend, parents[3] = project root
ROOT_DIR = Path(__file__).resolve().parents[3]
ENV_PATH = ROOT_DIR / ".env"

# Load environment variables from the root .env file.
# override=False ensures we do not overwrite variables already set in the OS environment.
load_dotenv(dotenv_path=ENV_PATH, override=False)


def _parse_bool(val: str | None, default: bool) -> bool:
    """Safely parse boolean environment variable. Rejects malformed values."""
    if val is None or val == "":
        return default
    val_clean = str(val).strip().lower()
    if val_clean in ("true", "1", "yes", "t", "on"):
        return True
    if val_clean in ("false", "0", "no", "f", "off"):
        return False
    raise ValueError(f"Invalid boolean environment configuration: '{val}'. Expected 'true' or 'false'.")


def _parse_int(val: str | None, default: int, min_val: int = 0, max_val: int = 100000) -> int:
    """Safely parse integer environment variable within bounds. Rejects non-integers, floats, and booleans."""
    if val is None or val == "":
        return default
    if isinstance(val, bool):
        raise TypeError("Expected integer value, got boolean.")
    val_str = str(val).strip()
    if "." in val_str:
        raise ValueError(f"Invalid integer configuration: '{val}'. Floats are not permitted for integer settings.")
    try:
        parsed = int(val_str)
        if parsed < min_val or parsed > max_val:
            raise ValueError(f"Configuration value {parsed} out of allowable bounds [{min_val}, {max_val}].")
        return parsed
    except ValueError as e:
        if "out of allowable bounds" in str(e):
            raise
        raise ValueError(f"Invalid integer configuration: '{val}'.") from e


def _parse_float(val: str | None, default: float, min_val: float = 0.0, max_val: float = 120.0) -> float:
    """Safely parse float environment variable within bounds. Rejects non-finite values (NaN, Inf)."""
    if val is None or val == "":
        return default
    try:
        parsed = float(str(val).strip())
        if not math.isfinite(parsed):
            raise ValueError(f"Invalid non-finite float value: '{val}'. NaN and Infinity are prohibited.")
        if parsed < min_val or parsed > max_val:
            raise ValueError(f"Float configuration value {parsed} out of allowable bounds [{min_val}, {max_val}].")
        return parsed
    except (ValueError, TypeError) as e:
        raise ValueError(f"Invalid float configuration: '{val}'.") from e


def _validate_url(url: str | None, default: str, setting_name: str) -> str:
    """
    Validates external service base URLs:
    1. Rejects embedded user-info / credentials (e.g. https://user:pass@host).
    2. Enforces HTTPS for remote production endpoints, permitting HTTP strictly
       for local development/testing (localhost, 127.0.0.1, testserver).
    """
    candidate = (url or default).strip()
    parsed = urllib.parse.urlparse(candidate)
    if not parsed.scheme or not parsed.netloc:
        raise ValueError(f"Invalid URL for {setting_name}: '{candidate}'. Missing scheme or host.")

    # Check for embedded credentials
    if parsed.username or parsed.password or "@" in parsed.netloc:
        raise ValueError(f"Security error: Embedded credentials prohibited in {setting_name}: '{candidate}'.")

    # Scheme validation
    is_local = parsed.hostname in ("localhost", "127.0.0.1", "testserver")
    if parsed.scheme.lower() not in ("https", "http"):
        raise ValueError(f"Unsupported scheme '{parsed.scheme}' for {setting_name}. Must be https:// or http://.")
    if parsed.scheme.lower() == "http" and not is_local:
        raise ValueError(f"Insecure HTTP prohibited for remote endpoint in {setting_name}: '{candidate}'. HTTPS is required.")

    return candidate


class Settings:
    """
    Centralized configuration management for RoverMind.
    Provides strict pre-live safety controls, rate/cost budget caps,
    and configurable reasoning provider routing.
    NOTE: Settings are loaded at process startup; changes to .env require a backend restart.
    """
    def __init__(self) -> None:
        # API Keys (read from environment or .env, defaulting to None)
        self._meta_api_key: str | None = os.environ.get("META_API_KEY")
        self._meta_reasoning_api_key: str | None = (
            os.environ.get("META_REASONING_API_KEY") or self._meta_api_key
        )

        # Global Kill Switch & Dry-Run Mode (Safe defaults: external disabled, dry-run enabled)
        self._external_api_enabled: bool = _parse_bool(os.environ.get("EXTERNAL_API_ENABLED"), default=False)
        self._external_api_dry_run: bool = _parse_bool(os.environ.get("EXTERNAL_API_DRY_RUN"), default=True)

        # Reasoning Model Provider Architecture
        # Allowed providers: "muse-spark", "llama-3.3", "offline"
        self._reasoning_provider: str = os.environ.get("REASONING_PROVIDER", "muse-spark").strip().lower()
        if self._reasoning_provider not in ("muse-spark", "llama-3.3", "offline"):
            self._reasoning_provider = "muse-spark"

        # Model Identifiers
        # Meta Muse Spark models: "muse-spark-1.3", "muse-spark-1.3-contributor", "muse-spark-open"
        muse_raw = os.environ.get("MUSE_SPARK_MODEL", "muse-spark-1.3").strip()
        self._muse_spark_model: str = muse_raw or "muse-spark-1.3"

        llama_raw = os.environ.get("LLAMA_MODEL", "llama-3.3-70b-instruct").strip()
        self._llama_model: str = llama_raw or "llama-3.3-70b-instruct"

        # Fallback provider if primary provider fails (e.g. 403 allowlist restriction or 404)
        self._fallback_reasoning_provider: str = os.environ.get("FALLBACK_REASONING_PROVIDER", "llama-3.3").strip().lower()
        if self._fallback_reasoning_provider not in ("muse-spark", "llama-3.3", "offline"):
            self._fallback_reasoning_provider = "llama-3.3"

        # Base URLs (Configurable separately for SAM and Reasoning)
        self._meta_api_base_url: str = _validate_url(os.environ.get("META_API_BASE_URL"), "https://api.meta.ai/v1", "META_API_BASE_URL")
        self._meta_reasoning_base_url: str = _validate_url(os.environ.get("META_REASONING_BASE_URL"), "https://api.meta.ai/v1", "META_REASONING_BASE_URL")

        # Hard Request & Cost Budgets
        self._max_sam_requests_per_analysis: int = _parse_int(os.environ.get("MAX_SAM_REQUESTS_PER_ANALYSIS"), default=1, min_val=0, max_val=5)
        self._max_reasoning_requests_per_briefing: int = _parse_int(os.environ.get("MAX_REASONING_REQUESTS_PER_BRIEFING"), default=2, min_val=0, max_val=5)
        self._max_reasoning_requests_per_chat: int = _parse_int(os.environ.get("MAX_REASONING_REQUESTS_PER_CHAT"), default=3, min_val=0, max_val=10)
        self._max_tool_iterations_per_chat: int = _parse_int(os.environ.get("MAX_TOOL_ITERATIONS_PER_CHAT"), default=2, min_val=0, max_val=5)

        # Tool Execution Limits
        self._max_tool_executions_per_chat: int = _parse_int(os.environ.get("MAX_TOOL_EXECUTIONS_PER_CHAT"), default=4, min_val=1, max_val=10)
        self._max_total_tool_output_bytes: int = _parse_int(os.environ.get("MAX_TOTAL_TOOL_OUTPUT_BYTES"), default=32768, min_val=1024, max_val=262144)

        # Concurrency Caps
        self._max_concurrent_sam_requests: int = _parse_int(os.environ.get("MAX_CONCURRENT_SAM_REQUESTS"), default=1, min_val=1, max_val=4)
        self._max_concurrent_reasoning_requests: int = _parse_int(os.environ.get("MAX_CONCURRENT_REASONING_REQUESTS"), default=1, min_val=1, max_val=4)

        # Payload & Context Guardrails
        self._max_input_text_length: int = _parse_int(os.environ.get("MAX_INPUT_TEXT_LENGTH"), default=1000, min_val=100, max_val=5000)
        self._max_conversation_history_messages: int = _parse_int(os.environ.get("MAX_CONVERSATION_HISTORY_MESSAGES"), default=10, min_val=2, max_val=50)
        self._max_tool_output_bytes: int = _parse_int(os.environ.get("MAX_TOOL_OUTPUT_BYTES"), default=8192, min_val=1024, max_val=65536)

        # Network Timeouts & Retries (Zero automatic retries by default to prevent runaway token costs)
        self._connect_timeout_seconds: float = _parse_float(os.environ.get("CONNECT_TIMEOUT_SECONDS"), default=5.0, min_val=1.0, max_val=30.0)
        self._read_timeout_seconds: float = _parse_float(os.environ.get("READ_TIMEOUT_SECONDS"), default=25.0, min_val=5.0, max_val=120.0)
        self._max_retries: int = _parse_int(os.environ.get("MAX_RETRIES"), default=0, min_val=0, max_val=3)

    # -------------------------------------------------------------------------
    # Computed Properties
    # -------------------------------------------------------------------------

    @property
    def external_api_enabled(self) -> bool:
        """Global kill switch. When False, NO external HTTP calls are dispatched."""
        return self._external_api_enabled

    @property
    def external_api_dry_run(self) -> bool:
        """Dry-run switch. When True, simulated responses validate flow without hitting Meta APIs."""
        return self._external_api_dry_run

    @property
    def is_meta_api_configured(self) -> bool:
        """
        Check if the Meta SAM API key credential is provided and non-empty.
        NOTE: Indicates presence of credential string only; does NOT verify
        provider authorization, model permissions, or live endpoint connectivity.
        """
        if not self._meta_api_key:
            return False
        return bool(self._meta_api_key.strip())

    @property
    def meta_api_key(self) -> str | None:
        """Read-only access to Meta SAM API key."""
        return self._meta_api_key

    @property
    def is_reasoning_api_configured(self) -> bool:
        """
        Check if the Meta Reasoning API key credential is provided and non-empty.
        NOTE: Indicates presence of credential string only; does NOT verify
        provider authorization, model permissions, or live endpoint connectivity.
        """
        if not self._meta_reasoning_api_key:
            return False
        return bool(self._meta_reasoning_api_key.strip())

    @property
    def meta_reasoning_api_key(self) -> str | None:
        """Read-only access to Meta Reasoning API key."""
        return self._meta_reasoning_api_key

    @property
    def reasoning_provider(self) -> str:
        """Configured primary reasoning provider ('muse-spark' | 'llama-3.3' | 'offline')."""
        return self._reasoning_provider

    @property
    def muse_spark_model(self) -> str:
        """Model identifier for Meta Muse Spark."""
        return self._muse_spark_model

    @property
    def llama_model(self) -> str:
        """Model identifier for Meta Llama reasoning."""
        return self._llama_model

    @property
    def fallback_reasoning_provider(self) -> str:
        """Fallback provider if primary provider is unavailable."""
        return self._fallback_reasoning_provider

    @property
    def meta_reasoning_model(self) -> str:
        """Resolves active reasoning model based on configured provider."""
        if self._reasoning_provider == "muse-spark":
            return self._muse_spark_model
        return self._llama_model

    @property
    def meta_api_base_url(self) -> str:
        """Configured Meta SAM 3.1 API base URL."""
        return self._meta_api_base_url

    @property
    def meta_reasoning_base_url(self) -> str:
        """Configured Meta Reasoning API base URL."""
        return self._meta_reasoning_base_url

    @property
    def max_sam_requests_per_analysis(self) -> int:
        return self._max_sam_requests_per_analysis

    @property
    def max_reasoning_requests_per_briefing(self) -> int:
        return self._max_reasoning_requests_per_briefing

    @property
    def max_reasoning_requests_per_chat(self) -> int:
        return self._max_reasoning_requests_per_chat

    @property
    def max_tool_iterations_per_chat(self) -> int:
        return self._max_tool_iterations_per_chat

    @property
    def max_tool_executions_per_chat(self) -> int:
        return self._max_tool_executions_per_chat

    @property
    def max_total_tool_output_bytes(self) -> int:
        return self._max_total_tool_output_bytes

    @property
    def max_concurrent_sam_requests(self) -> int:
        return self._max_concurrent_sam_requests

    @property
    def max_concurrent_reasoning_requests(self) -> int:
        return self._max_concurrent_reasoning_requests

    @property
    def max_input_text_length(self) -> int:
        return self._max_input_text_length

    @property
    def max_conversation_history_messages(self) -> int:
        return self._max_conversation_history_messages

    @property
    def max_tool_output_bytes(self) -> int:
        return self._max_tool_output_bytes

    @property
    def connect_timeout_seconds(self) -> float:
        return self._connect_timeout_seconds

    @property
    def read_timeout_seconds(self) -> float:
        return self._read_timeout_seconds

    @property
    def max_retries(self) -> int:
        return self._max_retries


# Expose a singleton instance for the application
settings = Settings()
