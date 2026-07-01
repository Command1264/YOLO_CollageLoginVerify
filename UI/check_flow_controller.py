from __future__ import annotations


class CheckFlowController:
    """Manage in-memory check execution state for GUI flow."""

    def __init__(self) -> None:
        self._check_running = False
        self._pending_check_queue: list[dict[str, str]] = []
        self._current_check_context: dict[str, str] | None = None

    def is_running(self) -> bool:
        """Return whether a check task is running."""
        return self._check_running

    def pending_count(self) -> int:
        """Return pending queue count."""
        return len(self._pending_check_queue)

    def pending_entries(self) -> list[dict[str, str]]:
        """Return current pending queue list."""
        return self._pending_check_queue

    def enqueue(self, entry: dict[str, str]) -> None:
        """Append one pending check entry."""
        self._pending_check_queue.append(entry)

    def begin_manual_context(self, semester: str) -> None:
        """Set current check context for manual trigger."""
        self._current_check_context = {"type": "manual", "semester": semester}

    def current_context(self) -> dict[str, str] | None:
        """Get current check context."""
        return self._current_check_context

    def can_start_now(self, service_boot_ready: bool) -> bool:
        """Return whether check can start immediately."""
        return bool(service_boot_ready) and (not self._check_running)

    def mark_started(self) -> None:
        """Mark check execution as running."""
        self._check_running = True

    def mark_finished(self) -> None:
        """Mark check execution as finished."""
        self._check_running = False

    def clear_current_context(self) -> dict[str, str] | None:
        """Clear and return current context."""
        context = self._current_check_context
        self._current_check_context = None
        return context

    def dequeue_next_for_start(self, service_boot_ready: bool) -> dict[str, str] | None:
        """Pop one pending entry as current context when start conditions are met."""
        if (not service_boot_ready) or self._check_running:
            return None
        if len(self._pending_check_queue) == 0:
            return None
        entry = self._pending_check_queue.pop(0)
        self._current_check_context = entry
        return entry
