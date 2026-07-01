from __future__ import annotations

from typing import Any

import os
import subprocess
import sys
import time
from pathlib import Path

from PySide6.QtWidgets import QPlainTextEdit

from utils.app_paths import get_bot_log_dir, to_universal_path


class MainWindowBotRuntimeMixin:
    def _sync_bot_processes(self: Any) -> None:
        provider = self.provider_combo.currentText().strip().lower()
        self._sync_bot_processes_by_provider(provider)

    def _start_background_bots_on_launch(self: Any) -> None:
        provider = self.config.get("notifier", {}).get("provider", "none")
        provider = str(provider).strip().lower()
        self._sync_bot_processes_by_provider(provider)
        idx = self.provider_combo.findText(provider)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)

    def _sync_bot_processes_by_provider(self: Any, provider: str) -> None:
        need_discord = self.bot_controller.should_enable(provider, "discord")
        need_telegram = self.bot_controller.should_enable(provider, "telegram")

        if need_discord:
            self._ensure_bot_running("discord")
        else:
            self._stop_bot("discord")

        if need_telegram:
            self._ensure_bot_running("telegram")
        else:
            self._stop_bot("telegram")
        self._update_bot_status_labels()

    def _ensure_bot_running(self: Any, bot_name: str) -> None:
        process = self.bot_controller.get_process(bot_name)
        if process is not None and process.poll() is None:
            return

        script_map = {
            "discord": "discordBot.py",
            "telegram": "telegramBot.py",
        }
        script_name = script_map.get(bot_name)
        if script_name is None:
            self.statusBar().showMessage(f"{bot_name} Bot 腳本不存在，無法啟動", 8000)
            return
        if (not getattr(sys, "frozen", False)) and (not (self.messaging_dir / script_name).exists()):
            self.statusBar().showMessage(f"{bot_name} Bot 腳本不存在，無法啟動", 8000)
            return

        try:
            env = os.environ.copy()
            project_root = str(self.project_root)
            messaging_path = str(self.messaging_dir)
            current_pythonpath = env.get("PYTHONPATH", "")
            pythonpath_parts = [project_root, messaging_path]
            if current_pythonpath:
                pythonpath_parts.append(current_pythonpath)
            env["PYTHONPATH"] = os.pathsep.join(pythonpath_parts)
            env["CYUT_APP_BASE_DIR"] = to_universal_path(self.runtime_base_dir)
            env["CYUT_DISCORD_LINKED_USERS_FILE"] = to_universal_path(self.discord_linked_users_file.text().strip())
            env["CYUT_TELEGRAM_LINKED_USERS_FILE"] = to_universal_path(self.telegram_linked_users_file.text().strip())
            env["CYUT_DISCORD_LOG_DIR"] = to_universal_path(get_bot_log_dir("discord", self.runtime_base_dir))
            env["CYUT_TELEGRAM_LOG_DIR"] = to_universal_path(get_bot_log_dir("telegram", self.runtime_base_dir))
            env["CYUT_DISCORD_BOT_TOKEN"] = self.discord_bot_token.text().strip()
            env["CYUT_TELEGRAM_BOT_TOKEN"] = self.telegram_token.text().strip()
            env["CYUT_LOGIN_ACCOUNT"] = self.login_account.text().strip()
            env["CYUT_LOGIN_PASSWORD"] = self.login_password.text().strip()
            env["CYUT_NOTIFY_BOT_LIFECYCLE"] = "1" if self._is_lifecycle_notify_enabled() else "0"

            bot_args = self._build_bot_process_args(bot_name)
            kwargs = {
                "args": bot_args,
                "cwd": str(self.runtime_base_dir if getattr(sys, "frozen", False) else self.messaging_dir),
                "env": env,
            }
            if sys.platform.startswith("win"):
                kwargs["creationflags"] = subprocess.CREATE_NO_WINDOW | subprocess.CREATE_NEW_PROCESS_GROUP
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                kwargs["startupinfo"] = startupinfo
            start_ts = time.time()
            self.bot_controller.set_process(bot_name, subprocess.Popen(**kwargs))
            self._bot_log_session_start[bot_name] = start_ts
            self._last_log_snapshot[bot_name] = ""
            self.statusBar().showMessage(f"{bot_name} Bot 已啟動", 5000)
        except Exception as exc:
            self._bot_log_session_start[bot_name] = None
            self.statusBar().showMessage(f"{bot_name} Bot 啟動失敗: {exc}", 8000)

    def _build_bot_process_args(self: Any, bot_name: str) -> list[str]:
        if getattr(sys, "frozen", False):
            return [sys.executable, "--bot", bot_name]
        script_path = Path(self.settings_controller.script_path).resolve()
        return [self._get_background_python_executable(), str(script_path), "--bot", bot_name]

    def _stop_bot(self: Any, bot_name: str) -> None:
        self.bot_controller.stop_process(
            bot_name=bot_name,
            lifecycle_notify_enabled=self._is_lifecycle_notify_enabled(),
            spawn_shutdown_notifier=self._spawn_shutdown_notifier_process,
        )
        self._bot_log_session_start[bot_name] = None

    def _stop_all_bots(self: Any) -> None:
        self._stop_bot("discord")
        self._stop_bot("telegram")
        self._update_bot_status_labels()

    def _update_bot_status_labels(self: Any) -> None:
        self.discord_status_label.setText(self._get_bot_status_text("discord"))
        self.telegram_status_label.setText(self._get_bot_status_text("telegram"))

    def _get_bot_status_text(self: Any, bot_name: str) -> str:
        provider = self.provider_combo.currentText().strip().lower()
        return self.bot_controller.get_status_text(provider, bot_name)

    def _refresh_bot_logs(self: Any) -> None:
        discord_text = self._tail_log_file("discord")
        if discord_text != self._last_log_snapshot["discord"]:
            self._set_log_view_text_preserve_scroll(self.discord_log_view, discord_text)
            self._last_log_snapshot["discord"] = discord_text

        telegram_text = self._tail_log_file("telegram")
        if telegram_text != self._last_log_snapshot["telegram"]:
            self._set_log_view_text_preserve_scroll(self.telegram_log_view, telegram_text)
            self._last_log_snapshot["telegram"] = telegram_text

    def _tail_log_file(self: Any, bot_name: str, line_limit: int = 200) -> str:
        process = self.bot_controller.get_process(bot_name)
        if process is None:
            return f"({bot_name} 尚未啟動，等待本次啟動 log)"

        file_path = self._resolve_latest_log_file(bot_name)
        if file_path is None:
            default_map = {
                "discord": get_bot_log_dir("discord", self.runtime_base_dir),
                "telegram": get_bot_log_dir("telegram", self.runtime_base_dir),
            }
            log_dir = self.bot_log_paths.get(bot_name, default_map.get(bot_name, self.messaging_dir / "logs"))
            return f"({to_universal_path(log_dir)} 尚無 {bot_name} log 檔)"
        if not file_path.exists():
            return f"({to_universal_path(file_path)} 尚無 log 檔)"
        try:
            return self.bot_controller.tail_log_file_text(file_path, line_limit=line_limit)
        except Exception as exc:
            return f"讀取 log 失敗: {exc}"

    def _resolve_latest_log_file(self: Any, bot_name: str) -> Path | None:
        default_map = {
            "discord": get_bot_log_dir("discord", self.runtime_base_dir),
            "telegram": get_bot_log_dir("telegram", self.runtime_base_dir),
        }
        log_dir = self.bot_log_paths.get(bot_name, default_map.get(bot_name, self.messaging_dir / "logs"))
        session_start = self._bot_log_session_start.get(bot_name)
        return self.bot_controller.resolve_latest_log_file(
            bot_name,
            log_dir,
            min_mtime=session_start,
        )

    def _apply_log_wrap_settings(self: Any) -> None:
        self.discord_log_view.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.WidgetWidth
            if self.discord_wrap_checkbox.isChecked()
            else QPlainTextEdit.LineWrapMode.NoWrap
        )
        self.telegram_log_view.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.WidgetWidth
            if self.telegram_wrap_checkbox.isChecked()
            else QPlainTextEdit.LineWrapMode.NoWrap
        )

    def _spawn_shutdown_notifier_process(self: Any, bot_name: str) -> None:
        base_env = os.environ.copy()
        base_env["CYUT_APP_BASE_DIR"] = to_universal_path(self.runtime_base_dir)
        base_env["CYUT_DISCORD_LINKED_USERS_FILE"] = to_universal_path(self.discord_linked_users_file.text().strip())
        base_env["CYUT_TELEGRAM_LINKED_USERS_FILE"] = to_universal_path(self.telegram_linked_users_file.text().strip())
        base_env["CYUT_DISCORD_BOT_TOKEN"] = self.discord_bot_token.text().strip()
        base_env["CYUT_TELEGRAM_BOT_TOKEN"] = self.telegram_token.text().strip()
        base_env["PYTHONPATH"] = os.pathsep.join(
            [str(self.project_root), os.environ.get("PYTHONPATH", "")]
        ).strip(os.pathsep)

        args = [sys.executable, "--lifecycle-notify", bot_name, "--lifecycle-action", "shutdown"]
        if not getattr(sys, "frozen", False):
            script_path = Path(self.settings_controller.script_path).resolve()
            args = [
                self._get_background_python_executable(),
                str(script_path),
                "--lifecycle-notify",
                bot_name,
                "--lifecycle-action",
                "shutdown",
            ]

        kwargs = {
            "args": args,
            "cwd": str(self.runtime_base_dir if getattr(sys, "frozen", False) else self.project_root),
            "env": base_env,
            "stdout": subprocess.DEVNULL,
            "stderr": subprocess.DEVNULL,
        }
        if sys.platform.startswith("win"):
            kwargs["creationflags"] = (
                subprocess.CREATE_NO_WINDOW |
                subprocess.DETACHED_PROCESS |
                subprocess.CREATE_NEW_PROCESS_GROUP
            )
            startupinfo = subprocess.STARTUPINFO()
            startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
            kwargs["startupinfo"] = startupinfo
        try:
            subprocess.Popen(**kwargs)
        except Exception as exc:
            print(f"{bot_name} 關機補發子程序啟動失敗: {exc}")

    def _get_background_python_executable(self: Any) -> str:
        if not sys.platform.startswith("win"):
            return sys.executable
        exe_path = Path(sys.executable)
        pythonw_path = exe_path.with_name("pythonw.exe")
        if pythonw_path.exists():
            return str(pythonw_path)
        return sys.executable
