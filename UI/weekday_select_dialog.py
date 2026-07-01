from __future__ import annotations

from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QVBoxLayout,
    QWidget,
)


class WeekdaySelectDialog(QDialog):
    """Weekday multi-select dialog with preset shortcuts."""

    def __init__(self, selected_days: list[int], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("選擇星期")
        self.resize(360, 280)
        self._syncing = False
        self.day_values = [1, 2, 3, 4, 5, 6, 7]

        root_layout = QVBoxLayout(self)

        preset_box = QGroupBox("快捷選項")
        preset_layout = QHBoxLayout(preset_box)
        self.everyday_checkbox = QCheckBox("每天")
        self.workday_checkbox = QCheckBox("工作日")
        self.weekend_checkbox = QCheckBox("假日")
        preset_layout.addWidget(self.everyday_checkbox)
        preset_layout.addWidget(self.workday_checkbox)
        preset_layout.addWidget(self.weekend_checkbox)
        root_layout.addWidget(preset_box)

        day_box = QGroupBox("星期")
        day_layout = QGridLayout(day_box)
        self.day_checkboxes: dict[int, QCheckBox] = {}
        labels = {
            1: "星期一",
            2: "星期二",
            3: "星期三",
            4: "星期四",
            5: "星期五",
            6: "星期六",
            7: "星期日",
        }
        for idx, value in enumerate(self.day_values):
            checkbox = QCheckBox(labels[value])
            self.day_checkboxes[value] = checkbox
            day_layout.addWidget(checkbox, idx // 2, idx % 2)
        root_layout.addWidget(day_box)

        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        root_layout.addWidget(buttons)

        self.everyday_checkbox.toggled.connect(self._on_preset_toggled)
        self.workday_checkbox.toggled.connect(self._on_preset_toggled)
        self.weekend_checkbox.toggled.connect(self._on_preset_toggled)
        for checkbox in self.day_checkboxes.values():
            checkbox.toggled.connect(self._on_day_toggled)

        self._apply_days(selected_days)

    def get_selected_days(self) -> list[int]:
        days = [day for day, checkbox in self.day_checkboxes.items() if checkbox.isChecked()]
        return sorted(days)

    def _apply_days(self, days: list[int]) -> None:
        self._syncing = True
        selected = set(days)
        for day, checkbox in self.day_checkboxes.items():
            checkbox.setChecked(day in selected)
        self._update_preset_checkboxes()
        self._syncing = False

    def _on_preset_toggled(self, checked: bool) -> None:
        if self._syncing or (not checked):
            return
        sender = self.sender()
        if sender is self.everyday_checkbox:
            self._apply_days([1, 2, 3, 4, 5, 6, 7])
        elif sender is self.workday_checkbox:
            self._apply_days([1, 2, 3, 4, 5])
        elif sender is self.weekend_checkbox:
            self._apply_days([6, 7])

    def _on_day_toggled(self, _checked: bool) -> None:
        if self._syncing:
            return
        self._syncing = True
        self._update_preset_checkboxes()
        self._syncing = False

    def _update_preset_checkboxes(self) -> None:
        selected = set(self.get_selected_days())
        self.everyday_checkbox.setChecked(selected == {1, 2, 3, 4, 5, 6, 7})
        self.workday_checkbox.setChecked(selected == {1, 2, 3, 4, 5})
        self.weekend_checkbox.setChecked(selected == {6, 7})
