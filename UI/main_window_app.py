import json
import logging
import os
import argparse
import atexit
import functools
import importlib
import signal
import shutil
import socket
import subprocess
import sys
import threading
import uuid
from dataclasses import asdict
from datetime import datetime
from pathlib import Path

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from utils.app_paths import get_app_data_dir, get_runtime_base_dir
from UI.single_instance import (
    SingleInstanceFileLock,
    prepare_single_instance_lock,
    should_enable_single_instance_lock,
)


_INSTANCE_LOCK: SingleInstanceFileLock | None = None
if should_enable_single_instance_lock(sys.argv[1:]):
    _INSTANCE_LOCK = prepare_single_instance_lock()
    atexit.register(_INSTANCE_LOCK.release)

from PySide6.QtCore import QEvent, QObject, QPointF, QThread, QTime, QTimer, Qt, Signal
from PySide6.QtGui import QCloseEvent, QFont, QFontDatabase, QIcon, QPixmap, QWheelEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QDialog,
    QFileDialog,
    QFrame,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QSplitter,
    QSpinBox,
    QSystemTrayIcon,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QTextEdit,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)

from utils.app_paths import (
    get_bot_log_dir,
    get_check_ipc_info_path,
    get_history_path,
    get_config_path,
    get_service_boot_state_path,
    to_universal_path,
)
from utils.app_logger import redirect_std_streams_to_logger, setup_application_logging
from UI.check_ipc_server import CheckIpcServer
from UI.check_flow_controller import CheckFlowController
from UI.check_queue_coordinator import CheckQueueCoordinator
from UI.check_result_processor import CheckResultProcessor
from UI.dashboard_schedule_tabs_builder import DashboardScheduleTabsBuilder
from UI.google_sheet_format_controller import GoogleSheetFormatController
from UI.google_sheet_alignment_ui_controller import GoogleSheetAlignmentUiController
from UI.async_workers import CheckWorker, NotifyWorker, SemesterWorker, ServicePreloadWorker
from UI.bot_process_controller import BotProcessController
from UI.captcha_verify_server import CaptchaVerifyServer
from UI.config_schema import (
    AppConfig,
    ConfigDefaults,
    get_legacy_https_cert_candidates,
    is_legacy_linked_users_value,
)
from UI.history_store import HistoryStore
from UI.log_tabs_builder import LogTabsBuilder
from UI.notifier import NotificationConfig, Notifier
from UI.qt_worker_runner import QtWorkerRunner
from UI.schedule_controller import ScheduleController, ScheduleItem
from UI.settings_controller import SettingsController
from UI.settings_basic_sections_builder import SettingsBasicSectionsBuilder
from UI.settings_save_service import SettingsSaveService
from UI.settings_sheet_format_section_builder import SettingsSheetFormatSectionBuilder
from UI.tray_controller import TrayController
from UI.weekday_select_dialog import WeekdaySelectDialog
from UI.window_close_controller import WindowCloseController
from UI.main_window_runtime_mixin import MainWindowRuntimeMixin
from UI.main_window_settings_path_mixin import MainWindowSettingsPathMixin
from UI.main_window_settings_sheet_format_mixin import MainWindowSettingsSheetFormatMixin
from UI.main_window_settings_mixin import MainWindowSettingsMixin
from UI.main_window_schedule_check_mixin import MainWindowScheduleCheckMixin
from UI.main_window_notify_bot_mixin import MainWindowNotifyBotMixin

_SCHOLARSHIP_SERVICE_CLASS = None


def get_scholarship_service_class():
    global _SCHOLARSHIP_SERVICE_CLASS
    if _SCHOLARSHIP_SERVICE_CLASS is None:
        module = importlib.import_module("UI.scholarship_service")
        _SCHOLARSHIP_SERVICE_CLASS = getattr(module, "ScholarshipService")
    return _SCHOLARSHIP_SERVICE_CLASS


