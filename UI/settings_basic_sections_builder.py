from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
)


class SettingsBasicSectionsBuilder:
    """Build login/verify/notify sections for settings tab."""

    def __init__(self, app) -> None:
        self.app = app

    def build_login_section(self, layout: QVBoxLayout) -> None:
        login_box = QGroupBox("學生系統登入設定")
        login_form = QFormLayout(login_box)
        login_cfg = self.app.config.get("login", {})
        self.app.login_account = QLineEdit(str(login_cfg.get("account", "")))
        self.app.login_password = QLineEdit(str(login_cfg.get("password", "")))
        self.app.login_password.setEchoMode(QLineEdit.EchoMode.Password)
        self.app.password_visible = False
        self.app.password_toggle_btn = QPushButton("👁")
        self.app.password_toggle_btn.setFixedWidth(36)
        self.app.password_toggle_btn.setToolTip("顯示密碼")
        self.app.password_toggle_btn.clicked.connect(self.app._toggle_password_visibility)
        password_layout = QHBoxLayout()
        password_layout.setContentsMargins(0, 0, 0, 0)
        password_layout.addWidget(self.app.login_password)
        password_layout.addWidget(self.app.password_toggle_btn)
        login_form.addRow("帳號", self.app.login_account)
        login_form.addRow("密碼", password_layout)
        layout.addWidget(login_box)

        login_btn_layout = QHBoxLayout()
        login_save_btn = QPushButton("儲存學生系統登入設定")
        login_save_btn.clicked.connect(self.app._save_student_login_config)
        login_btn_layout.addWidget(login_save_btn)
        layout.addLayout(login_btn_layout)

    def build_verify_section(self, layout: QVBoxLayout) -> None:
        verify_cfg = self.app.config.get("verify", {})
        verify_box = QGroupBox("驗證碼模型與伺服器設定")
        verify_form = QFormLayout(verify_box)
        self.app.login_model_path = QLineEdit(
            self.app._resolve_display_path(
                str(verify_cfg.get("model_path", "")),
                self.app._get_default_model_path(),
            )
        )
        self.app.login_model_store_relative = QCheckBox("相對")
        self.app.login_model_store_relative.setChecked(self.app._is_path_store_relative("model_path"))
        self.app.login_model_browse_btn = QPushButton("選擇")
        self.app.login_model_browse_btn.clicked.connect(self.app._browse_model_file)
        model_path_layout = QHBoxLayout()
        model_path_layout.setContentsMargins(0, 0, 0, 0)
        model_path_layout.addWidget(self.app.login_model_path)
        model_path_layout.addWidget(self.app.login_model_store_relative)
        model_path_layout.addWidget(self.app.login_model_browse_btn)

        captcha_cfg = verify_cfg.get("captcha_server", {})
        self.app.captcha_server_enabled = QCheckBox("啟用驗證碼辨識伺服器")
        self.app.captcha_server_enabled.setChecked(bool(captcha_cfg.get("enabled", False)))
        self.app.captcha_server_protocol = QComboBox()
        self.app.captcha_server_protocol.addItem("HTTP", "http")
        self.app.captcha_server_protocol.addItem("HTTPS", "https")
        protocol_idx = self.app.captcha_server_protocol.findData(str(captcha_cfg.get("protocol", "http")).strip().lower())
        self.app.captcha_server_protocol.setCurrentIndex(protocol_idx if protocol_idx >= 0 else 0)
        self.app.captcha_server_host = QLineEdit(str(captcha_cfg.get("host", "127.0.0.1")))
        self.app.captcha_server_port = QSpinBox()
        self.app.captcha_server_port.setRange(1, 65535)
        self.app.captcha_server_port.setValue(int(captcha_cfg.get("port", 5000)))
        self.app.captcha_server_path = QLineEdit(str(captcha_cfg.get("path", "/solve_captcha")))
        self.app.captcha_server_cert_file = QLineEdit(
            self.app._resolve_display_path(
                str(captcha_cfg.get("cert_file", "")),
                self.app._get_default_https_cert_file(),
            )
        )
        self.app.captcha_server_cert_store_relative = QCheckBox("相對")
        self.app.captcha_server_cert_store_relative.setChecked(self.app._is_path_store_relative("captcha_cert_file"))
        self.app.captcha_server_cert_browse_btn = QPushButton("選擇")
        self.app.captcha_server_cert_browse_btn.clicked.connect(self.app._browse_captcha_server_cert_file)
        cert_layout = QHBoxLayout()
        cert_layout.setContentsMargins(0, 0, 0, 0)
        cert_layout.addWidget(self.app.captcha_server_cert_file)
        cert_layout.addWidget(self.app.captcha_server_cert_store_relative)
        cert_layout.addWidget(self.app.captcha_server_cert_browse_btn)
        self.app.captcha_server_key_file = QLineEdit(
            self.app._resolve_display_path(
                str(captcha_cfg.get("key_file", "")),
                self.app._get_default_https_key_file(),
            )
        )
        self.app.captcha_server_key_store_relative = QCheckBox("相對")
        self.app.captcha_server_key_store_relative.setChecked(self.app._is_path_store_relative("captcha_key_file"))
        self.app.captcha_server_key_browse_btn = QPushButton("選擇")
        self.app.captcha_server_key_browse_btn.clicked.connect(self.app._browse_captcha_server_key_file)
        key_layout = QHBoxLayout()
        key_layout.setContentsMargins(0, 0, 0, 0)
        key_layout.addWidget(self.app.captcha_server_key_file)
        key_layout.addWidget(self.app.captcha_server_key_store_relative)
        key_layout.addWidget(self.app.captcha_server_key_browse_btn)
        self.app.captcha_server_status = QLabel("未啟動")
        self.app.captcha_server_start_btn = QPushButton("啟動伺服器")
        self.app.captcha_server_start_btn.clicked.connect(self.app._start_captcha_server_from_widgets)
        self.app.captcha_server_stop_btn = QPushButton("停止伺服器")
        self.app.captcha_server_stop_btn.clicked.connect(self.app._stop_captcha_server_from_widgets)
        self.app.captcha_server_protocol.currentIndexChanged.connect(self.app._on_captcha_server_protocol_changed)
        captcha_btn_layout = QHBoxLayout()
        captcha_btn_layout.setContentsMargins(0, 0, 0, 0)
        captcha_btn_layout.addWidget(self.app.captcha_server_start_btn)
        captcha_btn_layout.addWidget(self.app.captcha_server_stop_btn)
        verify_form.addRow("模型路徑", model_path_layout)
        verify_form.addRow("", self.app.captcha_server_enabled)
        verify_form.addRow("協定", self.app.captcha_server_protocol)
        verify_form.addRow("伺服器 IP", self.app.captcha_server_host)
        verify_form.addRow("伺服器 Port", self.app.captcha_server_port)
        verify_form.addRow("辨識路徑", self.app.captcha_server_path)
        verify_form.addRow("HTTPS 憑證(cert)", cert_layout)
        verify_form.addRow("HTTPS 私鑰(key)", key_layout)
        verify_form.addRow("伺服器狀態", self.app.captcha_server_status)
        verify_form.addRow("", captcha_btn_layout)
        layout.addWidget(verify_box)

        verify_btn_layout = QHBoxLayout()
        verify_save_btn = QPushButton("儲存模型與伺服器設定")
        verify_save_btn.clicked.connect(self.app._save_model_server_config)
        verify_btn_layout.addWidget(verify_save_btn)
        layout.addLayout(verify_btn_layout)

    def build_notify_section(self, layout: QVBoxLayout) -> None:
        notify_box = QGroupBox("通知設定")
        notify_form = QFormLayout(notify_box)

        self.app.provider_combo = QComboBox()
        self.app.provider_combo.addItems(["none", "discord", "telegram", "both"])
        self.app.discord_bot_token = QLineEdit(self.app.config.get("notifier", {}).get("discord_bot_token", ""))
        self.app.discord_linked_users_file = QLineEdit(
            self.app._resolve_display_path(
                str(self.app.config.get("notifier", {}).get("discord_linked_users_file", "")),
                self.app._get_default_linked_users_file("discord"),
            )
        )
        self.app.discord_linked_users_store_relative = QCheckBox("相對")
        self.app.discord_linked_users_store_relative.setChecked(self.app._is_path_store_relative("discord_linked_users_file"))
        self.app.telegram_token = QLineEdit(self.app.config.get("notifier", {}).get("telegram_token", ""))
        self.app.telegram_linked_users_file = QLineEdit(
            self.app._resolve_display_path(
                str(self.app.config.get("notifier", {}).get("telegram_linked_users_file", "")),
                self.app._get_default_linked_users_file("telegram"),
            )
        )
        self.app.telegram_linked_users_store_relative = QCheckBox("相對")
        self.app.telegram_linked_users_store_relative.setChecked(self.app._is_path_store_relative("telegram_linked_users_file"))
        self.app.discord_linked_users_browse_file_btn = QPushButton("選擇檔案")
        self.app.discord_linked_users_browse_file_btn.clicked.connect(self.app._browse_discord_linked_users_file)
        self.app.discord_linked_users_browse_dir_btn = QPushButton("選擇資料夾")
        self.app.discord_linked_users_browse_dir_btn.clicked.connect(self.app._browse_discord_linked_users_dir)
        discord_linked_users_layout = QHBoxLayout()
        discord_linked_users_layout.setContentsMargins(0, 0, 0, 0)
        discord_linked_users_layout.addWidget(self.app.discord_linked_users_file)
        discord_linked_users_layout.addWidget(self.app.discord_linked_users_store_relative)
        discord_linked_users_layout.addWidget(self.app.discord_linked_users_browse_file_btn)
        discord_linked_users_layout.addWidget(self.app.discord_linked_users_browse_dir_btn)

        self.app.telegram_linked_users_browse_file_btn = QPushButton("選擇檔案")
        self.app.telegram_linked_users_browse_file_btn.clicked.connect(self.app._browse_telegram_linked_users_file)
        self.app.telegram_linked_users_browse_dir_btn = QPushButton("選擇資料夾")
        self.app.telegram_linked_users_browse_dir_btn.clicked.connect(self.app._browse_telegram_linked_users_dir)
        telegram_linked_users_layout = QHBoxLayout()
        telegram_linked_users_layout.setContentsMargins(0, 0, 0, 0)
        telegram_linked_users_layout.addWidget(self.app.telegram_linked_users_file)
        telegram_linked_users_layout.addWidget(self.app.telegram_linked_users_store_relative)
        telegram_linked_users_layout.addWidget(self.app.telegram_linked_users_browse_file_btn)
        telegram_linked_users_layout.addWidget(self.app.telegram_linked_users_browse_dir_btn)
        self.app.notify_lifecycle_checkbox = QCheckBox("通知開機/關機")
        self.app.notify_lifecycle_checkbox.setChecked(bool(self.app.config.get("notifier", {}).get("notify_bot_lifecycle", True)))

        notify_form.addRow("通知管道", self.app.provider_combo)
        notify_form.addRow("Discord Bot Token", self.app.discord_bot_token)
        notify_form.addRow("Discord 訂閱名單檔", discord_linked_users_layout)
        notify_form.addRow("Telegram Bot Token", self.app.telegram_token)
        notify_form.addRow("Telegram 訂閱名單檔", telegram_linked_users_layout)
        notify_form.addRow("", self.app.notify_lifecycle_checkbox)

        btn_layout = QHBoxLayout()
        save_btn = QPushButton("儲存通知設定")
        save_btn.clicked.connect(self.app._save_notify_config)
        test_btn = QPushButton("發送測試訊息")
        test_btn.clicked.connect(self.app._send_test_notify)
        btn_layout.addWidget(save_btn)
        btn_layout.addWidget(test_btn)
        layout.addWidget(notify_box)
        layout.addLayout(btn_layout)

    def build_tip_section(self, layout: QVBoxLayout) -> None:
        tip = QLabel(
            "訂閱制說明：使用者需先對機器人輸入 /link，並輸入後台顯示的 N 位數驗證碼完成綁定；\n"
            "解除訂閱請用 /unlink。推播僅會送到 linked_users.json 內的已訂閱者。"
        )
        tip.setWordWrap(True)
        layout.addWidget(tip)
