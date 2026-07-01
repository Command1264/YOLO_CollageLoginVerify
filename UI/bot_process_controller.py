from __future__ import annotations

import subprocess
from pathlib import Path


class BotProcessController:
    """Manage bot process lifecycle state and log-file helpers."""

    def __init__(self) -> None:
        self.processes: dict[str, subprocess.Popen] = {}
        self.last_exit: dict[str, int | None] = {"discord": None, "telegram": None}

    def get_process(self, bot_name: str) -> subprocess.Popen | None:
        """Get tracked bot process by name."""
        return self.processes.get(bot_name)

    def set_process(self, bot_name: str, process: subprocess.Popen) -> None:
        """Track running process and reset exit code."""
        self.processes[bot_name] = process
        self.last_exit[bot_name] = None

    def pop_process(self, bot_name: str) -> subprocess.Popen | None:
        """Remove and return tracked process."""
        return self.processes.pop(bot_name, None)

    def set_exit_code(self, bot_name: str, code: int | None) -> None:
        """Set last exit code for one bot."""
        self.last_exit[bot_name] = code

    def should_enable(self, provider: str, bot_name: str) -> bool:
        """Return whether bot should be active under provider setting."""
        normalized_provider = provider.strip().lower()
        if bot_name == "discord":
            return normalized_provider in {"discord", "both"}
        if bot_name == "telegram":
            return normalized_provider in {"telegram", "both"}
        return False

    def get_status_text(self, provider: str, bot_name: str) -> str:
        """Build bot status text for UI."""
        need = self.should_enable(provider, bot_name)
        process = self.get_process(bot_name)
        if not need:
            return "未啟用（依通知管道設定）"
        if process is None:
            return "未啟動"
        poll_result = process.poll()
        if poll_result is None:
            return "執行中"
        if poll_result == 0:
            return "已結束（code=0）"
        return f"異常結束（code={poll_result}）"

    def stop_process(
        self,
        bot_name: str,
        lifecycle_notify_enabled: bool,
        spawn_shutdown_notifier,
    ) -> None:
        """Stop one bot process with graceful timeout and fallback kill."""
        process = self.get_process(bot_name)
        if process is None:
            return
        was_running = process.poll() is None
        if was_running:
            if lifecycle_notify_enabled:
                spawn_shutdown_notifier(bot_name)
            try:
                process.terminate()
            except Exception:
                pass

            try:
                process.wait(timeout=0.5)
            except Exception:
                pass

            if process.poll() is None:
                try:
                    process.kill()
                except Exception:
                    pass

                try:
                    process.wait(timeout=0.5)
                except Exception:
                    pass
        self.set_exit_code(bot_name, process.poll())
        self.pop_process(bot_name)

    def resolve_latest_log_file(
        self,
        bot_name: str,
        log_dir: Path,
        min_mtime: float | None = None,
    ) -> Path | None:
        """Resolve latest bot log file under log directory."""
        pattern_map = {
            "discord": "discord_*.log",
            "telegram": "telegram_*.log",
        }
        pattern = pattern_map.get(bot_name, "*.log")
        files = list(log_dir.glob(pattern))
        if min_mtime is not None:
            files = [
                file for file in files
                if file.exists() and file.stat().st_mtime >= min_mtime
            ]
        if len(files) == 0:
            return None
        files.sort(key=lambda file: file.stat().st_mtime, reverse=True)
        return files[0]

    def tail_log_file_text(self, file_path: Path, line_limit: int = 200) -> str:
        """Return tail text from a log file."""
        with file_path.open("r", encoding="utf-8", errors="replace") as file:
            lines = file.readlines()
        tail = lines[-line_limit:]
        return "".join(tail).rstrip() or "（log 檔目前為空）"
