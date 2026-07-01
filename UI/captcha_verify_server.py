from __future__ import annotations

import base64
import json
import ssl
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable, Protocol

import cv2 as cv
import numpy as np

from utils.verify_model_provider import get_shared_verify_model, get_shared_verify_model_lock


class VerifyModelProtocol(Protocol):
    def get_verify_code(self, *args, **kwargs) -> str | None:
        ...


class CaptchaVerifyServer:
    """Lightweight HTTP server for captcha recognition."""

    def __init__(self) -> None:
        self._server: ThreadingHTTPServer | None = None
        self._thread: threading.Thread | None = None
        self._host = ""
        self._port = 0
        self._scheme = "http"
        self._solve_path = "/solve_captcha"
        self._model_path = ""
        self._cert_file = ""
        self._key_file = ""
        self._model_lock = threading.Lock()
        self._model: VerifyModelProtocol | None = None
        self._infer_lock = get_shared_verify_model_lock()
        self._img_size = [640, 640]

    @property
    def is_running(self) -> bool:
        return self._server is not None

    @property
    def bound_host(self) -> str:
        return self._host

    @property
    def bound_port(self) -> int:
        return self._port

    @property
    def bound_scheme(self) -> str:
        return self._scheme

    def start(
        self,
        host: str,
        port: int,
        solve_path: str,
        model_path: str,
        protocol: str = "http",
        cert_file: str = "",
        key_file: str = "",
    ) -> tuple[bool, str]:
        if self._server is not None:
            return True, f"伺服器已在執行中（{self._host}:{self._port}）"

        normalized_path = self._normalize_solve_path(solve_path)
        normalized_protocol = str(protocol or "http").strip().lower()
        if normalized_protocol not in {"http", "https"}:
            normalized_protocol = "http"
        resolved_model_path = str(Path(model_path).expanduser().resolve())
        if not Path(resolved_model_path).is_file():
            return False, f"模型檔案不存在：{resolved_model_path}"
        resolved_cert_file = ""
        resolved_key_file = ""
        if normalized_protocol == "https":
            resolved_cert_file = str(Path(cert_file).expanduser().resolve())
            resolved_key_file = str(Path(key_file).expanduser().resolve())
            if not Path(resolved_cert_file).is_file():
                return False, f"HTTPS 憑證檔不存在：{resolved_cert_file}"
            if not Path(resolved_key_file).is_file():
                return False, f"HTTPS 私鑰檔不存在：{resolved_key_file}"

        try:
            server = ThreadingHTTPServer((host, int(port)), self._build_handler())
            if normalized_protocol == "https":
                context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
                context.load_cert_chain(certfile=resolved_cert_file, keyfile=resolved_key_file)
                server.socket = context.wrap_socket(server.socket, server_side=True)
            server.daemon_threads = True
            self._host = host
            self._port = int(server.server_port)
            self._scheme = normalized_protocol
            self._solve_path = normalized_path
            self._model_path = resolved_model_path
            self._cert_file = resolved_cert_file
            self._key_file = resolved_key_file
            self._model = None
            self._server = server
            thread = threading.Thread(
                target=server.serve_forever,
                kwargs={"poll_interval": 0.2},
                daemon=True,
            )
            thread.start()
            self._thread = thread
            return True, f"伺服器已啟動：{self._scheme}://{self._host}:{self._port}{self._solve_path}"
        except Exception as exc:
            self._server = None
            self._thread = None
            return False, f"伺服器啟動失敗：{exc}"

    def stop(self) -> None:
        server = self._server
        if server is None:
            return
        try:
            server.shutdown()
        except Exception:
            pass
        try:
            server.server_close()
        except Exception:
            pass
        self._server = None
        self._thread = None
        self._host = ""
        self._port = 0
        self._scheme = "http"
        self._cert_file = ""
        self._key_file = ""
        self._model = None

    def _normalize_solve_path(self, value: str) -> str:
        text = str(value or "").strip()
        if text == "":
            return "/solve_captcha"
        if not text.startswith("/"):
            text = f"/{text}"
        return text

    def _get_model(self) -> "VerifyModelProtocol":
        with self._model_lock:
            if self._model is None:
                loaded_model = get_shared_verify_model(self._model_path)
                self._model = loaded_model
            if self._model is None:
                raise RuntimeError("驗證碼模型載入失敗")
            return self._model

    def _decode_image(self, image_text: str) -> np.ndarray:
        value = str(image_text).strip()
        if value == "":
            raise ValueError("image is empty")
        if "," in value:
            value = value.split(",", 1)[1]
        img_bytes = base64.b64decode(value)
        np_arr = np.frombuffer(img_bytes, np.uint8)
        img = cv.imdecode(np_arr, cv.IMREAD_COLOR)
        if img is None:
            raise ValueError("invalid image data")
        return img

    def _preprocess(self, img: np.ndarray) -> np.ndarray:
        half_img = img[:, : img.shape[1] // 2]
        size = half_img.shape[0:2]
        scale = min(self._img_size[0] / size[0], self._img_size[1] / size[1])
        new_size = [round(i * scale) for i in size]
        new_img = np.full((*self._img_size, 3), 255, dtype=np.uint8)
        draw_loc = [
            (0 if (self._img_size[i] == new_size[i]) else (self._img_size[i] // 2) - (new_size[i] // 2))
            for i in range(2)
        ]
        new_img[
            int(draw_loc[0]) : int(draw_loc[0] + new_size[0]),
            int(draw_loc[1]) : int(draw_loc[1] + new_size[1]),
        ] = cv.resize(half_img, (0, 0), fx=scale, fy=scale)
        return new_img

    def _build_handler(self):
        get_model = self._get_model
        solve_path_getter: Callable[[], str] = lambda: self._solve_path
        decode_image: Callable[[str], np.ndarray] = self._decode_image
        preprocess: Callable[[np.ndarray], np.ndarray] = self._preprocess
        infer_lock = self._infer_lock

        class _Handler(BaseHTTPRequestHandler):
            def log_message(self, format: str, *args) -> None:
                return

            def _send_json(self, status_code: int, payload: dict) -> None:
                raw = json.dumps(payload, ensure_ascii=False).encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def _send_text(self, status_code: int, text: str) -> None:
                raw = text.encode("utf-8")
                self.send_response(status_code)
                self.send_header("Content-Type", "text/plain; charset=utf-8")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def do_GET(self) -> None:
                if self.path == "/":
                    self._send_text(200, "驗證碼辨識伺服器運作中...")
                    return
                self._send_json(404, {"success": False, "error": "not_found"})

            def do_POST(self) -> None:
                if self.path != solve_path_getter():
                    self._send_json(404, {"success": False, "error": "not_found"})
                    return
                try:
                    content_length = int(self.headers.get("Content-Length", "0"))
                except ValueError:
                    content_length = 0
                raw = self.rfile.read(max(content_length, 0))
                try:
                    payload = json.loads(raw.decode("utf-8")) if raw else {}
                except Exception:
                    payload = {}
                image_text = str(payload.get("image", "")).strip()
                if image_text == "":
                    self._send_json(400, {"success": False, "error": "missing_image"})
                    return
                try:
                    source = preprocess(decode_image(image_text))
                    with infer_lock:
                        result = get_model().get_verify_code(
                            source=source,
                            log=True,
                            save=False,
                        )
                    if result:
                        self._send_json(200, {"success": True, "text": result})
                        return
                    self._send_json(422, {"success": False, "error": "no_result"})
                except Exception as exc:
                    self._send_json(500, {"success": False, "error": str(exc)})

        return _Handler
