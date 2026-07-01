from __future__ import annotations

import threading
from pathlib import Path

from utils.app_paths import to_universal_path

_MODEL_INSTANCE_LOCK = threading.Lock()
_MODEL_INFER_LOCK = threading.RLock()
_SHARED_MODEL = None
_SHARED_MODEL_PATH = ""


class VerifyModelPathError(Exception):
    """Raised when verify model path is invalid."""


def _normalize_model_path(model_path: str) -> str:
    """Normalize model path to absolute universal form."""
    return to_universal_path(Path(model_path).expanduser().resolve())


def get_shared_verify_model(model_path: str):
    """Get or create shared verify model instance by path."""
    global _SHARED_MODEL
    global _SHARED_MODEL_PATH
    normalized_path = _normalize_model_path(model_path)
    if not Path(normalized_path).is_file():
        raise VerifyModelPathError(f"驗證碼模型檔案不存在：{normalized_path}")
    with _MODEL_INSTANCE_LOCK:
        if (_SHARED_MODEL is None) or (_SHARED_MODEL_PATH != normalized_path):
            from collageLogin.CYUTLoginVerifyModel import CYUTLoginVerifyModel

            _SHARED_MODEL = CYUTLoginVerifyModel(normalized_path)
            _SHARED_MODEL_PATH = normalized_path
        return _SHARED_MODEL


def get_shared_verify_model_lock() -> threading.RLock:
    """Get shared inference lock for verify model calls."""
    return _MODEL_INFER_LOCK


def get_shared_verify_model_path() -> str:
    """Return current shared model path."""
    return _SHARED_MODEL_PATH
