from __future__ import annotations

from typing import Any

import uuid
from dataclasses import asdict

from PySide6.QtCore import QThread, Qt
from PySide6.QtWidgets import QMessageBox, QLineEdit, QTableWidgetItem

from UI.async_workers import NotifyWorker
from UI.notifier import NotificationConfig
from utils.app_paths import to_universal_path


class MainWindowNotifyConfigMixin:
    def _current_notifier_config(self: Any) -> NotificationConfig:
        return NotificationConfig(
            provider=self.provider_combo.currentText(),
            discord_bot_token=self.discord_bot_token.text().strip(),
            discord_linked_users_file=to_universal_path(self.discord_linked_users_file.text().strip()),
            telegram_token=self.telegram_token.text().strip(),
            telegram_linked_users_file=to_universal_path(self.telegram_linked_users_file.text().strip()),
        )

    def _is_lifecycle_notify_enabled(self: Any) -> bool:
        return self.notify_lifecycle_checkbox.isChecked()

    def _save_notify_config(self: Any) -> None:
        discord_raw = self.discord_linked_users_file.text().strip()
        telegram_raw = self.telegram_linked_users_file.text().strip()
        save_result = self.settings_save_service.prepare_notify_save(
            notifier_data=asdict(self._current_notifier_config()),
            discord_raw_path=discord_raw,
            telegram_raw_path=telegram_raw,
            discord_store_relative=self.discord_linked_users_store_relative.isChecked(),
            telegram_store_relative=self.telegram_linked_users_store_relative.isChecked(),
            notify_bot_lifecycle=self._is_lifecycle_notify_enabled(),
        )
        if not save_result.success:
            QMessageBox.critical(self, "通知設定", save_result.error_message)
            return
        self.discord_linked_users_file.setText(save_result.discord_path)
        self.telegram_linked_users_file.setText(save_result.telegram_path)
        self._set_path_store_relative(
            "discord_linked_users_file",
            self.discord_linked_users_store_relative.isChecked(),
        )
        self._set_path_store_relative(
            "telegram_linked_users_file",
            self.telegram_linked_users_store_relative.isChecked(),
        )
        self.config["notifier"] = save_result.notifier_data
        self._save_config()
        self._apply_runtime_env_from_config()
        self._sync_bot_processes()
        corrected_message = self._build_path_corrected_message(save_result.corrected_entries)
        message = "通知設定已儲存。"
        if corrected_message != "":
            message = f"{message}\n\n{corrected_message}"
        QMessageBox.information(self, "通知設定", message)

    def _save_student_login_config(self: Any) -> None:
        login_cfg = self.config.setdefault("login", {})
        login_cfg["account"] = self.login_account.text().strip()
        login_cfg["password"] = self.login_password.text().strip()
        self._save_config()
        self._apply_runtime_env_from_config()
        QMessageBox.information(self, "學生系統登入設定", "學生系統登入設定已儲存。")

    def _save_model_server_config(self: Any) -> None:
        captcha_cfg = self._current_captcha_server_config()
        save_result = self.settings_save_service.prepare_model_server_save(
            model_raw_path=self.login_model_path.text().strip(),
            model_fallback_path=self._get_default_model_path(),
            model_store_relative=self.login_model_store_relative.isChecked(),
            captcha_cfg=captcha_cfg,
            cert_raw_path=self.captcha_server_cert_file.text().strip(),
            cert_fallback_path=self._get_default_https_cert_file(),
            cert_store_relative=self.captcha_server_cert_store_relative.isChecked(),
            key_raw_path=self.captcha_server_key_file.text().strip(),
            key_fallback_path=self._get_default_https_key_file(),
            key_store_relative=self.captcha_server_key_store_relative.isChecked(),
        )
        if not save_result.success:
            QMessageBox.warning(self, "模型與伺服器設定", save_result.error_message)
            return
        self.login_model_path.setText(save_result.model_path)
        self.captcha_server_cert_file.setText(save_result.cert_path)
        self.captcha_server_key_file.setText(save_result.key_path)
        self._set_path_store_relative("model_path", self.login_model_store_relative.isChecked())
        self._set_path_store_relative(
            "captcha_cert_file",
            self.captcha_server_cert_store_relative.isChecked(),
        )
        self._set_path_store_relative(
            "captcha_key_file",
            self.captcha_server_key_store_relative.isChecked(),
        )
        captcha_cfg_raw = save_result.verify_data.get("captcha_server", {})
        captcha_cfg_saved: dict[str, object] = {}
        if isinstance(captcha_cfg_raw, dict):
            captcha_cfg_saved = {str(k): v for k, v in captcha_cfg_raw.items()}
        self.captcha_server_host.setText(str(captcha_cfg_saved.get("host", captcha_cfg.get("host", "127.0.0.1"))))
        self.captcha_server_path.setText(str(captcha_cfg_saved.get("path", captcha_cfg.get("path", "/solve_captcha"))))

        verify_cfg = self.config.setdefault("verify", {})
        verify_cfg["model_path"] = str(save_result.verify_data.get("model_path", ""))
        verify_cfg["captcha_server"] = captcha_cfg_saved
        self._save_config()
        self._apply_runtime_env_from_config()
        self._sync_captcha_server_from_config()
        corrected_message = self._build_path_corrected_message(save_result.corrected_entries)
        message = "模型與伺服器設定已儲存。"
        if corrected_message != "":
            message = f"{message}\n\n{corrected_message}"
        QMessageBox.information(self, "模型與伺服器設定", message)

    def _save_login_config(self: Any) -> None:
        """Backward-compatible alias for old action."""
        self._save_model_server_config()

    def _toggle_password_visibility(self: Any) -> None:
        self.password_visible = not self.password_visible
        if self.password_visible:
            self.login_password.setEchoMode(QLineEdit.EchoMode.Normal)
            self.password_toggle_btn.setText("🙈")
            self.password_toggle_btn.setToolTip("隱藏密碼")
            return
        self.login_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.password_toggle_btn.setText("👁")
        self.password_toggle_btn.setToolTip("顯示密碼")

    def _send_test_notify(self: Any) -> None:
        self._dispatch_notification_async(
            self._current_notifier_config(),
            title="[測試通知] 系統連線測試",
            summary_text="這是測試訊息，若你收到表示通知設定成功。",
            patch_text="--- before\n+++ after\n+ 測試新增內容",
            show_success_popup=True,
        )

    def _dispatch_notification_async(
        self: Any,
        config: NotificationConfig,
        title: str,
        summary_text: str,
        patch_text: str,
        show_success_popup: bool = False,
    ) -> None:
        request_id = str(uuid.uuid4())
        worker = NotifyWorker(request_id, config, title, summary_text, patch_text)
        thread = QThread(self)
        worker.moveToThread(thread)
        self._notify_popup_flags[request_id] = show_success_popup

        def cleanup() -> None:
            for idx, (item_thread, _item_worker) in enumerate(self._notification_tasks):
                if item_thread is thread:
                    self._notification_tasks.pop(idx)
                    break

        thread.started.connect(worker.run)
        worker.finished.connect(self._on_notify_worker_finished)
        worker.failed.connect(self._on_notify_worker_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(cleanup)
        thread.finished.connect(thread.deleteLater)

        self._notification_tasks.append((thread, worker))
        thread.start()

    def _on_notify_worker_finished(self: Any, request_id: str, errors_obj: object) -> None:
        show_success_popup = self._notify_popup_flags.pop(request_id, False)
        errors = errors_obj if isinstance(errors_obj, list) else []
        if len(errors) != 0:
            self.statusBar().showMessage("通知發送有錯誤，請看通知設定", 8000)
            if show_success_popup:
                QMessageBox.warning(self, "測試通知", "\n".join(errors))
            return
        if show_success_popup:
            QMessageBox.information(self, "測試通知", "測試訊息已送出。")

    def _on_notify_worker_failed(self: Any, request_id: str, message: str) -> None:
        show_success_popup = self._notify_popup_flags.pop(request_id, False)
        self.statusBar().showMessage("通知發送失敗", 8000)
        if show_success_popup:
            QMessageBox.critical(self, "測試通知", message)

    def _append_history(self: Any, ts: str, dataset: str, status: str, summary: str, patch_text: str) -> None:
        self.history_store.append_entries(
            [
                {
                    "time": ts,
                    "dataset": dataset,
                    "status": status,
                    "summary": summary,
                    "patch_text": patch_text,
                }
            ]
        )

    def _load_history_table(self: Any) -> None:
        history = self.history_store.load_entries()
        self.history_table.setRowCount(0)
        for entry in reversed(history):
            row = self.history_table.rowCount()
            self.history_table.insertRow(row)
            time_item = QTableWidgetItem(entry.get("time", ""))
            time_item.setData(Qt.ItemDataRole.UserRole, entry.get("patch_text", ""))
            self.history_table.setItem(row, 0, time_item)
            self.history_table.setItem(row, 1, QTableWidgetItem(entry.get("dataset", "")))
            self.history_table.setItem(row, 2, QTableWidgetItem(entry.get("status", "")))
            self.history_table.setItem(row, 3, QTableWidgetItem(entry.get("summary", "")))

    def _on_history_double_click(self: Any, row: int, _column: int) -> None:
        time_item = self.history_table.item(row, 0)
        if time_item is None:
            return
        patch_text = time_item.data(Qt.ItemDataRole.UserRole) or ""
        if not patch_text.strip():
            self.diff_view.setPlainText("（此筆紀錄沒有差異內容）")
            return
        dataset_item = self.history_table.item(row, 1)
        dataset = dataset_item.text() if dataset_item is not None else "未知資料集"
        self.diff_view.setPlainText(f"### {dataset}\n{patch_text}")
