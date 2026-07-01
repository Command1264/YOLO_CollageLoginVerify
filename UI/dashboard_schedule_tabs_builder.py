from __future__ import annotations

from PySide6.QtCore import QTime, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPlainTextEdit,
    QProgressBar,
    QPushButton,
    QTableWidget,
    QTimeEdit,
    QVBoxLayout,
    QWidget,
)


class DashboardScheduleTabsBuilder:
    """Build dashboard and schedule tabs for main window."""

    def __init__(self, app) -> None:
        self.app = app

    def build_dashboard_tab(self) -> QWidget:
        """Build dashboard tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        logo_label = QLabel()
        logo_pixmap = self.app._load_logo_pixmap()
        if logo_pixmap is not None:
            logo_label.setPixmap(
                logo_pixmap.scaled(
                    220,
                    220,
                    Qt.AspectRatioMode.KeepAspectRatio,
                    Qt.TransformationMode.SmoothTransformation,
                )
            )
            logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(logo_label)

        ctrl_box = QGroupBox("檢查控制")
        ctrl_layout = QGridLayout(ctrl_box)
        self.app.semester_combo = QComboBox()
        self.app.semester_combo.setMinimumWidth(240)
        self.app.refresh_semester_btn = QPushButton("刷新學期")
        self.app.refresh_semester_btn.clicked.connect(self.app._refresh_semesters)
        self.app.check_now_btn = QPushButton("立即檢查")
        self.app.check_now_btn.clicked.connect(self.app._check_now)

        ctrl_layout.addWidget(QLabel("目標學期"), 0, 0)
        ctrl_layout.addWidget(self.app.semester_combo, 0, 1)
        ctrl_layout.addWidget(self.app.refresh_semester_btn, 0, 2)
        ctrl_layout.addWidget(self.app.check_now_btn, 0, 3)
        self.app.check_progress_bar = QProgressBar()
        self.app.check_progress_bar.setRange(0, 100)
        self.app.check_progress_bar.setValue(0)
        self.app.check_progress_label = QLabel("待命")
        ctrl_layout.addWidget(self.app.check_progress_bar, 1, 0, 1, 3)
        ctrl_layout.addWidget(self.app.check_progress_label, 1, 3)
        layout.addWidget(ctrl_box)

        self.app.history_table = QTableWidget(0, 4)
        self.app.history_table.setHorizontalHeaderLabels(["時間", "資料集", "結果", "摘要"])
        self.app.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.app.history_table.verticalHeader().setVisible(False)
        self.app.history_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.app.history_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.app.history_table.cellDoubleClicked.connect(self.app._on_history_double_click)
        layout.addWidget(self.app.history_table, stretch=3)

        diff_box = QGroupBox("更新差異（Apply Patch 風格）")
        diff_layout = QVBoxLayout(diff_box)
        self.app.diff_view = QPlainTextEdit()
        self.app.diff_view.setReadOnly(True)
        self.app.diff_view.setFont(QFont("Consolas", 10))
        diff_layout.addWidget(self.app.diff_view)
        layout.addWidget(diff_box, stretch=4)
        return tab

    def build_schedule_tab(self) -> QWidget:
        """Build schedule tab."""
        tab = QWidget()
        layout = QVBoxLayout(tab)

        form_box = QGroupBox("新增排程")
        form_layout = QGridLayout(form_box)
        self.app.schedule_name = QLineEdit()
        self.app.schedule_name.setPlaceholderText("例如：早上巡檢")
        self.app.schedule_time = QTimeEdit()
        self.app.schedule_time.setDisplayFormat("HH:mm")
        self.app.schedule_time.setTime(QTime.currentTime())
        self.app.schedule_semester = QComboBox()
        self.app.schedule_semester.addItem("跟隨主控台選擇", "__follow__")

        self.app.selected_weekdays = [1, 2, 3, 4, 5]
        weekdays_layout = QHBoxLayout()
        self.app.weekday_display_label = QLabel(self.app._format_weekday_display(self.app.selected_weekdays))
        self.app.weekday_select_btn = QPushButton("選擇星期")
        self.app.weekday_select_btn.clicked.connect(self.app._open_weekday_dialog)
        weekdays_layout.addWidget(self.app.weekday_display_label, stretch=1)
        weekdays_layout.addWidget(self.app.weekday_select_btn)

        add_btn = QPushButton("加入排程")
        add_btn.clicked.connect(self.app._add_schedule)
        remove_btn = QPushButton("移除選取")
        remove_btn.clicked.connect(self.app._remove_selected_schedule)

        form_layout.addWidget(QLabel("名稱"), 0, 0)
        form_layout.addWidget(self.app.schedule_name, 0, 1)
        form_layout.addWidget(QLabel("時間"), 0, 2)
        form_layout.addWidget(self.app.schedule_time, 0, 3)
        form_layout.addWidget(QLabel("學期"), 1, 0)
        form_layout.addWidget(self.app.schedule_semester, 1, 1, 1, 3)
        form_layout.addWidget(QLabel("星期"), 2, 0)
        form_layout.addLayout(weekdays_layout, 2, 1, 1, 3)
        form_layout.addWidget(add_btn, 3, 2)
        form_layout.addWidget(remove_btn, 3, 3)
        layout.addWidget(form_box)

        self.app.schedule_table = QTableWidget(0, 6)
        self.app.schedule_table.setHorizontalHeaderLabels(["啟用", "名稱", "時間", "星期", "學期", "上次執行"])
        self.app.schedule_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.app.schedule_table.verticalHeader().setVisible(False)
        self.app.schedule_table.setEditTriggers(
            QAbstractItemView.EditTrigger.DoubleClicked | QAbstractItemView.EditTrigger.EditKeyPressed
        )
        self.app.schedule_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.app.schedule_table.itemChanged.connect(self.app._on_schedule_item_changed)
        self.app.schedule_table.cellDoubleClicked.connect(self.app._on_schedule_table_double_click)
        layout.addWidget(self.app.schedule_table, stretch=1)
        return tab
