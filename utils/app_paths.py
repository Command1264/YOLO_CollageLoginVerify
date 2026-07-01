import os
import sys
from pathlib import Path


APP_FOLDER_NAME = "CYUTScholarshipRadar"


def get_runtime_base_dir() -> Path:
    override = os.getenv("CYUT_APP_BASE_DIR", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    argv0 = (sys.argv[0] or "").strip()
    if argv0:
        try:
            return Path(argv0).resolve().parent
        except Exception:
            pass
    return Path.cwd().resolve()


def get_app_data_dir(base_dir: Path | None = None) -> Path:
    runtime_base = base_dir if base_dir is not None else get_runtime_base_dir()
    return runtime_base / APP_FOLDER_NAME


def get_config_path(base_dir: Path | None = None) -> Path:
    return get_app_data_dir(base_dir) / "CYUTScholarshipRadarConfig.json"


def get_history_path(base_dir: Path | None = None) -> Path:
    return get_app_data_dir(base_dir) / "history.json"


def get_cache_dir(base_dir: Path | None = None) -> Path:
    return get_app_data_dir(base_dir) / ".cache"


def get_service_boot_state_path(base_dir: Path | None = None) -> Path:
    return get_app_data_dir(base_dir) / "service_boot_state.json"


def get_check_ipc_info_path(base_dir: Path | None = None) -> Path:
    return get_app_data_dir(base_dir) / "check_ipc_info.json"


def get_logs_dir(base_dir: Path | None = None) -> Path:
    return get_app_data_dir(base_dir) / "logs"


def get_bot_log_dir(bot_name: str, base_dir: Path | None = None) -> Path:
    return get_logs_dir(base_dir) / bot_name.lower().strip()


def get_subscriptions_dir(base_dir: Path | None = None) -> Path:
    return get_app_data_dir(base_dir) / "subscriptions"


def get_linked_users_path(platform: str, base_dir: Path | None = None) -> Path:
    safe_platform = platform.lower().strip()
    return get_subscriptions_dir(base_dir) / f"{safe_platform}_linked_users.json"


def get_cookies_path(base_dir: Path | None = None) -> Path:
    return get_app_data_dir(base_dir) / "cyutLoginCookies.json"


def get_oauth_credentials_path(base_dir: Path | None = None) -> Path:
    return get_app_data_dir(base_dir) / "OAuthCredentials.json"


def get_token_path(base_dir: Path | None = None) -> Path:
    return get_app_data_dir(base_dir) / "token.json"


def to_universal_path(path: Path | str) -> str:
    return str(path).replace("\\", "/")
