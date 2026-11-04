import threading


class BudgetExhaustedError(Exception):
    """Raised when an operation exceeds its allotted external request budget."""
    pass


class ConcurrencyLimitError(Exception):
    """Raised when an operation cannot acquire a concurrency semaphore."""
    pass


class RequestBudget:
    """
    Explicit, thread-safe request budget for an entire end-to-end operation
    (e.g., an entire image analysis pipeline, an observation briefing generation,
    or a single operator chat turn).
    
    Guarantees:
    - Primary and fallback provider attempts share the same budget instance.
    - Every actual live external API attempt consumes 1 unit.
    - Failed attempts still consume 1 unit (because an external HTTP request was made).
    - Dry runs, blocked requests, and deterministic offline calls do NOT consume budget.
    - Once consumed == limit, subsequent requests are rejected.
    - Concurrency-safe: cannot be corrupted or reset mid-operation.
    """
    def __init__(self, limit: int, operation_name: str = "operation"):
        if isinstance(limit, bool):
            raise TypeError("Budget limit cannot be a boolean.")
        if type(limit) is not int:
            raise TypeError(f"Budget limit must be an integer, got {type(limit).__name__}.")
        if limit < 0:
            raise ValueError(f"Budget limit cannot be negative, got {limit}.")

        self._limit: int = limit
        self._operation_name: str = operation_name
        self._consumed: int = 0
        self._lock = threading.Lock()

    @property
    def limit(self) -> int:
        return self._limit

    @property
    def operation_name(self) -> str:
        return self._operation_name

    @property
    def consumed(self) -> int:
        with self._lock:
            return self._consumed

    @property
    def remaining(self) -> int:
        with self._lock:
            return max(0, self._limit - self._consumed)

    def can_request(self) -> bool:
        """Checks whether the budget has available capacity without consuming it."""
        with self._lock:
            return self._consumed < self._limit

    def record_request(self) -> bool:
        """
        Attempts to consume 1 unit of request budget.
        Returns True if permitted (under limit).
        Returns False if the budget is exhausted (rejects request).
        """
        with self._lock:
            if self._consumed < self._limit:
                self._consumed += 1
                return True
            return False

    def __repr__(self) -> str:
        with self._lock:
            return f"<RequestBudget {self._operation_name}: {self._consumed}/{self._limit}>"
