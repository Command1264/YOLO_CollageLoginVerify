from __future__ import annotations

from dataclasses import asdict
from typing import Any, Callable, Protocol, cast

from PySide6.QtCore import QObject, Signal

from UI.notifier import NotificationConfig, Notifier


class SemesterServiceProtocol(Protocol):
    def get_semesters(self) -> tuple[list[object], str | None]:
        ...


class CheckServiceProtocol(Protocol):
    def check_updates(
        self,
        semester_value: str | None,
        progress_callback: Callable[[int, str], None] | None = None,
        google_sheet_format: dict | None = None,
    ) -> list[object]:
        ...


class SemesterWorker(QObject):
    """Background worker for loading semester options."""

    finished = Signal(list, str)
    failed = Signal(str)

    def __init__(self, service_factory: Callable[[], SemesterServiceProtocol]) -> None:
        """Initialize worker.

        Args:
            service_factory (Callable[[], object]): Factory that returns ScholarshipService instance.
        """
        super().__init__()
        self._service_factory = service_factory

    def run(self) -> None:
        """Execute semester loading task."""
        try:
            service = self._service_factory()
            semesters, selected = service.get_semesters()
            self.finished.emit([asdict(cast(Any, item)) for item in semesters], selected or "")
        except Exception as exc:
            self.failed.emit(str(exc))


class CheckWorker(QObject):
    """Background worker for one scholarship check execution."""

    finished = Signal(list, str)
    failed = Signal(str)
    progress = Signal(int, str)

    def __init__(
        self,
        service_factory: Callable[[], CheckServiceProtocol],
        semester: str,
        google_sheet_format: dict | None = None,
    ) -> None:
        """Initialize worker.

        Args:
            service_factory (Callable[[], object]): Factory that returns ScholarshipService instance.
            semester (str): Target semester value.
            google_sheet_format (dict | None): Google Sheets format config.
        """
        super().__init__()
        self._service_factory = service_factory
        self.semester = semester
        self.google_sheet_format = google_sheet_format or {}

    def run(self) -> None:
        """Execute one check task."""
        try:
            service = self._service_factory()
            results = service.check_updates(
                self.semester or None,
                progress_callback=self._emit_progress,
                google_sheet_format=self.google_sheet_format,
            )
            self.finished.emit([asdict(cast(Any, item)) for item in results], self.semester)
        except Exception as exc:
            self.failed.emit(str(exc))

    def _emit_progress(self, value: int, message: str) -> None:
        self.progress.emit(value, message)


class NotifyWorker(QObject):
    """Background worker for notification dispatch."""

    finished = Signal(str, object)
    failed = Signal(str, str)

    def __init__(self, request_id: str, config: NotificationConfig, title: str, summary_text: str, patch_text: str) -> None:
        """Initialize worker.

        Args:
            request_id (str): Request identifier.
            config (NotificationConfig): Notification config.
            title (str): Notification title.
            summary_text (str): Notification summary text.
            patch_text (str): Patch body text.
        """
        super().__init__()
        self.request_id = request_id
        self.config = config
        self.title = title
        self.summary_text = summary_text
        self.patch_text = patch_text

    def run(self) -> None:
        """Execute notification sending task."""
        try:
            notifier = Notifier(self.config)
            errors = notifier.send_update(
                title=self.title,
                summary_text=self.summary_text,
                patch_text=self.patch_text,
            )
            self.finished.emit(self.request_id, errors)
        except Exception as exc:
            self.failed.emit(self.request_id, str(exc))


class ServicePreloadWorker(QObject):
    """Background worker for preloading scholarship service module/class."""

    finished = Signal()
    failed = Signal(str)
    progress = Signal(int, str)

    def __init__(self, preload_handler: Callable[[], object]) -> None:
        """Initialize worker.

        Args:
            preload_handler (Callable[[], object]): Callable used to preload service class/module.
        """
        super().__init__()
        self._preload_handler = preload_handler

    def run(self) -> None:
        """Execute preload task."""
        try:
            self.progress.emit(15, "初始化檢查服務")
            self._preload_handler()
            self.progress.emit(100, "檢查服務載入完成")
            self.finished.emit()
        except Exception as exc:
            self.failed.emit(str(exc))
