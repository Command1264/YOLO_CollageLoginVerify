from __future__ import annotations

from typing import Any

from PySide6.QtGui import QFontDatabase
from PySide6.QtWidgets import QMessageBox


class MainWindowSettingsSheetFormatMixin:
    def _on_google_sheet_width_mode_changed(self: Any) -> None:
        mode = self.gs_column_width_mode_combo.currentData() or "default"
        self.gs_column_width_value_spin.setEnabled(mode == "fixed")

    def _default_google_sheet_column_alignments(self: Any) -> dict[str, dict[str, str]]:
        return self.gs_format_controller.default_column_alignments()

    def _build_google_sheet_font_family_options(self: Any) -> list[str]:
        return self.gs_format_controller.build_font_family_options(list(QFontDatabase.families()))

    def _get_dataset_columns_from_cache(self: Any, dataset_name: str) -> list[str]:
        return self.gs_format_controller.get_dataset_columns_from_cache(
            cache_dir=self.application_dir / ".cache",
            dataset_name=dataset_name,
        )

    def _build_ordered_alignment_map(self: Any, dataset_name: str, source_map: dict[str, str]) -> dict[str, str]:
        return self.gs_format_controller.build_ordered_alignment_map(
            dataset_name=dataset_name,
            source_map=source_map,
            dataset_columns=self._get_dataset_columns_from_cache(dataset_name),
        )

    def _normalize_google_sheet_column_alignments(self: Any, raw_value: object) -> dict[str, dict[str, str]]:
        return self.gs_format_controller.normalize_column_alignments(
            cache_dir=self.application_dir / ".cache",
            raw_value=raw_value,
        )

    def _on_alignment_dataset_changed(self: Any) -> None:
        self._save_current_alignment_table_to_memory()
        self._load_alignment_table_for_selected_dataset()

    def _save_current_alignment_table_to_memory(self: Any) -> None:
        if not hasattr(self, "gs_column_alignment_map"):
            return
        dataset_name = str(getattr(self, "gs_alignment_current_dataset", "") or "").strip()
        self.gs_alignment_ui_controller.save_current_alignment_table_to_memory(
            column_alignment_map=self.gs_column_alignment_map,
            dataset_name=dataset_name,
            table=self.gs_alignment_table,
        )

    def _alignment_column_display_name(self: Any, dataset_name: str, column_name: str) -> str:
        return column_name

    def _load_alignment_table_for_selected_dataset(self: Any) -> None:
        if not hasattr(self, "gs_column_alignment_map"):
            return
        dataset_name = str(self.gs_align_dataset_combo.currentData() or "").strip()
        self.gs_alignment_current_dataset = dataset_name
        dataset_map: dict[str, str] = self.gs_column_alignment_map.get(dataset_name, {})
        self.gs_alignment_ui_controller.load_alignment_table(
            table=self.gs_alignment_table,
            dataset_name=dataset_name,
            dataset_map=dataset_map,
            display_name_resolver=self._alignment_column_display_name,
        )
        self._resize_alignment_table_height()

    def _resize_alignment_table_height(self: Any) -> None:
        self.gs_alignment_ui_controller.resize_alignment_table_height(self.gs_alignment_table)

    def _reset_current_dataset_alignment_defaults(self: Any) -> None:
        defaults = self._default_google_sheet_column_alignments()
        dataset_name = str(self.gs_align_dataset_combo.currentData() or "").strip()
        if dataset_name == "" or dataset_name not in defaults:
            return
        if not hasattr(self, "gs_column_alignment_map"):
            self.gs_column_alignment_map = self._normalize_google_sheet_column_alignments(defaults)
        self.gs_column_alignment_map[dataset_name] = self._build_ordered_alignment_map(
            dataset_name,
            defaults[dataset_name],
        )
        self._load_alignment_table_for_selected_dataset()

    def _load_google_sheet_format_to_widgets(self: Any) -> None:
        cfg = self.config.get("google_sheet_format", {})
        font_size = str(cfg.get("font_size", "")).strip()
        font_family = str(cfg.get("font_family", "")).strip()
        font_color = str(cfg.get("font_color", "")).strip()
        header_alignment = str(cfg.get("header_alignment", "center")).strip().lower() or "center"
        apply_mode = str(cfg.get("apply_mode", "on_change")).strip() or "on_change"
        width_mode = str(cfg.get("column_width_mode", "default")).strip() or "default"
        width_value = int(cfg.get("column_width_value", 120))
        min_width = int(cfg.get("column_min_width", 100))
        column_alignments = self._normalize_google_sheet_column_alignments(cfg.get("column_alignments", {}))

        idx = self.gs_font_size_combo.findData(font_size)
        self.gs_font_size_combo.setCurrentIndex(idx if idx >= 0 else 0)
        idx = self.gs_font_family_combo.findData(font_family)
        if idx < 0:
            idx = self.gs_font_family_combo.findData("Arial")
        self.gs_font_family_combo.setCurrentIndex(idx if idx >= 0 else 0)
        idx = self.gs_font_color_combo.findData(font_color)
        self.gs_font_color_combo.setCurrentIndex(idx if idx >= 0 else 0)
        idx = self.gs_header_alignment_combo.findData(header_alignment)
        self.gs_header_alignment_combo.setCurrentIndex(idx if idx >= 0 else 1)
        idx = self.gs_apply_mode_combo.findData(apply_mode)
        self.gs_apply_mode_combo.setCurrentIndex(idx if idx >= 0 else 0)
        idx = self.gs_column_width_mode_combo.findData(width_mode)
        self.gs_column_width_mode_combo.setCurrentIndex(idx if idx >= 0 else 0)
        self.gs_column_width_value_spin.setValue(width_value if 40 <= width_value <= 600 else 120)
        self.gs_column_min_width_spin.setValue(min_width if 20 <= min_width <= 600 else 100)
        self.gs_column_alignment_map = column_alignments
        self._load_alignment_table_for_selected_dataset()
        self._on_google_sheet_width_mode_changed()

    def _current_google_sheet_format_config(self: Any) -> dict:
        self._save_current_alignment_table_to_memory()
        return {
            "font_size": str(self.gs_font_size_combo.currentData() or "").strip(),
            "font_family": str(self.gs_font_family_combo.currentData() or "Arial").strip(),
            "font_color": str(self.gs_font_color_combo.currentData() or "").strip(),
            "header_alignment": str(self.gs_header_alignment_combo.currentData() or "center").strip(),
            "apply_mode": str(self.gs_apply_mode_combo.currentData() or "on_change").strip(),
            "column_width_mode": str(self.gs_column_width_mode_combo.currentData() or "default").strip(),
            "column_width_value": int(self.gs_column_width_value_spin.value()),
            "column_min_width": int(self.gs_column_min_width_spin.value()),
            "column_alignments": self.gs_column_alignment_map,
        }

    def _save_google_sheet_format_config(self: Any) -> None:
        self.config["google_sheet_format"] = self._current_google_sheet_format_config()
        self._save_config()
        QMessageBox.information(self, "Google Sheet 格式", "Google Sheet 上傳格式已儲存。")
