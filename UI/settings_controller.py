from __future__ import annotations

import os
import sys
from pathlib import Path

from utils.app_paths import to_universal_path


class SettingsController:
    """Path/default resolver for settings related UI fields."""

    def __init__(self, runtime_base_dir: Path, application_dir: Path, script_path: Path) -> None:
        self.runtime_base_dir = runtime_base_dir.resolve()
        self.application_dir = application_dir.resolve()
        self.script_path = script_path.resolve()

    def default_path_store_mode(self) -> dict[str, bool]:
        return {
            "model_path": True,
            "captcha_cert_file": True,
            "captcha_key_file": True,
            "discord_linked_users_file": True,
            "telegram_linked_users_file": True,
        }

    def normalize_path_text(self, path_text: str) -> str:
        return to_universal_path(path_text.strip())

    def normalize_to_absolute_path_text(self, path_text: str) -> str:
        raw = str(path_text).strip()
        if raw == "":
            return ""
        normalized = self.normalize_path_text(raw)
        path_obj = Path(normalized).expanduser()
        if not path_obj.is_absolute():
            path_obj = self.runtime_base_dir / path_obj
        return to_universal_path(path_obj.resolve())

    def resolve_display_path(self, stored_path: str, fallback_abs_path: str) -> str:
        raw = str(stored_path).strip()
        if raw == "":
            return to_universal_path(Path(fallback_abs_path).expanduser().resolve())
        normalized = self.normalize_path_text(raw)
        path_obj = Path(normalized).expanduser()
        if path_obj.is_absolute():
            return to_universal_path(path_obj.resolve())
        return to_universal_path((self.runtime_base_dir / path_obj).resolve())

    def to_storage_path(self, abs_path: str, use_relative: bool) -> str:
        abs_normalized = to_universal_path(Path(abs_path).expanduser().resolve())
        if not use_relative:
            return abs_normalized
        runtime_root = self.runtime_base_dir
        try:
            relative = Path(abs_normalized).resolve().relative_to(runtime_root)
            return to_universal_path(relative)
        except Exception:
            try:
                return to_universal_path(os.path.relpath(abs_normalized, start=runtime_root))
            except Exception:
                return abs_normalized

    def get_default_picker_start_dir(self) -> str:
        if getattr(sys, "frozen", False):
            return to_universal_path(Path(sys.executable).resolve().parent)
        return to_universal_path(self.script_path.parent)

    def resolve_picker_start_dir(self, path_text: str) -> str:
        default_dir = Path(self.get_default_picker_start_dir())
        raw = str(path_text).strip()
        if raw == "":
            return to_universal_path(default_dir)
        abs_path = self.normalize_to_absolute_path_text(raw)
        candidate = Path(abs_path)
        if candidate.suffix != "":
            candidate = candidate.parent
        while True:
            if candidate.exists() and candidate.is_dir():
                return to_universal_path(candidate.resolve())
            parent = candidate.parent
            if parent == candidate:
                return to_universal_path(default_dir)
            candidate = parent

    def normalize_captcha_server_path(self, path_text: str) -> str:
        text = str(path_text or "").strip()
        if text == "":
            return "/solve_captcha"
        if not text.startswith("/"):
            text = f"/{text}"
        return text

    def get_default_linked_users_file(self, provider: str) -> str:
        provider_name = provider.strip().lower()
        if provider_name not in {"discord", "telegram"}:
            provider_name = "discord"
        return to_universal_path(self.application_dir / "subscriptions" / f"{provider_name}_linked_users.json")

    def normalize_linked_users_path_for_save(self, provider: str, raw_path: str) -> str:
        fallback = self.get_default_linked_users_file(provider)
        selected = raw_path.strip() or fallback
        normalized = self.normalize_to_absolute_path_text(selected)
        path_obj = Path(normalized)
        is_dir_like = (
            normalized.endswith("/") or
            normalized.endswith("\\") or
            (path_obj.exists() and path_obj.is_dir()) or
            path_obj.suffix == ""
        )
        if is_dir_like:
            path_obj = path_obj / f"{provider.lower()}_linked_users.json"
        return to_universal_path(path_obj)

    def ensure_linked_users_file_exists(self, file_path: str) -> None:
        path_obj = Path(file_path)
        path_obj.parent.mkdir(parents=True, exist_ok=True)
        if path_obj.exists():
            return
        with path_obj.open("w", encoding="utf-8") as file:
            file.write("{}")

    def get_default_model_path(self) -> str:
        model_name = "YOLO11x-google-best.pt"
        candidates: list[Path] = []
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).resolve().parent
            mei_root = getattr(sys, "_MEIPASS", "")
            if mei_root:
                candidates.append(Path(str(mei_root)).resolve() / "model" / model_name)
            candidates.append(exe_dir / "_internal" / "model" / model_name)
            candidates.append(exe_dir / "model" / model_name)
        else:
            script_dir = self.script_path.parent
            candidates.append(script_dir / "CYUTScholarshipRadar" / "model" / model_name)
            candidates.append(self.script_path.parents[1] / "model" / model_name)
        for path in candidates:
            if path.is_file():
                return to_universal_path(path)
        return to_universal_path(candidates[0])

    def get_default_https_cert_dir(self) -> str:
        return to_universal_path(self.application_dir / "https_credentials")

    def get_default_https_cert_file(self) -> str:
        return to_universal_path(Path(self.get_default_https_cert_dir()) / "cert.pem")

    def get_default_https_key_file(self) -> str:
        return to_universal_path(Path(self.get_default_https_cert_dir()) / "key.pem")
