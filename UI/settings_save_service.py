from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from UI.settings_controller import SettingsController


@dataclass
class NotifySaveResult:
    """Result payload for notifier settings save preparation."""

    success: bool
    error_message: str = ""
    discord_path: str = ""
    telegram_path: str = ""
    corrected_entries: list[tuple[str, str]] = field(default_factory=list)
    notifier_data: dict[str, object] = field(default_factory=dict)


@dataclass
class ModelServerSaveResult:
    """Result payload for model/server settings save preparation."""

    success: bool
    error_message: str = ""
    model_path: str = ""
    cert_path: str = ""
    key_path: str = ""
    corrected_entries: list[tuple[str, str]] = field(default_factory=list)
    verify_data: dict[str, object] = field(default_factory=dict)


class SettingsSaveService:
    """Build and validate settings payloads for GUI save actions."""

    def __init__(self, settings_controller: SettingsController) -> None:
        self.settings_controller = settings_controller

    def prepare_notify_save(
        self,
        notifier_data: dict[str, object],
        discord_raw_path: str,
        telegram_raw_path: str,
        discord_store_relative: bool,
        telegram_store_relative: bool,
        notify_bot_lifecycle: bool,
    ) -> NotifySaveResult:
        """Prepare notifier payload with normalized paths and file existence checks.

        Args:
            notifier_data (dict[str, object]): Base notifier data.
            discord_raw_path (str): Raw discord subscribers path text.
            telegram_raw_path (str): Raw telegram subscribers path text.
            discord_store_relative (bool): Whether discord path should be stored as relative.
            telegram_store_relative (bool): Whether telegram path should be stored as relative.
            notify_bot_lifecycle (bool): Bot lifecycle notification flag.

        Returns:
            NotifySaveResult: Preparation result.
        """
        corrected_entries: list[tuple[str, str]] = []
        discord_path = self.settings_controller.normalize_linked_users_path_for_save("discord", discord_raw_path)
        telegram_path = self.settings_controller.normalize_linked_users_path_for_save("telegram", telegram_raw_path)
        if ("\\" in discord_raw_path) and (discord_raw_path != discord_path):
            corrected_entries.append(("Discord 訂閱名單檔", discord_path))
        if ("\\" in telegram_raw_path) and (telegram_raw_path != telegram_path):
            corrected_entries.append(("Telegram 訂閱名單檔", telegram_path))
        try:
            self.settings_controller.ensure_linked_users_file_exists(discord_path)
            self.settings_controller.ensure_linked_users_file_exists(telegram_path)
        except Exception as exc:
            return NotifySaveResult(success=False, error_message=f"建立訂閱檔案失敗：{exc}")

        payload = dict(notifier_data)
        payload["discord_linked_users_file"] = self.settings_controller.to_storage_path(
            discord_path,
            use_relative=discord_store_relative,
        )
        payload["telegram_linked_users_file"] = self.settings_controller.to_storage_path(
            telegram_path,
            use_relative=telegram_store_relative,
        )
        payload["notify_bot_lifecycle"] = bool(notify_bot_lifecycle)
        return NotifySaveResult(
            success=True,
            discord_path=discord_path,
            telegram_path=telegram_path,
            corrected_entries=corrected_entries,
            notifier_data=payload,
        )

    def prepare_model_server_save(
        self,
        model_raw_path: str,
        model_fallback_path: str,
        model_store_relative: bool,
        captcha_cfg: dict[str, object],
        cert_raw_path: str,
        cert_fallback_path: str,
        cert_store_relative: bool,
        key_raw_path: str,
        key_fallback_path: str,
        key_store_relative: bool,
    ) -> ModelServerSaveResult:
        """Prepare model/server payload with normalized paths and validations.

        Args:
            model_raw_path (str): Raw model path text.
            model_fallback_path (str): Model fallback path.
            model_store_relative (bool): Whether model path should be stored as relative.
            captcha_cfg (dict[str, object]): Current captcha server config.
            cert_raw_path (str): Raw HTTPS cert path text.
            cert_fallback_path (str): HTTPS cert fallback path.
            cert_store_relative (bool): Whether cert path should be stored as relative.
            key_raw_path (str): Raw HTTPS key path text.
            key_fallback_path (str): HTTPS key fallback path.
            key_store_relative (bool): Whether key path should be stored as relative.

        Returns:
            ModelServerSaveResult: Preparation result.
        """
        corrected_entries: list[tuple[str, str]] = []
        model_source = str(model_raw_path).strip() or model_fallback_path
        model_path = self.settings_controller.normalize_to_absolute_path_text(model_source)
        if ("\\" in str(model_raw_path)) and (str(model_raw_path).strip() != model_path):
            corrected_entries.append(("模型路徑", model_path))
        if not Path(model_path).is_file():
            return ModelServerSaveResult(
                success=False,
                error_message=f"模型檔案不存在，請重新選擇：\n{model_path}",
            )

        cert_source = str(cert_raw_path).strip() or cert_fallback_path
        key_source = str(key_raw_path).strip() or key_fallback_path
        cert_path = self.settings_controller.normalize_to_absolute_path_text(cert_source)
        key_path = self.settings_controller.normalize_to_absolute_path_text(key_source)
        if ("\\" in str(cert_raw_path)) and (str(cert_raw_path).strip() != cert_path):
            corrected_entries.append(("HTTPS 憑證(cert)", cert_path))
        if ("\\" in str(key_raw_path)) and (str(key_raw_path).strip() != key_path):
            corrected_entries.append(("HTTPS 私鑰(key)", key_path))

        next_captcha_cfg = dict(captcha_cfg)
        protocol = str(next_captcha_cfg.get("protocol", "http")).strip().lower()
        if protocol not in {"http", "https"}:
            protocol = "http"
        next_captcha_cfg["protocol"] = protocol
        next_captcha_cfg["path"] = self.settings_controller.normalize_captcha_server_path(
            str(next_captcha_cfg.get("path", "/solve_captcha"))
        )
        if protocol == "https":
            if not Path(cert_path).is_file():
                return ModelServerSaveResult(
                    success=False,
                    error_message=f"HTTPS 憑證檔不存在，請重新選擇：\n{cert_path}",
                )
            if not Path(key_path).is_file():
                return ModelServerSaveResult(
                    success=False,
                    error_message=f"HTTPS 私鑰檔不存在，請重新選擇：\n{key_path}",
                )

        next_captcha_cfg["cert_file"] = self.settings_controller.to_storage_path(
            cert_path,
            use_relative=cert_store_relative,
        )
        next_captcha_cfg["key_file"] = self.settings_controller.to_storage_path(
            key_path,
            use_relative=key_store_relative,
        )
        verify_data = {
            "model_path": self.settings_controller.to_storage_path(
                model_path,
                use_relative=model_store_relative,
            ),
            "captcha_server": next_captcha_cfg,
        }
        return ModelServerSaveResult(
            success=True,
            model_path=model_path,
            cert_path=cert_path,
            key_path=key_path,
            corrected_entries=corrected_entries,
            verify_data=verify_data,
        )
