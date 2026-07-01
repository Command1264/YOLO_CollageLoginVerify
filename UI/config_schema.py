from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

from utils.app_paths import to_universal_path

LEGACY_LINKED_USERS_VALUES = {
    "discord_linked_users_file": {"MessagingApp/discord_linked_users.json", "discord_linked_users.json"},
    "telegram_linked_users_file": {"MessagingApp/telegram_linked_users.json", "telegram_linked_users.json"},
}


@dataclass
class ConfigDefaults:
    """Default values for config deserialization."""

    default_model_path: str
    default_cert_file: str
    default_key_file: str
    default_discord_linked_users_file: str
    default_telegram_linked_users_file: str
    default_column_alignments: dict[str, dict[str, str]]


@dataclass
class LoginConfig:
    account: str = ""
    password: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None) -> "LoginConfig":
        payload = raw if isinstance(raw, dict) else {}
        return cls(
            account=str(payload.get("account", "")).strip(),
            password=str(payload.get("password", "")).strip(),
        )


@dataclass
class CaptchaServerConfig:
    enabled: bool = False
    protocol: str = "http"
    host: str = "127.0.0.1"
    port: int = 5000
    path: str = "/solve_captcha"
    cert_file: str = ""
    key_file: str = ""

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None, defaults: ConfigDefaults) -> "CaptchaServerConfig":
        payload = raw if isinstance(raw, dict) else {}
        protocol = str(payload.get("protocol", "http")).strip().lower()
        if protocol not in {"http", "https"}:
            protocol = "http"
        host = str(payload.get("host", "127.0.0.1")).strip() or "127.0.0.1"
        try:
            port = int(payload.get("port", 5000))
        except (TypeError, ValueError):
            port = 5000
        if port < 1 or port > 65535:
            port = 5000
        path = str(payload.get("path", "/solve_captcha")).strip()
        if path == "":
            path = "/solve_captcha"
        if not path.startswith("/"):
            path = f"/{path}"
        cert_file = str(payload.get("cert_file", "")).strip() or defaults.default_cert_file
        key_file = str(payload.get("key_file", "")).strip() or defaults.default_key_file
        return cls(
            enabled=bool(payload.get("enabled", False)),
            protocol=protocol,
            host=host,
            port=port,
            path=path,
            cert_file=to_universal_path(cert_file),
            key_file=to_universal_path(key_file),
        )


@dataclass
class VerifyConfig:
    model_path: str
    captcha_server: CaptchaServerConfig

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None, defaults: ConfigDefaults) -> "VerifyConfig":
        payload = raw if isinstance(raw, dict) else {}
        model_path = str(payload.get("model_path", "")).strip() or defaults.default_model_path
        return cls(
            model_path=to_universal_path(model_path),
            captcha_server=CaptchaServerConfig.from_dict(payload.get("captcha_server"), defaults),
        )


@dataclass
class NotifierConfig:
    provider: str = "none"
    discord_bot_token: str = ""
    discord_linked_users_file: str = ""
    telegram_token: str = ""
    telegram_linked_users_file: str = ""
    notify_bot_lifecycle: bool = True

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None, defaults: ConfigDefaults) -> "NotifierConfig":
        payload = raw if isinstance(raw, dict) else {}
        provider = str(payload.get("provider", "none")).strip().lower()
        if provider not in {"none", "discord", "telegram", "both"}:
            provider = "none"
        discord_linked = (
            str(payload.get("discord_linked_users_file", "")).strip() or
            defaults.default_discord_linked_users_file
        )
        telegram_linked = (
            str(payload.get("telegram_linked_users_file", "")).strip() or
            defaults.default_telegram_linked_users_file
        )
        return cls(
            provider=provider,
            discord_bot_token=str(payload.get("discord_bot_token", "")).strip(),
            discord_linked_users_file=to_universal_path(discord_linked),
            telegram_token=str(payload.get("telegram_token", "")).strip(),
            telegram_linked_users_file=to_universal_path(telegram_linked),
            notify_bot_lifecycle=bool(payload.get("notify_bot_lifecycle", True)),
        )