class QtSignalLogEmitter(QObject):
    log_line = Signal(str)


class QtSignalLogHandler(logging.Handler):
    def __init__(self, emitter: QtSignalLogEmitter) -> None:
        super().__init__()
        self.emitter = emitter

    def emit(self, record: logging.LogRecord) -> None:
        try:
            message = self.format(record)
        except Exception:
            message = str(record.msg)
        self.emitter.log_line.emit(message)


class NoWheelEventFilter(QObject):
    def eventFilter(self, watched: QObject, event: QEvent) -> bool:
        if event.type() == QEvent.Type.Wheel:
            app = self.parent()
            if (
                isinstance(app, ScholarshipApp)
                and isinstance(watched, QWidget)
                and isinstance(event, QWheelEvent)
            ):
                app._forward_settings_wheel_event(watched, event)
            return True
        return super().eventFilter(watched, event)


class ScholarshipApp(
    QMainWindow,
    MainWindowRuntimeMixin,
    MainWindowSettingsPathMixin,
    MainWindowSettingsSheetFormatMixin,
    MainWindowSettingsMixin,
    MainWindowScheduleCheckMixin,
    MainWindowNotifyBotMixin,
):
    check_now_btn: QPushButton
    provider_combo: QComboBox
    app_log_view: QPlainTextEdit
    app_log_wrap_checkbox: QCheckBox
    captcha_server_protocol: QComboBox
    captcha_server_cert_file: QLineEdit
    captcha_server_key_file: QLineEdit
    captcha_server_enabled: QCheckBox
    captcha_server_host: QLineEdit
    captcha_server_port: QSpinBox
    captcha_server_path: QLineEdit
    captcha_server_cert_browse_btn: QPushButton
    captcha_server_key_browse_btn: QPushButton
    captcha_server_status: QLabel
    captcha_server_start_btn: QPushButton
    captcha_server_stop_btn: QPushButton
    login_model_path: QLineEdit
    login_model_store_relative: QCheckBox
    discord_linked_users_file: QLineEdit
    telegram_linked_users_file: QLineEdit
    discord_linked_users_store_relative: QCheckBox
    telegram_linked_users_store_relative: QCheckBox
    discord_bot_token: QLineEdit
    telegram_token: QLineEdit
    notify_lifecycle_checkbox: QCheckBox
    login_account: QLineEdit
    login_password: QLineEdit
    password_toggle_btn: QPushButton
    semester_combo: QComboBox
    refresh_semester_btn: QPushButton
    check_progress_bar: QProgressBar
    check_progress_label: QLabel
    history_table: QTableWidget
    diff_view: QPlainTextEdit
    schedule_name: QLineEdit
    schedule_time: QTimeEdit
    schedule_semester: QComboBox
    weekday_display_label: QLabel
    schedule_table: QTableWidget
    selected_weekdays: list[int]
    discord_status_label: QLabel
    telegram_status_label: QLabel
    discord_wrap_checkbox: QCheckBox
    telegram_wrap_checkbox: QCheckBox
    discord_log_view: QPlainTextEdit
    telegram_log_view: QPlainTextEdit
    gs_align_dataset_combo: QComboBox
    gs_alignment_table: QTableWidget
    gs_font_size_combo: QComboBox
    gs_font_family_combo: QComboBox
    gs_font_color_combo: QComboBox
    gs_header_alignment_combo: QComboBox
    gs_apply_mode_combo: QComboBox
    gs_column_width_mode_combo: QComboBox
    gs_column_width_value_spin: QSpinBox
    gs_column_min_width_spin: QSpinBox
    gs_column_alignment_map: dict[str, dict[str, str]]
    gs_alignment_current_dataset: str
    captcha_server_cert_store_relative: QCheckBox
    captcha_server_key_store_relative: QCheckBox

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("朝陽獎助學金雷達")
        self.resize(1200, 760)
        self.setMinimumSize(960, 640)

        self.project_root = Path(__file__).resolve().parents[1]
        self.runtime_base_dir = get_runtime_base_dir()
        self.application_dir = get_app_data_dir(self.runtime_base_dir)
        self.app_logger, self.app_log_file = setup_application_logging(self.runtime_base_dir)
        self._stdout_proxy, self._stderr_proxy = redirect_std_streams_to_logger(self.app_logger)
        self.messaging_dir = self.project_root / "MessagingApp"
        self.app_icon_path = self._resolve_app_icon_path()
        self.logo_path = self._resolve_logo_path()

        self.config_path = get_config_path(self.runtime_base_dir)
        self.history_path = get_history_path(self.runtime_base_dir)
        self.history_store = HistoryStore(self.history_path, max_records=500)
        self.check_result_processor = CheckResultProcessor()
        self.gs_format_controller = GoogleSheetFormatController()
        self.gs_alignment_ui_controller = GoogleSheetAlignmentUiController()
        self.schedule_controller = ScheduleController()
        self.window_close_controller = WindowCloseController()
        self._instance_lock = _INSTANCE_LOCK
        self.settings_controller = SettingsController(
            runtime_base_dir=self.runtime_base_dir,
            application_dir=self.application_dir,
            script_path=Path(__file__),
        )
        self.settings_save_service = SettingsSaveService(self.settings_controller)
        self._migrate_legacy_files()
        self.config = self._load_config()
        self._normalize_config_paths()
        self._apply_runtime_env_from_config()
        self.force_exit = False
        self.tray_icon: QSystemTrayIcon | None = None
        self.tray_controller = TrayController()
        self.bot_controller = BotProcessController()
        self.bot_log_paths = {
            "discord": get_bot_log_dir("discord", self.runtime_base_dir),
            "telegram": get_bot_log_dir("telegram", self.runtime_base_dir),
        }
        self._notification_tasks: list[tuple[QThread, NotifyWorker]] = []
        self._notify_popup_flags: dict[str, bool] = {}
        self._last_log_snapshot = {"discord": "", "telegram": ""}
        self._bot_log_session_start: dict[str, float | None] = {"discord": None, "telegram": None}
        self._settings_scroll_area: QScrollArea | None = None
        self._settings_no_wheel_filter = NoWheelEventFilter(self)
        self.service_boot_ready = False
        self.service_boot_loading = False
        self.check_flow_controller = CheckFlowController()
        self.worker_runner = QtWorkerRunner(self)
        self.service_boot_state_path = get_service_boot_state_path(self.runtime_base_dir)
        self.check_ipc_info_path = get_check_ipc_info_path(self.runtime_base_dir)
        self.check_ipc_server: CheckIpcServer | None = None
        self.check_ipc_host = "127.0.0.1"
        self.check_ipc_port = 0
        self.check_ipc_token = ""
        self.check_queue_coordinator = CheckQueueCoordinator()
        self.captcha_server = CaptchaVerifyServer()

        self._build_ui()
        self.check_now_btn.setEnabled(False)
        self._setup_gui_application_log_handler()
        self._apply_window_icon()
        self._load_history_table()
        self._load_semester_to_combo()
        self._load_schedules_to_table()
        self._create_tray_icon()
        self._setup_scheduler()
        self._setup_bot_status_timer()
        self._start_check_ipc_server()
        self._setup_check_ipc_timer()
        QTimer.singleShot(0, self._sync_captcha_server_from_config)
        QTimer.singleShot(0, self._start_background_bots_on_launch)
        QTimer.singleShot(0, self._preload_scholarship_service_async)

    def _preload_scholarship_service_async(self) -> None:
        if self.service_boot_loading or self.service_boot_ready:
            return
        self.service_boot_loading = True
        self._write_service_boot_state("loading", 0, "ScholarshipService 啟動中")
        self.statusBar().showMessage("ScholarshipService 啟動中... 0%")
        worker = ServicePreloadWorker(preload_handler=get_scholarship_service_class)
        thread = QThread(self)
        worker.moveToThread(thread)
        thread.started.connect(worker.run)
        worker.progress.connect(self._on_service_preload_progress)
        worker.finished.connect(self._on_service_preload_finished)
        worker.failed.connect(self._on_service_preload_failed)
        worker.finished.connect(thread.quit)
        worker.failed.connect(thread.quit)
        thread.finished.connect(thread.deleteLater)
        thread.start()
        self._service_preload_thread = thread
        self._service_preload_worker = worker

    def _write_service_boot_state(self, status: str, progress: int, message: str) -> None:
        payload = {
            "status": status,
            "progress": max(0, min(100, int(progress))),
            "message": message,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        }
        self._write_json(self.service_boot_state_path, payload)

    def _on_service_preload_progress(self, value: int, message: str) -> None:
        progress = max(0, min(100, int(value)))
        self.statusBar().showMessage(f"ScholarshipService 啟動中... {progress}% | {message}")
        self._write_service_boot_state("loading", progress, message)

    def _on_service_preload_finished(self) -> None:
        self.service_boot_loading = False
        self.service_boot_ready = True
        self.check_now_btn.setEnabled(not self.check_flow_controller.is_running())
        self.statusBar().showMessage("ScholarshipService 已完成載入", 5000)
        self._write_service_boot_state("ready", 100, "ScholarshipService 已完成載入")
        self._update_check_ipc_queue_ahead()
        self._drain_pending_check_queue()

    def _on_service_preload_failed(self, message: str) -> None:
        self.service_boot_loading = False
        self.service_boot_ready = False
        self.check_now_btn.setEnabled(False)
        self.statusBar().showMessage("ScholarshipService 載入失敗", 8000)
        self._write_service_boot_state("failed", 0, message)
        QMessageBox.critical(self, "啟動失敗", f"ScholarshipService 載入失敗：{message}")

    def _build_ui(self) -> None:
        tabs = QTabWidget()
        self.setCentralWidget(tabs)

        tabs.addTab(self._build_dashboard_tab(), "主控台")
        tabs.addTab(self._build_schedule_tab(), "排程")
        tabs.addTab(self._build_settings_tab(), "設定")
        tabs.addTab(self._build_bot_log_tab(), "機器人日誌")
        tabs.addTab(self._build_application_log_tab(), "應用程式日誌")
        tabs.addTab(self._build_feature_tab(), "專案功能")
        self.statusBar().showMessage("就緒")

    def _build_dashboard_tab(self) -> QWidget:
        return DashboardScheduleTabsBuilder(self).build_dashboard_tab()

    def _build_schedule_tab(self) -> QWidget:
        return DashboardScheduleTabsBuilder(self).build_schedule_tab()

    def _build_settings_tab(self) -> QWidget:
        content = QWidget()
        layout = QVBoxLayout(content)
        basic_builder = SettingsBasicSectionsBuilder(self)
        basic_builder.build_login_section(layout)
        basic_builder.build_verify_section(layout)
        basic_builder.build_notify_section(layout)

        sheet_format_box = SettingsSheetFormatSectionBuilder(self).build()
        layout.addWidget(sheet_format_box)

        basic_builder.build_tip_section(layout)
        layout.addStretch()

        notifier_cfg = self.config.get("notifier", {})
        provider = notifier_cfg.get("provider", "none")
        index = self.provider_combo.findText(provider)
        self.provider_combo.setCurrentIndex(index if index >= 0 else 0)
        self._normalize_captcha_server_path_in_widget()
        self._on_captcha_server_protocol_changed()
        self._refresh_captcha_server_status_label()
        self._load_google_sheet_format_to_widgets()
        self._disable_settings_combo_wheel(content)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content)
        self._settings_scroll_area = scroll
        return scroll

    def _disable_settings_combo_wheel(self, root: QWidget) -> None:
        for combo in root.findChildren(QComboBox):
            combo.installEventFilter(self._settings_no_wheel_filter)
        for spin_box in root.findChildren(QSpinBox):
            spin_box.installEventFilter(self._settings_no_wheel_filter)

    def _forward_settings_wheel_event(self, source_widget: QWidget, event: QWheelEvent) -> None:
        if self._settings_scroll_area is None:
            return
        viewport = self._settings_scroll_area.viewport()
        if viewport is None:
            return

        global_pos = source_widget.mapToGlobal(event.position().toPoint())
        viewport_pos = viewport.mapFromGlobal(global_pos)
        forwarded_event = QWheelEvent(
            QPointF(viewport_pos),
            QPointF(global_pos),
            event.pixelDelta(),
            event.angleDelta(),
            event.buttons(),
            event.modifiers(),
            event.phase(),
            event.inverted(),
            event.source(),
            event.pointingDevice(),
        )
        QApplication.sendEvent(viewport, forwarded_event)

    def _build_bot_log_tab(self) -> QWidget:
        return LogTabsBuilder(self).build_bot_log_tab()

    def _build_application_log_tab(self) -> QWidget:
        return LogTabsBuilder(self).build_application_log_tab()

    def _setup_gui_application_log_handler(self) -> None:
        self.gui_log_emitter = QtSignalLogEmitter()
        self.gui_log_emitter.log_line.connect(self._append_application_log_line)
        self.gui_log_handler = QtSignalLogHandler(self.gui_log_emitter)
        self.gui_log_handler.setLevel(logging.INFO)
        self.gui_log_handler.setFormatter(
            logging.Formatter(
                "[%(asctime)s] [%(levelname)-8s] %(name)s: %(message)s",
                "%Y-%m-%d %H:%M:%S",
            )
        )
        logging.getLogger().addHandler(self.gui_log_handler)
        self._append_application_log_line(
            f"[INFO] application: 應用程式日誌已啟用，檔案: {to_universal_path(self.app_log_file)}"
        )

    def _append_application_log_line(self, line: str) -> None:
        self._append_log_line_preserve_scroll(self.app_log_view, line)

    def _append_log_line_preserve_scroll(self, view: QPlainTextEdit, line: str) -> None:
        vbar = view.verticalScrollBar()
        hbar = view.horizontalScrollBar()
        old_v = vbar.value()
        old_h = hbar.value()
        old_max_v = vbar.maximum()
        follow_bottom = (old_max_v <= 0) or (old_v >= old_max_v - 2)

        view.appendPlainText(line)

        new_vbar = view.verticalScrollBar()
        new_hbar = view.horizontalScrollBar()
        new_max_v = new_vbar.maximum()
        if follow_bottom or (new_max_v <= 0):
            new_vbar.setValue(new_max_v)
        else:
            new_vbar.setValue(min(old_v, new_max_v))
        new_hbar.setValue(min(old_h, new_hbar.maximum()))

    def _set_log_view_text_preserve_scroll(self, view: QPlainTextEdit, text: str) -> None:
        vbar = view.verticalScrollBar()
        hbar = view.horizontalScrollBar()
        old_v = vbar.value()
        old_h = hbar.value()
        old_max_v = vbar.maximum()
        follow_bottom = (old_max_v <= 0) or (old_v >= old_max_v - 2)

        view.setPlainText(text)

        new_vbar = view.verticalScrollBar()
        new_hbar = view.horizontalScrollBar()
        new_max_v = new_vbar.maximum()
        if follow_bottom or (new_max_v <= 0):
            new_vbar.setValue(new_max_v)
        else:
            new_vbar.setValue(min(old_v, new_max_v))
        new_hbar.setValue(min(old_h, new_hbar.maximum()))

    def _apply_app_log_wrap_setting(self) -> None:
        self.app_log_view.setLineWrapMode(
            QPlainTextEdit.LineWrapMode.WidgetWidth
            if self.app_log_wrap_checkbox.isChecked()
            else QPlainTextEdit.LineWrapMode.NoWrap
        )

    def _setup_bot_status_timer(self) -> None:
        self.bot_status_timer = QTimer(self)
        self.bot_status_timer.setInterval(2000)
        self.bot_status_timer.timeout.connect(self._on_bot_status_timer)
        self.bot_status_timer.start()
        self._on_bot_status_timer()
        self._apply_log_wrap_settings()

    def _on_bot_status_timer(self) -> None:
        self._update_bot_status_labels()
        self._refresh_bot_logs()

    def _build_feature_tab(self) -> QWidget:
        return LogTabsBuilder(self).build_feature_tab()

    def _setup_scheduler(self) -> None:
        self.scheduler_timer = QTimer(self)
        self.scheduler_timer.setInterval(30 * 1000)
        self.scheduler_timer.timeout.connect(self._on_scheduler_tick)
        self.scheduler_timer.start()

    def closeEvent(self, event: QCloseEvent, /) -> None:
        self.window_close_controller.handle_close_event(
            force_exit=self.force_exit,
            has_tray_icon=bool(self.tray_icon),
            stop_captcha_server=self.captcha_server.stop,
            stop_check_ipc_server=self._stop_check_ipc_server,
            stop_all_bots=self._stop_all_bots,
            release_instance_lock=lambda: self._instance_lock.release() if self._instance_lock is not None else None,
            accept_event=event.accept,
            ignore_event=event.ignore,
            hide_window=self.hide,
            show_minimize_message=lambda: self.statusBar().showMessage("已最小化到系統匣"),
        )
















































































































































