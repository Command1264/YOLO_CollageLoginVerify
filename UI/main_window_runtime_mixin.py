from __future__ import annotations

from typing import Any

import logging
import sys
import uuid
from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QThread, QTimer
from PySide6.QtGui import QCloseEvent, QFontDatabase, QIcon, QPixmap
from PySide6.QtWidgets import QApplication, QMessageBox, QSystemTrayIcon

from UI.check_ipc_server import CheckIpcServer
from UI.captcha_verify_server import CaptchaVerifyServer
from UI.tray_controller import TrayController
from UI.async_workers import ServicePreloadWorker
from utils.app_paths import to_universal_path

class MainWindowRuntimeMixin:
    def _build_asset_search_dirs(self: Any) -> list[Path]:
        base_dirs: list[Path] = []
        seen: set[str] = set()

        def _add_dir(path_obj: Path | None) -> None:
            if path_obj is None:
                return
            try:
                resolved = path_obj.resolve()
            except Exception:
                return
            key = str(resolved).lower()
            if key in seen:
                return
            seen.add(key)
            base_dirs.append(resolved)

        _add_dir(Path.cwd())
        _add_dir(Path(__file__).resolve().parent)
        _add_dir(self.project_root / "UI")
        _add_dir(self.runtime_base_dir)
        if getattr(sys, "frozen", False):
            _add_dir(Path(sys.executable).resolve().parent)
            _add_dir(Path(sys.executable).resolve().parent / "_internal")
            meipass = getattr(sys, "_MEIPASS", None)
            if isinstance(meipass, str) and meipass.strip() != "":
                _add_dir(Path(meipass))
        return base_dirs

    def _setup_check_ipc_timer(self: Any) -> None:
        self.check_ipc_timer = QTimer(self)
        self.check_ipc_timer.setInterval(500)
        self.check_ipc_timer.timeout.connect(self._drain_check_ipc_inbox)
        self.check_ipc_timer.start()

    def _start_check_ipc_server(self: Any) -> None:
        if self.check_ipc_server is not None:
            return
        self.check_ipc_token = uuid.uuid4().hex
        server = CheckIpcServer(
            host=self.check_ipc_host,
            port=0,
            token=self.check_ipc_token,
            enqueue_handler=self._enqueue_check_job_from_ipc,
            status_handler=self._get_check_job_status_from_ipc,
        )
        try:
            self.check_ipc_port = server.run_in_background()
            self.check_ipc_server = server
            payload = {
                "host": self.check_ipc_host,
                "port": self.check_ipc_port,
                "token": self.check_ipc_token,
                "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            }
            self._write_json(self.check_ipc_info_path, payload)
        except Exception as exc:
            self.check_ipc_server = None
            self.check_ipc_port = 0
            self.check_ipc_token = ""
            self.statusBar().showMessage(f"檢查 IPC 啟動失敗: {exc}", 8000)

    def _stop_check_ipc_server(self: Any) -> None:
        if hasattr(self, "check_ipc_timer"):
            try:
                self.check_ipc_timer.stop()
            except Exception:
                pass
        if self.check_ipc_server is not None:
            try:
                self.check_ipc_server.stop()
            except Exception:
                pass
        self.check_ipc_server = None
        self.check_ipc_port = 0
        self.check_ipc_token = ""
        try:
            if self.check_ipc_info_path.exists():
                self.check_ipc_info_path.unlink()
        except Exception:
            pass

    def _current_captcha_server_config(self: Any) -> dict:
        self._normalize_captcha_server_path_in_widget()
        protocol = str(self.captcha_server_protocol.currentData() or "http").strip().lower()
        cert_file = self._normalize_path_text(
            self.captcha_server_cert_file.text().strip() or self._get_default_https_cert_file()
        )
        key_file = self._normalize_path_text(
            self.captcha_server_key_file.text().strip() or self._get_default_https_key_file()
        )
        self.captcha_server_cert_file.setText(cert_file)
        self.captcha_server_key_file.setText(key_file)
        return {
            "enabled": self.captcha_server_enabled.isChecked(),
            "protocol": protocol if protocol in {"http", "https"} else "http",
            "host": self.captcha_server_host.text().strip() or "127.0.0.1",
            "port": int(self.captcha_server_port.value()),
            "path": self._normalize_captcha_server_path(self.captcha_server_path.text()),
            "cert_file": cert_file,
            "key_file": key_file,
        }

    def _on_captcha_server_protocol_changed(self: Any) -> None:
        protocol = str(self.captcha_server_protocol.currentData() or "http").strip().lower()
        https_enabled = protocol == "https"
        self.captcha_server_cert_file.setEnabled(https_enabled)
        self.captcha_server_cert_browse_btn.setEnabled(https_enabled)
        self.captcha_server_key_file.setEnabled(https_enabled)
        self.captcha_server_key_browse_btn.setEnabled(https_enabled)

    def _refresh_captcha_server_status_label(self: Any) -> None:
        if not hasattr(self, "captcha_server_status"):
            return
        if self.captcha_server.is_running:
            scheme = self.captcha_server.bound_scheme
            host = self.captcha_server.bound_host
            port = self.captcha_server.bound_port
            self.captcha_server_status.setText(f"執行中：{scheme}://{host}:{port}/")
            self.captcha_server_start_btn.setEnabled(False)
            self.captcha_server_stop_btn.setEnabled(True)
            return
        self.captcha_server_status.setText("未啟動")
        self.captcha_server_start_btn.setEnabled(True)
        self.captcha_server_stop_btn.setEnabled(False)

    def _start_captcha_server_with_config(self: Any, cfg: dict, model_path_override: str | None = None) -> tuple[bool, str]:
        verify_cfg = self.config.get("verify", {})
        model_path = self._resolve_display_path(
            str(model_path_override if model_path_override is not None else verify_cfg.get("model_path", "")).strip(),
            self._get_default_model_path(),
        )
        protocol = str(cfg.get("protocol", "http")).strip().lower()
        if protocol not in {"http", "https"}:
            protocol = "http"
        host = str(cfg.get("host", "127.0.0.1")).strip() or "127.0.0.1"
        port = int(cfg.get("port", 5000))
        path = self._normalize_captcha_server_path(str(cfg.get("path", "/solve_captcha")))
        cert_file = self._resolve_display_path(
            str(cfg.get("cert_file", "")).strip(),
            self._get_default_https_cert_file(),
        )
        key_file = self._resolve_display_path(
            str(cfg.get("key_file", "")).strip(),
            self._get_default_https_key_file(),
        )
        ok, message = self.captcha_server.start(
            host=host,
            port=port,
            solve_path=path,
            model_path=model_path,
            protocol=protocol,
            cert_file=cert_file,
            key_file=key_file,
        )
        self._refresh_captcha_server_status_label()
        return ok, message

    def _start_captcha_server_from_widgets(self: Any) -> None:
        cfg = self._current_captcha_server_config()
        model_path = self.login_model_path.text().strip() or self._get_default_model_path()
        model_path = self._normalize_path_text(model_path)
        self.login_model_path.setText(model_path)
        ok, message = self._start_captcha_server_with_config(cfg, model_path_override=model_path)
        if ok:
            self.statusBar().showMessage(message, 5000)
        else:
            QMessageBox.warning(self, "驗證碼伺服器", message)

    def _stop_captcha_server_from_widgets(self: Any) -> None:
        self.captcha_server.stop()
        self._refresh_captcha_server_status_label()
        self.statusBar().showMessage("驗證碼辨識伺服器已停止", 5000)

    def _sync_captcha_server_from_config(self: Any) -> None:
        verify_cfg = self.config.get("verify", {})
        captcha_cfg = verify_cfg.get("captcha_server", {})
        if not isinstance(captcha_cfg, dict):
            self._refresh_captcha_server_status_label()
            return
        enabled = bool(captcha_cfg.get("enabled", False))
        if enabled:
            if self.captcha_server.is_running:
                self.captcha_server.stop()
            ok, message = self._start_captcha_server_with_config(captcha_cfg)
            if ok:
                self.statusBar().showMessage(message, 5000)
            else:
                self.statusBar().showMessage(message, 8000)
        else:
            self.captcha_server.stop()
            self._refresh_captcha_server_status_label()

    def _enqueue_check_job_from_ipc(self: Any, semester: str, requester: str) -> dict:
        return self.check_queue_coordinator.enqueue_external_job(
            semester=semester,
            requester=requester,
            service_boot_ready=self.service_boot_ready,
            check_running=self.check_flow_controller.is_running(),
            pending_count=self.check_flow_controller.pending_count(),
        )

    def _get_check_job_status_from_ipc(self: Any, job_id: str) -> dict:
        return self.check_queue_coordinator.get_job_status(job_id)

    def _drain_check_ipc_inbox(self: Any) -> None:
        incoming = self.check_queue_coordinator.drain_ipc_inbox()
        if len(incoming) == 0:
            return
        for entry in incoming:
            self.check_flow_controller.enqueue(entry)
        self._update_check_ipc_queue_ahead()
        self._drain_pending_check_queue()

    def _update_check_ipc_queue_ahead(self: Any) -> None:
        self.check_queue_coordinator.update_queue_ahead(
            pending_check_queue=self.check_flow_controller.pending_entries(),
            check_running=self.check_flow_controller.is_running(),
        )

    def _create_tray_icon(self: Any) -> None:
        self.tray_icon = self.tray_controller.create_tray_icon(
            owner=self,
            icon=self._resolve_tray_icon(),
            on_show_window=self._show_window,
            on_run_check=self._check_now,
            on_quit=self._quit_app,
            on_activated=self._tray_activated,
        )

    def _resolve_tray_icon(self: Any):
        return self.tray_controller.resolve_tray_icon(
            owner=self,
            app_icon=self._load_app_icon(),
            window_icon=self.windowIcon(),
        )

    def _resolve_app_icon_path(self: Any) -> Path | None:
        base_dirs = self._build_asset_search_dirs()
        preferred_ext = "ico" if sys.platform.startswith("win") else "png"
        fallback_ext = "png" if preferred_ext == "ico" else "ico"
        for ext in [preferred_ext, fallback_ext]:
            for base_dir in base_dirs:
                path = base_dir / f"CYUTScholarshipRadarLogo.{ext}"
                if path.exists():
                    return path
        return None

    def _resolve_logo_path(self: Any) -> Path | None:
        candidates: list[Path] = []
        for base_dir in self._build_asset_search_dirs():
            candidates.append(base_dir / "CYUTScholarshipRadarLogo.png")
            candidates.append(base_dir / "CYUTScholarshipRadarLogo.ico")
        for path in candidates:
            if path.exists():
                return path
        return None

    def _load_logo_pixmap(self: Any) -> QPixmap | None:
        if self.logo_path is None:
            return None
        pixmap = QPixmap(str(self.logo_path))
        if pixmap.isNull():
            return None
        return pixmap

    def _apply_window_icon(self: Any) -> None:
        app_icon = self._load_app_icon()
        if app_icon is None:
            return
        self.setWindowIcon(app_icon)

    def _load_app_icon(self: Any) -> QIcon | None:
        if self.app_icon_path is not None and self.app_icon_path.exists():
            icon = QIcon(str(self.app_icon_path))
            if not icon.isNull():
                return icon
        if getattr(sys, "frozen", False) and sys.platform.startswith("win"):
            exe_icon = QIcon(str(Path(sys.executable).resolve()))
            if not exe_icon.isNull():
                return exe_icon
        return None

    def _tray_activated(self: Any, reason: QSystemTrayIcon.ActivationReason) -> None:
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_window()

    def _show_window(self: Any) -> None:
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def _quit_app(self: Any) -> None:
        self.window_close_controller.quit_app(
            set_force_exit=lambda: setattr(self, "force_exit", True),
            stop_captcha_server=self.captcha_server.stop,
            stop_check_ipc_server=self._stop_check_ipc_server,
            stop_all_bots=self._stop_all_bots,
            release_instance_lock=lambda: self._instance_lock.release() if self._instance_lock is not None else None,
            hide_tray_icon=self.tray_controller.hide_tray_icon,
            quit_application=self._quit_qapplication,
        )

    def _quit_qapplication(self: Any) -> None:
        app = QApplication.instance()
        if app is not None:
            app.quit()
