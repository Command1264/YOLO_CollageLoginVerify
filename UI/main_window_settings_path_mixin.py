from __future__ import annotations

from typing import Any

from pathlib import Path
import sys

from PySide6.QtWidgets import QFileDialog, QLineEdit


class MainWindowSettingsPathMixin:
    def _get_user_path_base_dir(self: Any) -> Path:
        if getattr(sys, "frozen", False):
            return Path(sys.executable).resolve().parent
        return Path(__file__).resolve().parents[1]

    def _get_default_linked_users_file(self: Any, provider: str) -> str:
        return self.settings_controller.get_default_linked_users_file(provider)

    def _default_path_store_mode(self: Any) -> dict[str, bool]:
        return self.settings_controller.default_path_store_mode()

    def _get_path_store_mode_config(self: Any) -> dict:
        cfg = self.config.setdefault("path_store_mode", {})
        if not isinstance(cfg, dict):
            cfg = {}
            self.config["path_store_mode"] = cfg
        return cfg

    def _is_path_store_relative(self: Any, key: str) -> bool:
        cfg = self._get_path_store_mode_config()
        default_value = self._default_path_store_mode().get(key, True)
        return bool(cfg.get(key, default_value))

    def _set_path_store_relative(self: Any, key: str, enabled: bool) -> None:
        cfg = self._get_path_store_mode_config()
        cfg[key] = bool(enabled)

    def _resolve_display_path(self: Any, stored_path: str, fallback_abs_path: str) -> str:
        return self.settings_controller.resolve_display_path(stored_path, fallback_abs_path)

    def _to_storage_path(self: Any, abs_path: str, use_relative: bool) -> str:
        return self.settings_controller.to_storage_path(abs_path, use_relative)

    def _normalize_path_text(self: Any, path_text: str) -> str:
        return self.settings_controller.normalize_path_text(path_text)

    def _normalize_to_absolute_path_text(self: Any, path_text: str) -> str:
        return self.settings_controller.normalize_to_absolute_path_text(path_text)

    def _normalize_captcha_server_path(self: Any, path_text: str) -> str:
        return self.settings_controller.normalize_captcha_server_path(path_text)

    def _normalize_captcha_server_path_in_widget(self: Any) -> None:
        if not hasattr(self, "captcha_server_path"):
            return
        self.captcha_server_path.setText(
            self._normalize_captcha_server_path(self.captcha_server_path.text())
        )

    def _set_normalized_path_to_line_edit(self: Any, line_edit: QLineEdit, path_text: str) -> str:
        normalized = self._normalize_to_absolute_path_text(path_text)
        line_edit.setText(normalized)
        return normalized

    def _get_default_picker_start_dir(self: Any) -> str:
        return self.settings_controller.get_default_picker_start_dir()

    def _resolve_picker_start_dir(self: Any, path_text: str) -> str:
        return self.settings_controller.resolve_picker_start_dir(path_text)

    def _normalize_and_apply_path(self: Any, line_edit: QLineEdit, fallback_path: str) -> tuple[str, bool]:
        original = line_edit.text().strip()
        selected = original or fallback_path
        normalized = self._set_normalized_path_to_line_edit(line_edit, selected)
        corrected = ("\\" in original) and (original != normalized)
        return normalized, corrected

    def _build_path_corrected_message(self: Any, corrected_entries: list[tuple[str, str]]) -> str:
        if len(corrected_entries) == 0:
            return ""
        lines = ['已自動將路徑中的 "\\\\" 修正為 "/"：']
        for title, path_text in corrected_entries:
            lines.append(f"- {title}: {path_text}")
        return "\n".join(lines)

    def _browse_model_file(self: Any) -> None:
        current_path = self.login_model_path.text().strip() or self._get_default_model_path()
        start_dir = self._resolve_picker_start_dir(current_path)
        selected_file, _ = QFileDialog.getOpenFileName(
            self,
            "選擇模型檔案",
            start_dir,
            "PyTorch Model (*.pt);;All Files (*.*)",
        )
        if not selected_file:
            return
        self._set_normalized_path_to_line_edit(self.login_model_path, selected_file)

    def _browse_captcha_server_cert_file(self: Any) -> None:
        current_path = self.captcha_server_cert_file.text().strip() or self._get_default_https_cert_file()
        start_dir = self._resolve_picker_start_dir(current_path)
        selected_file, _ = QFileDialog.getOpenFileName(
            self,
            "選擇 HTTPS 憑證檔",
            start_dir,
            "PEM Files (*.pem);;All Files (*.*)",
        )
        if not selected_file:
            return
        self._set_normalized_path_to_line_edit(self.captcha_server_cert_file, selected_file)

    def _browse_captcha_server_key_file(self: Any) -> None:
        current_path = self.captcha_server_key_file.text().strip() or self._get_default_https_key_file()
        start_dir = self._resolve_picker_start_dir(current_path)
        selected_file, _ = QFileDialog.getOpenFileName(
            self,
            "選擇 HTTPS 私鑰檔",
            start_dir,
            "PEM Files (*.pem);;All Files (*.*)",
        )
        if not selected_file:
            return
        self._set_normalized_path_to_line_edit(self.captcha_server_key_file, selected_file)

    def _browse_discord_linked_users_dir(self: Any) -> None:
        self._browse_linked_users_dir("discord", self.discord_linked_users_file)

    def _browse_telegram_linked_users_dir(self: Any) -> None:
        self._browse_linked_users_dir("telegram", self.telegram_linked_users_file)

    def _browse_discord_linked_users_file(self: Any) -> None:
        self._browse_linked_users_file("discord", self.discord_linked_users_file)

    def _browse_telegram_linked_users_file(self: Any) -> None:
        self._browse_linked_users_file("telegram", self.telegram_linked_users_file)

    def _browse_linked_users_file(self: Any, provider: str, line_edit: QLineEdit) -> None:
        current_path = line_edit.text().strip() or self._get_default_linked_users_file(provider)
        start_dir = self._resolve_picker_start_dir(current_path)
        selected_file, _ = QFileDialog.getOpenFileName(
            self,
            f"選擇{provider.capitalize()}訂閱檔案",
            start_dir,
            "JSON Files (*.json);;All Files (*.*)",
        )
        if not selected_file:
            return
        self._set_normalized_path_to_line_edit(line_edit, selected_file)

    def _browse_linked_users_dir(self: Any, provider: str, line_edit: QLineEdit) -> None:
        current_path = line_edit.text().strip() or self._get_default_linked_users_file(provider)
        start_dir = self._resolve_picker_start_dir(current_path)
        selected_dir = QFileDialog.getExistingDirectory(
            self,
            f"選擇{provider.capitalize()}訂閱檔案資料夾",
            start_dir,
        )
        if not selected_dir:
            return
        selected_file = Path(selected_dir) / f"{provider.lower()}_linked_users.json"
        self._set_normalized_path_to_line_edit(line_edit, str(selected_file))

    def _normalize_linked_users_path_for_save(self: Any, provider: str, raw_path: str) -> str:
        return self.settings_controller.normalize_linked_users_path_for_save(provider, raw_path)

    def _ensure_linked_users_file_exists(self: Any, file_path: str) -> None:
        self.settings_controller.ensure_linked_users_file_exists(file_path)

    def _get_default_model_path(self: Any) -> str:
        return self.settings_controller.get_default_model_path()

    def _get_default_https_cert_dir(self: Any) -> str:
        return self.settings_controller.get_default_https_cert_dir()

    def _get_default_https_cert_file(self: Any) -> str:
        return self.settings_controller.get_default_https_cert_file()

    def _get_default_https_key_file(self: Any) -> str:
        return self.settings_controller.get_default_https_key_file()
