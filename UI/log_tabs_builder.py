from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)


class LogTabsBuilder:
    """Build bot/application/feature tabs for main window."""

    def __init__(self, app) -> None:
        self.app = app

    def build_bot_log_tab(self) -> QWidget:
        """Build bot status and bot logs tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        status_box = QGroupBox("Bot 狀態")
        status_form = QFormLayout(status_box)
        self.app.discord_status_label = QLabel("未啟動")
        self.app.telegram_status_label = QLabel("未啟動")
        status_form.addRow("Discord Bot", self.app.discord_status_label)
        status_form.addRow("Telegram Bot", self.app.telegram_status_label)
        layout.addWidget(status_box)

        log_box = QGroupBox("Bot Logs")
        log_layout = QVBoxLayout(log_box)

        discord_log_box = QGroupBox("Discord Bot Log")
        discord_log_layout = QVBoxLayout(discord_log_box)
        self.app.discord_wrap_checkbox = QCheckBox("自動換行")
        self.app.discord_wrap_checkbox.setChecked(False)
        self.app.discord_wrap_checkbox.stateChanged.connect(self.app._apply_log_wrap_settings)
        self.app.discord_log_view = QPlainTextEdit()
        self.app.discord_log_view.setReadOnly(True)
        self.app.discord_log_view.setFont(QFont("Consolas", 9))
        discord_log_layout.addWidget(self.app.discord_wrap_checkbox)
        discord_log_layout.addWidget(self.app.discord_log_view)

        telegram_log_box = QGroupBox("Telegram Bot Log")
        telegram_log_layout = QVBoxLayout(telegram_log_box)
        self.app.telegram_wrap_checkbox = QCheckBox("自動換行")
        self.app.telegram_wrap_checkbox.setChecked(False)
        self.app.telegram_wrap_checkbox.stateChanged.connect(self.app._apply_log_wrap_settings)
        self.app.telegram_log_view = QPlainTextEdit()
        self.app.telegram_log_view.setReadOnly(True)
        self.app.telegram_log_view.setFont(QFont("Consolas", 9))
        telegram_log_layout.addWidget(self.app.telegram_wrap_checkbox)
        telegram_log_layout.addWidget(self.app.telegram_log_view)

        logs_splitter = QSplitter(Qt.Orientation.Horizontal)
        logs_splitter.setChildrenCollapsible(False)
        logs_splitter.addWidget(discord_log_box)
        logs_splitter.addWidget(telegram_log_box)
        logs_splitter.setStretchFactor(0, 1)
        logs_splitter.setStretchFactor(1, 1)
        logs_splitter.setSizes([600, 600])
        log_layout.addWidget(logs_splitter)

        layout.addWidget(log_box, stretch=1)
        layout.addStretch()
        return tab

    def build_application_log_tab(self) -> QWidget:
        """Build application log tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        ctrl_layout = QHBoxLayout()
        self.app.app_log_wrap_checkbox = QCheckBox("自動換行")
        self.app.app_log_wrap_checkbox.setChecked(False)
        self.app.app_log_wrap_checkbox.stateChanged.connect(self.app._apply_app_log_wrap_setting)
        ctrl_layout.addWidget(self.app.app_log_wrap_checkbox)
        ctrl_layout.addStretch()
        layout.addLayout(ctrl_layout)

        self.app.app_log_view = QPlainTextEdit()
        self.app.app_log_view.setReadOnly(True)
        self.app.app_log_view.setFont(QFont("Consolas", 9))
        self.app.app_log_view.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        layout.addWidget(self.app.app_log_view, stretch=1)
        return tab

    def build_feature_tab(self) -> QWidget:
        """Build feature summary tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        text = QTextEdit()
        text.setReadOnly(True)
        text.setMarkdown(
            "### 專案功能統整\n"
            "- 驗證碼辨識：使用 YOLO 模型辨識朝陽系統驗證碼。\n"
            "- 學生系統登入：自動登入 `auth2.cyut.edu.tw` 與 `student.cyut.edu.tw`。\n"
            "- 獎助學金資料：抓取「校內外獎助學金」與「個人申請結果」。\n"
            "- Google Sheet：原核心模組可寫入與比對試算表。\n"
            "- 通訊推播：專案內已有 Discord/Telegram 整合模組。\n"
            "- 本 GUI：提供排程、多學期檢查、System Tray、Diff 顯示與推播設定。"
        )
        layout.addWidget(text)
        return tab
