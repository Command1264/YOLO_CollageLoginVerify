from __future__ import annotations

import time
import threading
from pathlib import Path

import portalocker

from utils.app_paths import get_app_data_dir, get_runtime_base_dir


class SingleInstanceFileLock:
    """Cross-process single instance lock with retry-acquire support."""

    def __init__(self, lock_path: Path) -> None:
        self.lock_path = lock_path
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self._file = None
        self._has_lock = False
        self._retry_thread: threading.Thread | None = None
        self._retry_stop = threading.Event()
        self._mutex = threading.Lock()

    def has_lock(self) -> bool:
        with self._mutex:
            return self._has_lock

    def try_acquire(self) -> bool:
        with self._mutex:
            if self._has_lock:
                return True
            if self._file is None:
                self._file = self.lock_path.open("a+")
            try:
                portalocker.lock(
                    self._file,
                    portalocker.LockFlags.EXCLUSIVE | portalocker.LockFlags.NON_BLOCKING,
                )
                self._has_lock = True
                return True
            except Exception:
                return False

    def start_retry_acquire(self, interval_sec: float = 1.0) -> None:
        if self._retry_thread is not None and self._retry_thread.is_alive():
            return
        self._retry_stop.clear()
        self._retry_thread = threading.Thread(
            target=self._retry_loop,
            args=(max(interval_sec, 0.2),),
            daemon=True,
        )
        self._retry_thread.start()

    def _retry_loop(self, interval_sec: float) -> None:
        while not self._retry_stop.is_set():
            if self.try_acquire():
                return
            time.sleep(interval_sec)

    def release(self) -> None:
        self._retry_stop.set()
        with self._mutex:
            if self._file is None:
                return
            if self._has_lock:
                try:
                    portalocker.unlock(self._file)
                except Exception:
                    pass
            self._has_lock = False
            try:
                self._file.close()
            except Exception:
                pass
            self._file = None


def ask_duplicate_launch_confirm() -> bool:
    """Ask whether to launch a second instance."""
    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)
        answer = messagebox.askyesno(
            "重複啟動確認",
            "偵測到程式已在執行中。\n是否仍要重複開啟？",
            parent=root,
        )
        root.destroy()
        return bool(answer)
    except Exception:
        return False


def prepare_single_instance_lock() -> SingleInstanceFileLock:
    """Build and acquire single-instance lock with retry fallback."""
    lock_path = get_app_data_dir(get_runtime_base_dir()) / "app_instance.lock"
    instance_lock = SingleInstanceFileLock(lock_path)
    if instance_lock.try_acquire():
        return instance_lock
    if not ask_duplicate_launch_confirm():
        raise SystemExit(0)
    instance_lock.start_retry_acquire(interval_sec=1.0)
    return instance_lock


def should_enable_single_instance_lock(argv: list[str]) -> bool:
    """Return whether single-instance lock should be enabled."""
    if "--bot" in argv:
        return False
    if "--lifecycle-notify" in argv:
        return False
    return True