def run() -> None:
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--bot", choices=["discord", "telegram"], default=None)
    parser.add_argument("--lifecycle-notify", choices=["discord", "telegram"], default=None)
    parser.add_argument("--lifecycle-action", choices=["shutdown"], default="shutdown")
    args, _ = parser.parse_known_args(sys.argv[1:])
    if args.lifecycle_notify is not None:
        _run_lifecycle_notify(args.lifecycle_notify, args.lifecycle_action)
        return
    if args.bot == "discord":
        from MessagingApp.discordBot import run_discord_bot
        run_discord_bot()
        return
    if args.bot == "telegram":
        from MessagingApp.telegramBot import run_telegram_bot
        run_telegram_bot()
        return

    if getattr(sys, "frozen", False):
        os.environ["CYUT_APP_BASE_DIR"] = to_universal_path(Path(sys.executable).resolve().parent)
    else:
        os.environ["CYUT_APP_BASE_DIR"] = to_universal_path(Path(__file__).resolve().parent)
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    window = ScholarshipApp()
    window.show()
    sys.exit(app.exec())


def _run_lifecycle_notify(provider: str, action: str) -> None:
    provider_text = provider.strip().lower()
    if provider_text not in {"discord", "telegram"}:
        return
    if action != "shutdown":
        return
    platform_name = "Discord" if provider_text == "discord" else "Telegram"
    message = (
        f"[{platform_name}] 關機 | 時間: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | "
        f"電腦: {socket.gethostname()} | 平台: {platform_name}"
    )
    config = NotificationConfig(
        provider=provider_text,
        discord_bot_token=os.getenv("CYUT_DISCORD_BOT_TOKEN", "").strip(),
        discord_linked_users_file=os.getenv("CYUT_DISCORD_LINKED_USERS_FILE", "").strip(),
        telegram_token=os.getenv("CYUT_TELEGRAM_BOT_TOKEN", "").strip(),
        telegram_linked_users_file=os.getenv("CYUT_TELEGRAM_LINKED_USERS_FILE", "").strip(),
    )
    try:
        Notifier(config, timeout=2).send_text(message)
    except Exception:
        return


if __name__ == "__main__":
    run()
