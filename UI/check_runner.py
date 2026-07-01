from dataclasses import asdict
import json
from datetime import datetime, timedelta
from pathlib import Path
import os
import sys
from typing import Callable
from urllib import request, parse

from utils.app_paths import get_runtime_base_dir, get_service_boot_state_path, get_check_ipc_info_path

_DEFAULT_LOADING_STATE = {
    "status": "loading",
    "progress": 0,
    "message": "啟動中",
}
_STATE_STALE_SECONDS = 180
_IPC_TIMEOUT_SECONDS = 4.0


def _build_state_path_candidates() -> list[Path]:
    candidates: list[Path] = []
    base_dirs: list[Path] = []
    seen_base_dirs: set[str] = set()

    def append_base_dir(path: Path | None) -> None:
        if path is None:
            return
        try:
            resolved = path.expanduser().resolve()
        except Exception:
            return
        key = str(resolved).lower()
        if key in seen_base_dirs:
            return
        seen_base_dirs.add(key)
        base_dirs.append(resolved)

    env_base_dir = os.getenv("CYUT_APP_BASE_DIR", "").strip()
    if env_base_dir:
        append_base_dir(Path(env_base_dir))

    append_base_dir(get_runtime_base_dir())
    append_base_dir(Path.cwd())

    try:
        append_base_dir(Path(sys.executable).resolve().parent)
    except Exception:
        pass

    argv0 = (sys.argv[0] or "").strip()
    if argv0:
        try:
            append_base_dir(Path(argv0).resolve().parent)
        except Exception:
            pass

    module_dir = Path(__file__).resolve().parent
    append_base_dir(module_dir)
    append_base_dir(module_dir.parent)

    seen_paths: set[str] = set()
    for base_dir in base_dirs:
        for candidate in (
            get_service_boot_state_path(base_dir),
            base_dir / "service_boot_state.json",
        ):
            key = str(candidate).lower()
            if key in seen_paths:
                continue
            seen_paths.add(key)
            candidates.append(candidate)
    return candidates


def _resolve_latest_boot_state_path() -> Path | None:
    latest_path: Path | None = None
    latest_mtime: float = -1.0
    for candidate in _build_state_path_candidates():
        try:
            if not candidate.exists():
                continue
            mtime = candidate.stat().st_mtime
            if mtime > latest_mtime:
                latest_mtime = mtime
                latest_path = candidate
        except Exception:
            continue
    return latest_path


def _parse_updated_at(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    text = value.strip()
    if not text:
        return None
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y/%m/%d %H:%M:%S"):
        try:
            return datetime.strptime(text, fmt)
        except ValueError:
            continue
    return None


def _is_state_stale(updated_at: datetime | None) -> bool:
    if updated_at is None:
        return True
    return updated_at < (datetime.now() - timedelta(seconds=_STATE_STALE_SECONDS))


def _read_check_ipc_info() -> dict:
    info_path = get_check_ipc_info_path(get_runtime_base_dir())
    if not info_path.exists():
        return {}
    try:
        with info_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _build_check_ipc_base_url(info: dict) -> tuple[str, str]:
    host = str(info.get("host", "")).strip()
    port = int(info.get("port", 0))
    token = str(info.get("token", "")).strip()
    if host == "" or token == "" or port <= 0:
        return "", ""
    return f"http://{host}:{port}", token


def _call_check_ipc_api(method: str, path: str, payload: dict | None = None) -> dict:
    info = _read_check_ipc_info()
    base_url, token = _build_check_ipc_base_url(info)
    if base_url == "" or token == "":
        return {"success": False, "error": "main_not_running"}

    body: bytes | None = None
    headers = {
        "X-CYUT-Token": token,
        "Accept": "application/json",
    }
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"

    req = request.Request(
        url=f"{base_url}{path}",
        data=body,
        method=method.upper(),
        headers=headers,
    )
    try:
        with request.urlopen(req, timeout=_IPC_TIMEOUT_SECONDS) as response:
            raw = response.read()
        data = json.loads(raw.decode("utf-8")) if raw else {}
        if isinstance(data, dict):
            return data
        return {"success": False, "error": "invalid_response"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def enqueue_main_check_job(semester_value: str | None = None, requester: str = "bot") -> dict:
    semester = (semester_value or "").strip()
    payload = {
        "semester": semester,
        "requester": requester,
    }
    return _call_check_ipc_api("POST", "/enqueue", payload)


def get_main_check_job_status(job_id: str) -> dict:
    safe_job_id = job_id.strip()
    if safe_job_id == "":
        return {"success": False, "error": "missing_job_id"}
    query = parse.urlencode({"job_id": safe_job_id})
    return _call_check_ipc_api("GET", f"/status?{query}", None)


def run_check_once(
    semester_value: str | None = None,
    google_sheet_format: dict | None = None,
    progress_callback: Callable[[int, str], None] | None = None,
) -> dict:
    """Run scholarship check flow once and return bot-friendly summary payload."""
    try:
        from UI.scholarship_service import ScholarshipService

        service = ScholarshipService()
        results = service.check_updates(
            semester_value=semester_value,
            progress_callback=progress_callback,
            google_sheet_format=google_sheet_format or {},
        )

        has_updates = False
        lines: list[str] = []
        for item in results:
            status_text = "成功" if item.success else "失敗"
            if item.summary is not None:
                delta_text = f"新增 {item.summary.added} / 刪除 {item.summary.removed}"
                if item.success and (item.summary.added > 0 or item.summary.removed > 0):
                    has_updates = True
            else:
                delta_text = "無差異資料"
            lines.append(f"[{status_text}] {item.name}: {item.message} ({delta_text})")

        return {
            "success": True,
            "has_updates": has_updates,
            "lines": lines,
            "results": [asdict(item) for item in results],
        }
    except Exception as exc:
        return {
            "success": False,
            "has_updates": False,
            "lines": [f"執行失敗: {exc}"],
            "results": [],
        }


def read_service_boot_state() -> dict:
    """Read shared ScholarshipService boot state."""
    state_path = _resolve_latest_boot_state_path()
    if state_path is None:
        return {**_DEFAULT_LOADING_STATE, "is_stale": True, "state_path": ""}
    try:
        with state_path.open("r", encoding="utf-8") as file:
            raw = json.load(file)
        if not isinstance(raw, dict):
            return {
                **_DEFAULT_LOADING_STATE,
                "is_stale": True,
                "state_path": str(state_path),
            }
        updated_at = _parse_updated_at(raw.get("updated_at"))
        is_stale = _is_state_stale(updated_at)
        return {
            "status": str(raw.get("status", "loading")).strip() or "loading",
            "progress": int(raw.get("progress", 0)),
            "message": str(raw.get("message", "啟動中")),
            "updated_at": raw.get("updated_at", ""),
            "is_stale": is_stale,
            "state_path": str(state_path),
        }
    except Exception:
        return {
            **_DEFAULT_LOADING_STATE,
            "is_stale": True,
            "state_path": str(state_path),
        }
