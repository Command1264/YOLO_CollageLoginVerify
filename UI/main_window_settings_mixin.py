from __future__ import annotations

from typing import Any

import json
import os
import shutil
from pathlib import Path

from UI.config_schema import AppConfig, ConfigDefaults, get_legacy_https_cert_candidates, is_legacy_linked_users_value
from utils.app_paths import to_universal_path

class MainWindowSettingsMixin:
    def _load_config(self: Any) -> dict:
        raw = {}
        if self.config_path.exists():
            loaded = self._read_json(self.config_path)
            if isinstance(loaded, dict):
                raw = loaded
        config_obj = AppConfig.from_dict(raw, self._build_config_defaults())
        normalized = config_obj.to_dict()
        if raw != normalized:
            self._write_json(self.config_path, normalized)
        return normalized

    def _migrate_legacy_files(self: Any) -> None:
        migration_pairs = [
            (self.project_root / "cyutLoginCookies.json", self.application_dir / "cyutLoginCookies.json"),
            (self.project_root / "token.json", self.application_dir / "token.json"),
            (self.project_root / "OAuthCredentials.json", self.application_dir / "OAuthCredentials.json"),
            (self.project_root / "MessagingApp" / "discord_linked_users.json", Path(self._get_default_linked_users_file("discord"))),
            (self.project_root / "MessagingApp" / "telegram_linked_users.json", Path(self._get_default_linked_users_file("telegram"))),
        ]
        for src, dst in migration_pairs:
            try:
                if (not src.exists()) or dst.exists():
                    continue
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            except Exception:
                continue

    def _save_config(self: Any) -> None:
        config_obj = AppConfig.from_dict(self.config, self._build_config_defaults())
        self.config = config_obj.to_dict()
        self._write_json(self.config_path, self.config)

    def _build_config_defaults(self: Any) -> ConfigDefaults:
        return ConfigDefaults(
            default_model_path=self._get_default_model_path(),
            default_cert_file=self._get_default_https_cert_file(),
            default_key_file=self._get_default_https_key_file(),
            default_discord_linked_users_file=self._get_default_linked_users_file("discord"),
            default_telegram_linked_users_file=self._get_default_linked_users_file("telegram"),
            default_column_alignments=self._default_google_sheet_column_alignments(),
        )

    def _normalize_config_paths(self: Any) -> None:
        changed = False
        normalized = AppConfig.from_dict(self.config, self._build_config_defaults()).to_dict()
        if normalized != self.config:
            self.config = normalized
            changed = True

        verify_cfg = self.config.setdefault("verify", {})
        notifier = self.config.setdefault("notifier", {})

        old_model_default = to_universal_path(self.application_dir / "model" / "YOLO11x-google-best.pt")
        new_model_default = self._get_default_model_path()
        model_path = str(verify_cfg.get("model_path", "")).strip() or new_model_default
        if model_path == old_model_default:
            model_path = new_model_default
            changed = True
        model_abs_path = self._resolve_display_path(model_path, new_model_default)
        model_store_value = self._to_storage_path(
            model_abs_path,
            use_relative=self._is_path_store_relative("model_path"),
        )
        if str(verify_cfg.get("model_path", "")).strip() != model_store_value:
            verify_cfg["model_path"] = model_store_value
            changed = True

        captcha_server = verify_cfg.get("captcha_server", {})
        if not isinstance(captcha_server, dict):
            captcha_server = {}
            verify_cfg["captcha_server"] = captcha_server
            changed = True

        legacy_cert_candidates, legacy_key_candidates = get_legacy_https_cert_candidates(
            self._get_user_path_base_dir()
        )
        new_default_cert = self._get_default_https_cert_file()
        new_default_key = self._get_default_https_key_file()

        cert_file_raw = str(captcha_server.get("cert_file", "")).strip()
        cert_file = cert_file_raw or new_default_cert
        if cert_file in legacy_cert_candidates:
            cert_file = new_default_cert
        cert_file_abs = self._resolve_display_path(cert_file, new_default_cert)
        cert_file_store = self._to_storage_path(
            cert_file_abs,
            use_relative=self._is_path_store_relative("captcha_cert_file"),
        )
        if cert_file_raw != cert_file_store:
            captcha_server["cert_file"] = cert_file_store
            changed = True

        key_file_raw = str(captcha_server.get("key_file", "")).strip()
        key_file = key_file_raw or new_default_key
        if key_file in legacy_key_candidates:
            key_file = new_default_key
        key_file_abs = self._resolve_display_path(key_file, new_default_key)
        key_file_store = self._to_storage_path(
            key_file_abs,
            use_relative=self._is_path_store_relative("captcha_key_file"),
        )
        if key_file_raw != key_file_store:
            captcha_server["key_file"] = key_file_store
            changed = True

        defaults = {
            "discord_linked_users_file": self._get_default_linked_users_file("discord"),
            "telegram_linked_users_file": self._get_default_linked_users_file("telegram"),
        }
        for key, fallback in defaults.items():
            value = str(notifier.get(key, "")).strip()
            if (value == "") or is_legacy_linked_users_value(key, value):
                display_value = self._resolve_display_path("", fallback)
            else:
                display_value = self._resolve_display_path(value, fallback)
            normalized_value = self._to_storage_path(
                display_value,
                use_relative=self._is_path_store_relative(key),
            )
            if str(notifier.get(key, "")).strip() != normalized_value:
                notifier[key] = normalized_value
                changed = True

        if changed:
            self._save_config()

    def _apply_runtime_env_from_config(self: Any) -> None:
        login_cfg = self.config.get("login", {})
        account = str(login_cfg.get("account", "")).strip()
        password = str(login_cfg.get("password", "")).strip()
        if account:
            os.environ["CYUT_LOGIN_ACCOUNT"] = account
        if password:
            os.environ["CYUT_LOGIN_PASSWORD"] = password

        notifier_cfg = self.config.get("notifier", {})
        discord_token = str(notifier_cfg.get("discord_bot_token", "")).strip()
        telegram_token = str(notifier_cfg.get("telegram_token", "")).strip()
        if discord_token:
            os.environ["CYUT_DISCORD_BOT_TOKEN"] = discord_token
        if telegram_token:
            os.environ["CYUT_TELEGRAM_BOT_TOKEN"] = telegram_token
        verify_cfg = self.config.get("verify", {})
        model_path = str(verify_cfg.get("model_path", "")).strip()
        if model_path:
            os.environ["CYUT_VERIFY_MODEL_PATH"] = self._resolve_display_path(
                model_path,
                self._get_default_model_path(),
            )
        captcha_cfg = verify_cfg.get("captcha_server", {})
        if isinstance(captcha_cfg, dict):
            verify_server_scheme = str(captcha_cfg.get("protocol", "http")).strip().lower()
            if verify_server_scheme not in {"http", "https"}:
                verify_server_scheme = "http"
            os.environ["CYUT_VERIFY_SERVER_SCHEME"] = verify_server_scheme
            os.environ["CYUT_VERIFY_SERVER_HOST"] = str(captcha_cfg.get("host", "127.0.0.1")).strip() or "127.0.0.1"
            try:
                verify_server_port = int(captcha_cfg.get("port", 5000))
            except (TypeError, ValueError):
                verify_server_port = 5000
            os.environ["CYUT_VERIFY_SERVER_PORT"] = str(verify_server_port)
            os.environ["CYUT_VERIFY_SERVER_PATH"] = self._normalize_captcha_server_path(
                str(captcha_cfg.get("path", "/solve_captcha"))
            )
            os.environ["CYUT_VERIFY_SERVER_CERT_FILE"] = self._resolve_display_path(
                str(captcha_cfg.get("cert_file", "")).strip(),
                self._get_default_https_cert_file(),
            )
            os.environ["CYUT_VERIFY_SERVER_KEY_FILE"] = self._resolve_display_path(
                str(captcha_cfg.get("key_file", "")).strip(),
                self._get_default_https_key_file(),
            )

    def _write_json(self: Any, path: Path, data: dict | list) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("w", encoding="utf-8") as file:
            json.dump(data, file, ensure_ascii=False, indent=2)

    def _read_json(self: Any, path: Path) -> dict | list:
        with path.open("r", encoding="utf-8") as file:
            return json.load(file)