@dataclass
class GoogleSheetFormatConfig:
    font_size: str = ""
    font_family: str = "Arial"
    font_color: str = ""
    header_alignment: str = "center"
    apply_mode: str = "on_change"
    column_width_mode: str = "default"
    column_width_value: int = 120
    column_min_width: int = 100
    column_alignments: dict[str, dict[str, str]] | None = None

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None, defaults: ConfigDefaults) -> "GoogleSheetFormatConfig":
        payload = raw if isinstance(raw, dict) else {}
        try:
            width_value = int(payload.get("column_width_value", 120))
        except (TypeError, ValueError):
            width_value = 120
        try:
            min_width = int(payload.get("column_min_width", 100))
        except (TypeError, ValueError):
            min_width = 100
        alignments_raw = payload.get("column_alignments", {})
        alignments = alignments_raw if isinstance(alignments_raw, dict) else defaults.default_column_alignments
        return cls(
            font_size=str(payload.get("font_size", "")).strip(),
            font_family=str(payload.get("font_family", "Arial")).strip() or "Arial",
            font_color=str(payload.get("font_color", "")).strip(),
            header_alignment=str(payload.get("header_alignment", "center")).strip().lower() or "center",
            apply_mode=str(payload.get("apply_mode", "on_change")).strip().lower() or "on_change",
            column_width_mode=str(payload.get("column_width_mode", "default")).strip().lower() or "default",
            column_width_value=width_value,
            column_min_width=min_width,
            column_alignments=alignments,
        )


@dataclass
class AppConfig:
    selected_semester: str
    semesters: list[dict[str, Any]]
    schedules: list[dict[str, Any]]
    login: LoginConfig
    verify: VerifyConfig
    notifier: NotifierConfig
    google_sheet_format: GoogleSheetFormatConfig
    path_store_mode: dict[str, bool]

    @classmethod
    def from_dict(cls, raw: dict[str, Any] | None, defaults: ConfigDefaults) -> "AppConfig":
        payload = raw if isinstance(raw, dict) else {}
        login_payload = payload.get("login", {})
        verify_payload = payload.get("verify", {})
        if not isinstance(login_payload, dict):
            login_payload = {}
        if not isinstance(verify_payload, dict):
            verify_payload = {}
        # Legacy migration: login.model_path/login.captcha_server -> verify.*
        if ("model_path" in login_payload) and ("model_path" not in verify_payload):
            verify_payload["model_path"] = login_payload.get("model_path")
        if ("captcha_server" in login_payload) and ("captcha_server" not in verify_payload):
            verify_payload["captcha_server"] = login_payload.get("captcha_server")
        semesters = payload.get("semesters", [])
        schedules = payload.get("schedules", [])
        store_mode = payload.get("path_store_mode", {})
        if not isinstance(semesters, list):
            semesters = []
        if not isinstance(schedules, list):
            schedules = []
        if not isinstance(store_mode, dict):
            store_mode = {}
        normalized_store_mode = {
            "model_path": bool(store_mode.get("model_path", True)),
            "captcha_cert_file": bool(store_mode.get("captcha_cert_file", True)),
            "captcha_key_file": bool(store_mode.get("captcha_key_file", True)),
            "discord_linked_users_file": bool(store_mode.get("discord_linked_users_file", True)),
            "telegram_linked_users_file": bool(store_mode.get("telegram_linked_users_file", True)),
        }
        return cls(
            selected_semester=str(payload.get("selected_semester", "")).strip(),
            semesters=semesters,
            schedules=schedules,
            login=LoginConfig.from_dict(login_payload),
            verify=VerifyConfig.from_dict(verify_payload, defaults),
            notifier=NotifierConfig.from_dict(payload.get("notifier"), defaults),
            google_sheet_format=GoogleSheetFormatConfig.from_dict(payload.get("google_sheet_format"), defaults),
            path_store_mode=normalized_store_mode,
        )

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        if "path_picker_cache" in payload:
            payload.pop("path_picker_cache", None)
        return payload


def get_legacy_https_cert_candidates(base_dir: Path) -> tuple[set[str], set[str]]:
    """Return legacy cert/key path candidates for migration."""
    cert_candidates = {
        to_universal_path(base_dir / "CYUTScholarshipRadar" / "https_credentials" / "cert.pem"),
        to_universal_path(base_dir / "https_credentials" / "cert.pem"),
    }
    key_candidates = {
        to_universal_path(base_dir / "CYUTScholarshipRadar" / "https_credentials" / "key.pem"),
        to_universal_path(base_dir / "https_credentials" / "key.pem"),
    }
    return cert_candidates, key_candidates


def is_legacy_linked_users_value(config_key: str, value: str) -> bool:
    """Check whether a linked-users path value is from legacy layouts."""
    return str(value).strip() in LEGACY_LINKED_USERS_VALUES.get(config_key, set())
