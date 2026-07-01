from __future__ import annotations

import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Callable
from urllib.parse import parse_qs, urlparse


class CheckIpcServer:
    def __init__(
        self,
        host: str,
        port: int,
        token: str,
        enqueue_handler: Callable[[str, str], dict],
        status_handler: Callable[[str], dict],
    ) -> None:
        self._host = host
        self._port = port
        self._token = token
        self._enqueue_handler = enqueue_handler
        self._status_handler = status_handler
        self._server: ThreadingHTTPServer | None = None

    def start(self) -> int:
        return self.run_in_background()

    def run_in_background(self) -> int:
        import threading

        server = ThreadingHTTPServer((self._host, self._port), self._build_handler())
        server.daemon_threads = True
        self._server = server
        thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.2}, daemon=True)
        thread.start()
        return int(server.server_port)

    def stop(self) -> None:
        if self._server is None:
            return
        try:
            self._server.shutdown()
        except Exception:
            pass
        try:
            self._server.server_close()
        except Exception:
            pass
        self._server = None

    def _build_handler(self):
        token = self._token
        enqueue_handler = self._enqueue_handler
        status_handler = self._status_handler

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

            def _is_authorized(self) -> bool:
                return self.headers.get("X-CYUT-Token", "").strip() == token

            def do_POST(self) -> None:
                if not self._is_authorized():
                    self._send_json(403, {"success": False, "error": "unauthorized"})
                    return
                parsed = urlparse(self.path)
                if parsed.path != "/enqueue":
                    self._send_json(404, {"success": False, "error": "not_found"})
                    return

                try:
                    content_len = int(self.headers.get("Content-Length", "0"))
                except ValueError:
                    content_len = 0
                raw = self.rfile.read(max(content_len, 0))
                payload = {}
                if raw:
                    try:
                        payload = json.loads(raw.decode("utf-8"))
                    except Exception:
                        payload = {}
                semester = str(payload.get("semester", "")).strip()
                requester = str(payload.get("requester", "bot")).strip() or "bot"
                try:
                    result = enqueue_handler(semester, requester)
                    self._send_json(200, result)
                except Exception as exc:
                    self._send_json(500, {"success": False, "error": str(exc)})

            def do_GET(self) -> None:
                if not self._is_authorized():
                    self._send_json(403, {"success": False, "error": "unauthorized"})
                    return
                parsed = urlparse(self.path)
                if parsed.path != "/status":
                    self._send_json(404, {"success": False, "error": "not_found"})
                    return
                query = parse_qs(parsed.query, keep_blank_values=True)
                job_id = str((query.get("job_id") or [""])[0]).strip()
                if job_id == "":
                    self._send_json(400, {"success": False, "error": "missing_job_id"})
                    return
                try:
                    result = status_handler(job_id)
                    self._send_json(200, result)
                except Exception as exc:
                    self._send_json(500, {"success": False, "error": str(exc)})

        return _Handler
