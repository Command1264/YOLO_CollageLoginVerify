from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QPushButton,
    QSizePolicy,
    QSpinBox,
    QTableWidget,
    QHeaderView,
    QVBoxLayout,
    QWidget,
)


class SettingsSheetFormatSectionBuilder:
    """Build Google Sheet format section for settings tab."""

    def __init__(self, app) -> None:
        self.app = app

    def build(self) -> QWidget:
        sheet_format_box = QGroupBox("Google Sheet 上傳格式")
        sheet_format_form = QFormLayout(sheet_format_box)
        self.app.gs_font_size_combo = QComboBox()
        self.app.gs_font_size_combo.addItem("預設", "")
        for value in [10, 12, 14, 16, 18, 20]:
            self.app.gs_font_size_combo.addItem(str(value), str(value))

        self.app.gs_font_family_combo = QComboBox()
        self.app.gs_font_family_combo.setMaxVisibleItems(14)
        self.app.gs_font_family_combo.view().setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        for value in self.app._build_google_sheet_font_family_options():
            self.app.gs_font_family_combo.addItem(value, value)

        self.app.gs_font_color_combo = QComboBox()
        self.app.gs_font_color_combo.addItem("預設", "")
        self.app.gs_font_color_combo.addItem("黑色", "#000000")
        self.app.gs_font_color_combo.addItem("深灰", "#333333")
        self.app.gs_font_color_combo.addItem("藍色", "#1A73E8")
        self.app.gs_font_color_combo.addItem("紅色", "#D93025")
        self.app.gs_font_color_combo.addItem("綠色", "#188038")
        self.app.gs_header_alignment_combo = QComboBox()
        self.app.gs_header_alignment_combo.addItem("置左", "left")
        self.app.gs_header_alignment_combo.addItem("置中", "center")
        self.app.gs_header_alignment_combo.addItem("置右", "right")

        self.app.gs_column_width_mode_combo = QComboBox()
        self.app.gs_column_width_mode_combo.addItem("預設", "default")
        self.app.gs_column_width_mode_combo.addItem("自動", "auto")
        self.app.gs_column_width_mode_combo.addItem("固定像素", "fixed")
        self.app.gs_apply_mode_combo = QComboBox()
        self.app.gs_apply_mode_combo.addItem("有內容變更時", "on_change")
        self.app.gs_apply_mode_combo.addItem("僅首次建立工作表", "first_time")
        self.app.gs_apply_mode_combo.addItem("每次檢查都套用", "always")
        self.app.gs_column_width_value_spin = QSpinBox()
        self.app.gs_column_width_value_spin.setRange(40, 600)
        self.app.gs_column_width_value_spin.setValue(120)
        self.app.gs_column_min_width_spin = QSpinBox()
        self.app.gs_column_min_width_spin.setRange(20, 600)
        self.app.gs_column_min_width_spin.setValue(100)
        self.app.gs_column_width_mode_combo.currentIndexChanged.connect(self.app._on_google_sheet_width_mode_changed)

        sheet_format_form.addRow("字體大小", self.app.gs_font_size_combo)
        sheet_format_form.addRow("字型", self.app.gs_font_family_combo)
        sheet_format_form.addRow("文字顏色", self.app.gs_font_color_combo)
        sheet_format_form.addRow("標題對齊", self.app.gs_header_alignment_combo)
        sheet_format_form.addRow("格式套用時機", self.app.gs_apply_mode_combo)
        sheet_format_form.addRow("欄寬模式", self.app.gs_column_width_mode_combo)
        sheet_format_form.addRow("固定欄寬(px)", self.app.gs_column_width_value_spin)
        sheet_format_form.addRow("欄寬最小值(px)", self.app.gs_column_min_width_spin)

        self.app.gs_align_dataset_combo = QComboBox()
        self.app.gs_align_dataset_combo.addItem("校內外獎助學金", "校內外獎助學金")
        self.app.gs_align_dataset_combo.addItem("個人申請結果", "個人申請結果")
        self.app.gs_align_dataset_combo.currentIndexChanged.connect(self.app._on_alignment_dataset_changed)
        self.app.gs_align_reset_btn = QPushButton("還原該資料集預設")
        self.app.gs_align_reset_btn.clicked.connect(self.app._reset_current_dataset_alignment_defaults)
        align_ctrl_layout = QHBoxLayout()
        align_ctrl_layout.addWidget(self.app.gs_align_dataset_combo)
        align_ctrl_layout.addWidget(self.app.gs_align_reset_btn)

        self.app.gs_alignment_table = QTableWidget(0, 2)
        self.app.gs_alignment_table.setHorizontalHeaderLabels(["欄位名稱", "對齊"])
        self.app.gs_alignment_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self.app.gs_alignment_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self.app.gs_alignment_table.verticalHeader().setVisible(False)
        self.app.gs_alignment_table.verticalHeader().setDefaultSectionSize(32)
        self.app.gs_alignment_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.app.gs_alignment_table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.app.gs_alignment_table.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.app.gs_alignment_table.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.app.gs_alignment_table.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        align_box = QGroupBox("欄位對齊（可逐欄調整）")
        align_layout = QVBoxLayout(align_box)
        align_layout.addLayout(align_ctrl_layout)
        align_layout.addWidget(self.app.gs_alignment_table)
        sheet_format_form.addRow("欄位對齊", align_box)

        sheet_format_btn_layout = QHBoxLayout()
        self.app.gs_save_btn = QPushButton("儲存 Google Sheet 格式")
        self.app.gs_save_btn.clicked.connect(self.app._save_google_sheet_format_config)
        sheet_format_btn_layout.addWidget(self.app.gs_save_btn)
        sheet_format_form.addRow("", sheet_format_btn_layout)
        return sheet_format_box
