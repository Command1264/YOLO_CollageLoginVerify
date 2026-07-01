from __future__ import annotations

from collections.abc import Callable

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QComboBox, QTableWidget, QTableWidgetItem


class GoogleSheetAlignmentUiController:
    """Handle Google Sheet alignment table UI read/write behavior."""

    def save_current_alignment_table_to_memory(
        self,
        column_alignment_map: dict[str, dict[str, str]],
        dataset_name: str,
        table: QTableWidget,
    ) -> None:
        """Persist current table alignment selections into memory map.

        Args:
            column_alignment_map (dict[str, dict[str, str]]): Alignment map by dataset.
            dataset_name (str): Current dataset key.
            table (QTableWidget): Alignment table widget.
        """
        if dataset_name.strip() == "":
            return
        dataset_map = column_alignment_map.setdefault(dataset_name, {})
        for row in range(table.rowCount()):
            column_item = table.item(row, 0)
            align_combo = table.cellWidget(row, 1)
            if column_item is None or not isinstance(align_combo, QComboBox):
                continue
            raw_column_name = column_item.data(Qt.ItemDataRole.UserRole)
            column_name = str(raw_column_name if raw_column_name else column_item.text()).strip()
            if column_name == "":
                continue
            alignment = str(align_combo.currentData() or "center").strip().lower()
            if alignment not in {"left", "center", "right"}:
                alignment = "center"
            dataset_map[column_name] = alignment

    def load_alignment_table(
        self,
        table: QTableWidget,
        dataset_name: str,
        dataset_map: dict[str, str],
        display_name_resolver: Callable[[str, str], str],
    ) -> None:
        """Rebuild alignment table from dataset alignment map.

        Args:
            table (QTableWidget): Alignment table widget.
            dataset_name (str): Current dataset key.
            dataset_map (dict[str, str]): Column alignment map for dataset.
            display_name_resolver (Callable[[str, str], str]): Display name mapper.
        """
        table.setRowCount(0)
        for row_index, (column_name, alignment) in enumerate(dataset_map.items()):
            table.insertRow(row_index)
            item = QTableWidgetItem(display_name_resolver(dataset_name, column_name))
            item.setData(Qt.ItemDataRole.UserRole, column_name)
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            table.setItem(row_index, 0, item)
            combo = QComboBox()
            combo.addItem("置左", "left")
            combo.addItem("置中", "center")
            combo.addItem("置右", "right")
            idx = combo.findData(alignment)
            combo.setCurrentIndex(idx if idx >= 0 else 1)
            table.setCellWidget(row_index, 1, combo)

    def resize_alignment_table_height(self, table: QTableWidget) -> None:
        """Resize alignment table height to fit all rows.

        Args:
            table (QTableWidget): Alignment table widget.
        """
        row_count = table.rowCount()
        header_height = table.horizontalHeader().height()
        rows_height = sum(table.rowHeight(row) for row in range(row_count))
        frame_height = table.frameWidth() * 2
        extra_padding = 4
        target_height = max(80, header_height + rows_height + frame_height + extra_padding)
        table.setFixedHeight(target_height)
