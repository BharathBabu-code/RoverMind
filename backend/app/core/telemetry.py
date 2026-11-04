import copy
import json
import logging
import os
import shutil
import threading
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any, List

from backend.app.core.config import settings, ROOT_DIR
from backend.app.core.sanitizer import sanitize_error

logger = logging.getLogger("rovermind.telemetry")

# Ledger location at project root (gitignored)
LEDGER_FILE_PATH = ROOT_DIR / "api_usage_ledger.json"

# Process-level thread lock for single-process ASGI service.
# NOTE: RoverMind is designed to run as a single-process FastAPI/Uvicorn service.
# Threading locks provide full safety across concurrent async requests and worker threads.
# If horizontally scaled across multiple OS processes, external Redis or portalocker would be needed.
_LEDGER_LOCK = threading.Lock()


class ApiTelemetryTracker:
    """
    Comprehensive, thread-safe telemetry and usage audit ledger.
    Tracks live API metrics, blocked kill-switch events, dry-run simulations,
    active in-flight requests, and model provider provenance across restarts.
    """
    def __init__(self):
        self._lock = threading.Lock()

        # In-memory session counters and state
        self._sam_success_count: int = 0
        self._sam_failure_count: int = 0
        self._sam_blocked_count: int = 0
        self._sam_dry_run_count: int = 0
        self._sam_concurrency_rejected_count: int = 0
        self._sam_budget_exhausted_count: int = 0
        self._sam_last_verified: Optional[str] = None
        self._sam_last_error: Optional[str] = None
        self._sam_active_requests: int = 0
        self._sam_last_outcome: Optional[str] = None  # "success" | "failure" | None

        self._reasoning_success_count: int = 0
        self._reasoning_failure_count: int = 0
        self._reasoning_blocked_count: int = 0
        self._reasoning_dry_run_count: int = 0
        self._reasoning_concurrency_rejected_count: int = 0
        self._reasoning_budget_exhausted_count: int = 0
        self._reasoning_last_verified: Optional[str] = None
        self._reasoning_last_error: Optional[str] = None
        self._reasoning_active_requests: int = 0
        self._reasoning_last_outcome: Optional[str] = None  # "success" | "failure" | None

        self._active_reasoning_model_used: Optional[str] = None

        # Concurrency Semaphores (guarded caps)
        self.sam_semaphore = threading.Semaphore(settings.max_concurrent_sam_requests)
        self.reasoning_semaphore = threading.Semaphore(settings.max_concurrent_reasoning_requests)

        # Initialize or load persistent ledger with validation and recovery
        self._load_ledger()

    # -------------------------------------------------------------------------
    # Persistent Ledger IO & Structural Validation
    # -------------------------------------------------------------------------

    def _default_ledger_data(self) -> Dict[str, Any]:
        now_iso = datetime.now(timezone.utc).isoformat()
        return {
            "version": "1.0",
            "created_at": now_iso,
            "last_updated": now_iso,
            "sam_stats": {
                "attempted": 0,
                "succeeded": 0,
                "failed": 0,
                "blocked_kill_switch": 0,
                "dry_run_simulated": 0,
                "concurrency_rejected": 0,
                "budget_exhausted": 0
            },
            "reasoning_stats": {
                "attempted": 0,
                "succeeded": 0,
                "failed": 0,
                "blocked_kill_switch": 0,
                "dry_run_simulated": 0,
                "concurrency_rejected": 0,
                "budget_exhausted": 0,
                "by_model": {
                    "muse-spark-1.3": {"attempted": 0, "succeeded": 0, "failed": 0},
                    "llama-3.3-70b-instruct": {"attempted": 0, "succeeded": 0, "failed": 0}
                }
            },
            "recent_events": []
        }

    def _validate_ledger_schema(self, data: Any) -> bool:
        """Validates that loaded ledger dictionary contains expected structural keys and non-negative integer counters."""
        if not isinstance(data, dict):
            return False
        required_keys = ("version", "sam_stats", "reasoning_stats", "recent_events")
        if not all(k in data for k in required_keys):
            return False

        sam_stats = data.get("sam_stats")
        reasoning_stats = data.get("reasoning_stats")
        recent_events = data.get("recent_events")

        if not isinstance(sam_stats, dict) or not isinstance(reasoning_stats, dict) or not isinstance(recent_events, list):
            return False

        # Validate sam_stats counter types and non-negativity
        base_keys = ("attempted", "succeeded", "failed", "blocked_kill_switch", "dry_run_simulated")
        for k in base_keys:
            if k not in sam_stats or not isinstance(sam_stats[k], int) or isinstance(sam_stats[k], bool) or sam_stats[k] < 0:
                return False

        # Validate reasoning_stats counter types and non-negativity
        for k in base_keys:
            if k not in reasoning_stats or not isinstance(reasoning_stats[k], int) or isinstance(reasoning_stats[k], bool) or reasoning_stats[k] < 0:
                return False

        # Validate by_model structure if present
        by_model = reasoning_stats.get("by_model")
        if by_model is not None:
            if not isinstance(by_model, dict):
                return False
            for model_name, stat in by_model.items():
                if not isinstance(stat, dict):
                    return False
                for m_k in ("attempted", "succeeded", "failed"):
                    if m_k not in stat or not isinstance(stat[m_k], int) or isinstance(stat[m_k], bool) or stat[m_k] < 0:
                        return False

        # Validate recent_events list elements
        for ev in recent_events:
            if not isinstance(ev, dict):
                return False
            if not all(k in ev for k in ("timestamp", "service", "event_type", "detail")):
                return False

        return True

    def _load_ledger(self) -> None:
        with _LEDGER_LOCK:
            if LEDGER_FILE_PATH.exists():
                try:
                    with open(LEDGER_FILE_PATH, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if self._validate_ledger_schema(data):
                        self._ledger_data = data
                        return
                    else:
                        raise ValueError("Incompatible or structurally invalid ledger schema")
                except Exception as e:
                    # Do not silently destroy a corrupt or invalid ledger.
                    # Preserve/rename the corrupt file with a timestamp and unique suffix to prevent collisions.
                    timestamp_suffix = int(time.time())
                    unique_id = uuid.uuid4().hex[:8]
                    stem = LEDGER_FILE_PATH.stem
                    corrupt_path = LEDGER_FILE_PATH.with_name(f"{stem}.corrupt.{timestamp_suffix}_{unique_id}.json")
                    try:
                        shutil.copy2(LEDGER_FILE_PATH, corrupt_path)
                        sanitized_e = sanitize_error(e)
                        logger.warning(
                            f"Corrupt or invalid ledger file detected ({sanitized_e}). "
                            f"Preserved original to {corrupt_path.name}."
                        )
                    except Exception as copy_err:
                        sanitized_copy = sanitize_error(copy_err)
                        logger.error(f"Failed to backup corrupt ledger: {sanitized_copy}")

            self._ledger_data = self._default_ledger_data()
            self._persist_ledger_unlocked()

    def _persist_ledger_unlocked(self) -> None:
        """
        Atomically persists ledger to disk using a unique temporary file.
        Prevents file write corruption and collision. Emits safe logs on failure without crashing.
        Cleans up failed temporary files if write or replace fails.
        """
        unique_tmp = LEDGER_FILE_PATH.with_name(f"api_usage_ledger.{uuid.uuid4().hex}.tmp")
        try:
            self._ledger_data["last_updated"] = datetime.now(timezone.utc).isoformat()
            with open(unique_tmp, "w", encoding="utf-8") as f:
                json.dump(self._ledger_data, f, indent=2)
            unique_tmp.replace(LEDGER_FILE_PATH)
        except Exception as e:
            sanitized_e = sanitize_error(e)
            logger.warning(f"Failed to persist API usage ledger: {sanitized_e}")
            if unique_tmp.exists():
                try:
                    unique_tmp.unlink()
                except Exception:
                    pass

    def _record_ledger_event(self, service: str, event_type: str, detail: str, model: Optional[str] = None) -> None:
        sanitized_detail = sanitize_error(detail)
        with _LEDGER_LOCK:
            now_iso = datetime.now(timezone.utc).isoformat()
            events: List[Dict[str, Any]] = self._ledger_data.setdefault("recent_events", [])
            events.append({
                "timestamp": now_iso,
                "service": service,
                "event_type": event_type,
                "model": model,
                "detail": sanitized_detail[:200]
            })
            if len(events) > 50:
                self._ledger_data["recent_events"] = events[-50:]

            if service == "sam":
                stats = self._ledger_data["sam_stats"]
                if event_type == "attempt":
                    stats["attempted"] += 1
                elif event_type == "success":
                    stats["succeeded"] += 1
                elif event_type == "failure":
                    stats["failed"] += 1
                elif event_type == "blocked":
                    stats["blocked_kill_switch"] += 1
                elif event_type == "dry_run":
                    stats["dry_run_simulated"] += 1
                elif event_type == "concurrency_rejected":
                    stats["concurrency_rejected"] = stats.get("concurrency_rejected", 0) + 1
                elif event_type == "budget_exhausted":
                    stats["budget_exhausted"] = stats.get("budget_exhausted", 0) + 1
            elif service == "reasoning":
                stats = self._ledger_data["reasoning_stats"]
                if event_type == "attempt":
                    stats["attempted"] += 1
                elif event_type == "success":
                    stats["succeeded"] += 1
                elif event_type == "failure":
                    stats["failed"] += 1
                elif event_type == "blocked":
                    stats["blocked_kill_switch"] += 1
                elif event_type == "dry_run":
                    stats["dry_run_simulated"] += 1
                elif event_type == "concurrency_rejected":
                    stats["concurrency_rejected"] = stats.get("concurrency_rejected", 0) + 1
                elif event_type == "budget_exhausted":
                    stats["budget_exhausted"] = stats.get("budget_exhausted", 0) + 1

                if model:
                    by_model = stats.setdefault("by_model", {})
                    model_stat = by_model.setdefault(model, {"attempted": 0, "succeeded": 0, "failed": 0})
                    if event_type == "attempt":
                        model_stat["attempted"] += 1
                    elif event_type == "success":
                        model_stat["succeeded"] += 1
                    elif event_type == "failure":
                        model_stat["failed"] += 1

            self._persist_ledger_unlocked()

    # -------------------------------------------------------------------------
    # Thread-Safe Telemetry Mutators
    # -------------------------------------------------------------------------

    def record_sam_blocked(self, reason: str = "Kill switch active (EXTERNAL_API_ENABLED=false)") -> None:
        sanitized = sanitize_error(reason)
        with self._lock:
            self._sam_blocked_count += 1
        self._record_ledger_event("sam", "blocked", sanitized)

    def record_sam_dry_run(self) -> None:
        with self._lock:
            self._sam_dry_run_count += 1
        self._record_ledger_event("sam", "dry_run", "Simulated SAM dry-run execution")

    def record_sam_start(self) -> None:
        with self._lock:
            self._sam_active_requests += 1
        self._record_ledger_event("sam", "attempt", "Live SAM API request started")

    def record_sam_success(self) -> None:
        with self._lock:
            self._sam_active_requests = max(0, self._sam_active_requests - 1)
            self._sam_success_count += 1
            self._sam_last_verified = datetime.now(timezone.utc).isoformat()
            self._sam_last_error = None
            self._sam_last_outcome = "success"
        self._record_ledger_event("sam", "success", "Live SAM API request succeeded")

    def record_sam_failure(self, error: Any, was_started: bool = True) -> None:
        sanitized = sanitize_error(error)
        with self._lock:
            if was_started and self._sam_active_requests > 0:
                self._sam_active_requests = max(0, self._sam_active_requests - 1)
            self._sam_failure_count += 1
            self._sam_last_error = sanitized
            self._sam_last_outcome = "failure"
        self._record_ledger_event("sam", "failure", sanitized)

    def record_sam_concurrency_rejected(self, reason: str = "Concurrency semaphore cap reached") -> None:
        """
        Records a concurrency rejection for SAM without touching the active requests counter.
        A request that never acquired the semaphore was never started.
        """
        sanitized = sanitize_error(reason)
        with self._lock:
            self._sam_concurrency_rejected_count += 1
            self._sam_last_error = sanitized
            self._sam_last_outcome = "failure"
        self._record_ledger_event("sam", "concurrency_rejected", sanitized)

    def record_sam_budget_exhausted(self, detail: str = "Request budget exhausted") -> None:
        """Records SAM budget exhaustion as a distinguishable telemetry event."""
        sanitized = sanitize_error(detail)
        with self._lock:
            self._sam_budget_exhausted_count += 1
            self._sam_last_error = sanitized
        self._record_ledger_event("sam", "budget_exhausted", sanitized)

    def record_reasoning_blocked(self, reason: str = "Kill switch active (EXTERNAL_API_ENABLED=false)") -> None:
        sanitized = sanitize_error(reason)
        with self._lock:
            self._reasoning_blocked_count += 1
        self._record_ledger_event("reasoning", "blocked", sanitized)

    def record_reasoning_dry_run(self, model: str) -> None:
        with self._lock:
            self._reasoning_dry_run_count += 1
            self._active_reasoning_model_used = model
        self._record_ledger_event("reasoning", "dry_run", f"Simulated dry-run for {model}", model=model)

    def record_reasoning_start(self, model: str) -> None:
        with self._lock:
            self._reasoning_active_requests += 1
        self._record_ledger_event("reasoning", "attempt", f"Live request started for {model}", model=model)

    def record_reasoning_success(self, model: str) -> None:
        with self._lock:
            self._reasoning_active_requests = max(0, self._reasoning_active_requests - 1)
            self._reasoning_success_count += 1
            self._reasoning_last_verified = datetime.now(timezone.utc).isoformat()
            self._reasoning_last_error = None
            self._reasoning_last_outcome = "success"
            self._active_reasoning_model_used = model
        self._record_ledger_event("reasoning", "success", f"Live request succeeded for {model}", model=model)

    def record_reasoning_failure(self, model: str, error: Any, was_started: bool = True) -> None:
        sanitized = sanitize_error(error)
        with self._lock:
            if was_started and self._reasoning_active_requests > 0:
                self._reasoning_active_requests = max(0, self._reasoning_active_requests - 1)
            self._reasoning_failure_count += 1
            self._reasoning_last_error = sanitized
            self._reasoning_last_outcome = "failure"
        self._record_ledger_event("reasoning", "failure", sanitized, model=model)

    def record_reasoning_concurrency_rejected(self, model: Optional[str] = None, reason: str = "Concurrency semaphore cap reached") -> None:
        """
        Records a concurrency rejection for Reasoning without touching the active requests counter.
        A request that never acquired the semaphore was never started.
        """
        sanitized = sanitize_error(reason)
        with self._lock:
            self._reasoning_concurrency_rejected_count += 1
            self._reasoning_last_error = sanitized
            self._reasoning_last_outcome = "failure"
        self._record_ledger_event("reasoning", "concurrency_rejected", sanitized, model=model)

    def record_reasoning_budget_exhausted(self, detail: str = "Request budget exhausted", model: Optional[str] = None) -> None:
        """Records reasoning budget exhaustion as a distinguishable telemetry event."""
        sanitized = sanitize_error(detail)
        with self._lock:
            self._reasoning_budget_exhausted_count += 1
            self._reasoning_last_error = sanitized
        self._record_ledger_event("reasoning", "budget_exhausted", sanitized, model=model)

    def record_call(
        self,
        provider: str,
        model: str,
        tokens_in: int = 0,
        tokens_out: int = 0,
        latency_ms: float = 0.0,
        cost_usd: float = 0.0,
        success: bool = True,
        error: Optional[Any] = None,
    ) -> None:
        """
        Generic provider call recorder with automatic error sanitization.
        Ensures raw exception messages and sensitive parameters are sanitized before entry.
        """
        sanitized_error = sanitize_error(error) if error is not None else None
        if success:
            if "sam" in provider.lower():
                self.record_sam_success()
            else:
                self.record_reasoning_success(model)
        else:
            if "sam" in provider.lower():
                self.record_sam_failure(sanitized_error or "Unknown failure")
            else:
                self.record_reasoning_failure(model, sanitized_error or "Unknown failure")

    # -------------------------------------------------------------------------
    # Thread-Safe Status & Provenance Resolvers
    # -------------------------------------------------------------------------

    def get_sam_status(self) -> str:
        """
        Resolves accurate, live SAM operational status.
        Never falsely reports 'last_request_successful' if the latest attempt failed.
        """
        with self._lock:
            if not settings.is_meta_api_configured:
                return "not_configured"
            if not settings.external_api_enabled:
                return "blocked_by_kill_switch"
            if settings.external_api_dry_run:
                return "dry_run_active"
            if self._sam_active_requests > 0:
                return "request_in_progress"
            if self._sam_last_outcome == "failure":
                if self._sam_last_error and ("rate limit" in self._sam_last_error.lower() or "429" in self._sam_last_error):
                    return "rate_limited"
                return "request_failed"
            if self._sam_last_outcome == "success":
                return "last_request_successful"
            return "configured_untested"

    def get_reasoning_status(self) -> str:
        """
        Resolves accurate, live reasoning operational status.
        Never falsely reports 'last_request_successful' if the latest attempt failed.
        """
        with self._lock:
            if not settings.is_reasoning_api_configured:
                return "not_configured"
            if not settings.external_api_enabled:
                return "blocked_by_kill_switch"
            if settings.external_api_dry_run:
                return "dry_run_active"
            if self._reasoning_active_requests > 0:
                return "request_in_progress"
            if self._reasoning_last_outcome == "failure":
                if self._reasoning_last_error and ("rate limit" in self._reasoning_last_error.lower() or "429" in self._reasoning_last_error):
                    return "rate_limited"
                return "request_failed"
            if self._reasoning_last_outcome == "success":
                return "last_request_successful"
            return "configured_untested"

    def get_reasoning_provenance(self) -> str:
        """
        Returns exact standardized model provenance tag based on actual completed request:
        LIVE — MUSE SPARK | LIVE — LLAMA 3.3 | DETERMINISTIC — OFFLINE FALLBACK |
        EXTERNAL INFERENCE DISABLED | DRY RUN
        """
        with self._lock:
            if not settings.external_api_enabled:
                return "EXTERNAL INFERENCE DISABLED"
            if settings.external_api_dry_run:
                return "DRY RUN"
            if not settings.is_reasoning_api_configured or settings.reasoning_provider == "offline":
                return "DETERMINISTIC — OFFLINE FALLBACK"
            if self._reasoning_last_outcome == "success" and self._active_reasoning_model_used:
                if settings.reasoning_provider == "muse-spark" or "muse" in self._active_reasoning_model_used.lower():
                    return "LIVE — MUSE SPARK"
                elif settings.reasoning_provider == "llama-3.3" or "llama" in self._active_reasoning_model_used.lower():
                    return "LIVE — LLAMA 3.3"
            return "DETERMINISTIC — OFFLINE FALLBACK"

    def reset(self, reset_ledger: bool = False) -> None:
        """Resets in-memory counters (useful for isolated unit testing)."""
        with self._lock:
            self._sam_success_count = 0
            self._sam_failure_count = 0
            self._sam_blocked_count = 0
            self._sam_dry_run_count = 0
            self._sam_concurrency_rejected_count = 0
            self._sam_budget_exhausted_count = 0
            self._sam_last_verified = None
            self._sam_last_error = None
            self._sam_active_requests = 0
            self._sam_last_outcome = None

            self._reasoning_success_count = 0
            self._reasoning_failure_count = 0
            self._reasoning_blocked_count = 0
            self._reasoning_dry_run_count = 0
            self._reasoning_concurrency_rejected_count = 0
            self._reasoning_budget_exhausted_count = 0
            self._reasoning_last_verified = None
            self._reasoning_last_error = None
            self._reasoning_active_requests = 0
            self._reasoning_last_outcome = None
            self._active_reasoning_model_used = None

        if reset_ledger:
            with _LEDGER_LOCK:
                self._ledger_data = self._default_ledger_data()
                self._persist_ledger_unlocked()

    def get_telemetry_summary(self) -> Dict[str, Any]:
        """
        Returns an atomic, consistent snapshot of in-memory telemetry and ledger statistics.
        Acquires both locks in consistent order (_LEDGER_LOCK then self._lock) and deep-copies
        nested data structures.
        """
        with _LEDGER_LOCK:
            with self._lock:
                ledger_stats = copy.deepcopy({
                    "sam_stats": self._ledger_data.get("sam_stats", {}),
                    "reasoning_stats": self._ledger_data.get("reasoning_stats", {}),
                    "recent_events_count": len(self._ledger_data.get("recent_events", []))
                })

                sam_active = self._sam_active_requests
                sam_success = self._sam_success_count
                sam_verified = self._sam_last_verified
                sam_err = self._sam_last_error
                sam_outcome = self._sam_last_outcome

                reason_active = self._reasoning_active_requests
                reason_success = self._reasoning_success_count
                reason_verified = self._reasoning_last_verified
                reason_err = self._reasoning_last_error
                reason_outcome = self._reasoning_last_outcome
                active_model = self._active_reasoning_model_used

        # Derive current SAM status
        if not settings.is_meta_api_configured:
            sam_status = "not_configured"
            active_seg = "offline-synthetic-fixture"
        elif not settings.external_api_enabled:
            sam_status = "blocked_by_kill_switch"
            active_seg = "offline-synthetic-fixture"
        elif settings.external_api_dry_run:
            sam_status = "dry_run_active"
            active_seg = "dry-run-sam-3.1"
        elif sam_active > 0:
            sam_status = "request_in_progress"
            active_seg = "live-meta-sam-3.1" if sam_success > 0 else "offline-synthetic-fixture"
        elif sam_outcome == "failure":
            sam_status = "rate_limited" if (sam_err and ("rate limit" in sam_err.lower() or "429" in sam_err)) else "request_failed"
            active_seg = "offline-synthetic-fixture"
        elif sam_outcome == "success":
            sam_status = "last_request_successful"
            active_seg = "live-meta-sam-3.1"
        else:
            sam_status = "configured_untested"
            active_seg = "offline-synthetic-fixture"

        # Derive current Reasoning status & provenance
        if not settings.external_api_enabled:
            prov = "EXTERNAL INFERENCE DISABLED"
            reason_status = "blocked_by_kill_switch" if settings.is_reasoning_api_configured else "not_configured"
            active_reason = "deterministic-rule-engine"
        elif settings.external_api_dry_run:
            prov = "DRY RUN"
            reason_status = "dry_run_active" if settings.is_reasoning_api_configured else "not_configured"
            active_reason = "dry-run"
        elif not settings.is_reasoning_api_configured or settings.reasoning_provider == "offline":
            prov = "DETERMINISTIC — OFFLINE FALLBACK"
            reason_status = "not_configured"
            active_reason = "deterministic-rule-engine"
        elif reason_active > 0:
            prov = "DETERMINISTIC — OFFLINE FALLBACK"
            reason_status = "request_in_progress"
            active_reason = "live-meta-reasoning"
        elif reason_outcome == "failure":
            prov = "DETERMINISTIC — OFFLINE FALLBACK"
            reason_status = "rate_limited" if (reason_err and ("rate limit" in reason_err.lower() or "429" in reason_err)) else "request_failed"
            active_reason = "deterministic-rule-engine"
        elif reason_outcome == "success" and active_model:
            if settings.reasoning_provider == "muse-spark" or "muse" in active_model.lower():
                prov = "LIVE — MUSE SPARK"
            elif settings.reasoning_provider == "llama-3.3" or "llama" in active_model.lower():
                prov = "LIVE — LLAMA 3.3"
            else:
                prov = "DETERMINISTIC — OFFLINE FALLBACK"
            reason_status = "last_request_successful"
            active_reason = prov
        else:
            prov = "DETERMINISTIC — OFFLINE FALLBACK"
            reason_status = "configured_untested"
            active_reason = "deterministic-rule-engine"

        return {
            "external_api_enabled": settings.external_api_enabled,
            "external_api_dry_run": settings.external_api_dry_run,
            "reasoning_provider": settings.reasoning_provider,
            "muse_spark_model": settings.muse_spark_model,
            "llama_model": settings.llama_model,
            "provider_provenance": prov,
            "sam_status": sam_status,
            "sam_last_verified": sam_verified,
            "sam_last_error": sam_err,
            "sam_last_outcome": sam_outcome,
            "sam_success_count": sam_success,
            "sam_active_requests": sam_active,
            "reasoning_status": reason_status,
            "reasoning_last_verified": reason_verified,
            "reasoning_last_error": reason_err,
            "reasoning_last_outcome": reason_outcome,
            "reasoning_success_count": reason_success,
            "reasoning_active_requests": reason_active,
            "active_segmentation_source": active_seg,
            "active_reasoning_source": active_reason,
            "ledger": ledger_stats
        }


api_telemetry = ApiTelemetryTracker()
