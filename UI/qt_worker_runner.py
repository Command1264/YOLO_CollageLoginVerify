from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, cast

from PySide6.QtCore import QObject, QThread


class WorkerSignalsProtocol(Protocol):
    def connect(self, slot: Callable[..., Any]) -> Any:
        ...


class QtWorkerProtocol(Protocol):
    def moveToThread(self, thread: QThread) -> None:
        ...

    def run(self) -> None:
        ...

    @property
    def finished(self) -> WorkerSignalsProtocol:
        ...

    @property
    def failed(self) -> WorkerSignalsProtocol:
        ...


class QtWorkerRunner:
    """Start and track QObject workers running on QThread."""

    def __init__(self, owner: QObject) -> None:
        """Initialize runner.

        Args:
            owner (QObject): Owner QObject used as QThread parent.
        """
        self._owner = owner
        self._active_tasks: list[tuple[QThread, QObject]] = []

    def run(self, worker_obj: QObject, ok_handler: Callable[..., Any], err_handler: Callable[..., Any]) -> None:
        """Run one worker with success and error handlers.

        Args:
            worker_obj (QObject): Worker exposing run/finished/failed.
            ok_handler (Callable): Success signal callback.
            err_handler (Callable): Error signal callback.
        """
        worker = cast(QtWorkerProtocol, worker_obj)
        thread = QThread(self._owner)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.finished.connect(ok_handler)
        worker.failed.connect(err_handler)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(lambda: self._cleanup_task(thread))
        thread.finished.connect(thread.deleteLater)
        self._active_tasks.append((thread, worker_obj))
        thread.start()

    def _cleanup_task(self, target_thread: QThread) -> None:
        self._active_tasks = [
            (thread, worker)
            for thread, worker in self._active_tasks
            if thread is not target_thread
        ]
