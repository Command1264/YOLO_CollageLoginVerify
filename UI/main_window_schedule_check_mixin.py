from __future__ import annotations

from typing import Any

import functools
import uuid
from datetime import datetime

from PySide6.QtCore import QObject, QThread, QTime, Qt
from PySide6.QtWidgets import QMessageBox, QTableWidgetItem, QTimeEdit, QComboBox, QDialog

from UI.async_workers import CheckWorker, SemesterWorker
from UI.schedule_controller import ScheduleItem
from UI.weekday_select_dialog import WeekdaySelectDialog

class MainWindowScheduleCheckMixin:
    def _service_factory(self: Any):
        from UI.main_window_app import get_scholarship_service_class

        return get_scholarship_service_class()()

    def _load_semester_to_combo(self: Any) -> None:
        semesters = self.config.get("semesters", [])
        self.semester_combo.clear()
        self.schedule_semester.clear()
        self.schedule_semester.addItem("跟隨主控台選擇", "__follow__")
        for item in semesters:
            self.semester_combo.addItem(item.get("label", item.get("value", "")), item.get("value", ""))
            self.schedule_semester.addItem(item.get("label", item.get("value", "")), item.get("value", ""))
        selected = self.config.get("selected_semester", "")
        if selected:
            idx = self.semester_combo.findData(selected)
            if idx >= 0:
                self.semester_combo.setCurrentIndex(idx)

    def _refresh_semesters(self: Any) -> None:
        self.statusBar().showMessage("取得學期清單中...")
        self._run_worker(
            SemesterWorker(service_factory=self._service_factory),
            self._on_semester_finished,
            self._on_worker_failed,
        )

    def _on_semester_finished(self: Any, semesters: list[dict], selected: str) -> None:
        self.config["semesters"] = semesters
        if selected:
            self.config["selected_semester"] = selected
        self._save_config()
        self._load_semester_to_combo()
        self.statusBar().showMessage("學期清單已更新", 5000)

    def _load_schedules_to_table(self: Any) -> None:
        self.schedule_table.blockSignals(True)
        self.schedule_table.setRowCount(0)
        semester_options = self._build_schedule_semester_options()
        for item in self._get_schedules():
            row = self.schedule_table.rowCount()
            self.schedule_table.insertRow(row)

            enabled = QTableWidgetItem()
            enabled.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable)
            enabled.setCheckState(Qt.CheckState.Checked if item.enabled else Qt.CheckState.Unchecked)
            enabled.setData(Qt.ItemDataRole.UserRole, item.schedule_id)
            self.schedule_table.setItem(row, 0, enabled)
            name_item = QTableWidgetItem(item.name)
            name_item.setData(Qt.ItemDataRole.UserRole, item.schedule_id)
            name_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable | Qt.ItemFlag.ItemIsEditable)
            self.schedule_table.setItem(row, 1, name_item)

            time_edit = QTimeEdit()
            time_edit.setDisplayFormat("HH:mm")
            parsed_time = QTime.fromString(item.time, "HH:mm")
            time_edit.setTime(parsed_time if parsed_time.isValid() else QTime.currentTime())
            time_edit.setProperty("schedule_id", item.schedule_id)
            time_edit.timeChanged.connect(self._on_schedule_time_changed)
            self.schedule_table.setCellWidget(row, 2, time_edit)

            weekday_item = QTableWidgetItem(self._format_weekday_display(item.weekdays))
            weekday_item.setData(Qt.ItemDataRole.UserRole, item.schedule_id)
            weekday_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.schedule_table.setItem(row, 3, weekday_item)

            semester_combo = QComboBox()
            for label, value in semester_options:
                semester_combo.addItem(label, value)
            semester_idx = semester_combo.findData(item.semester)
            if semester_idx < 0:
                semester_combo.addItem(item.semester, item.semester)
                semester_idx = semester_combo.findData(item.semester)
            semester_combo.setCurrentIndex(semester_idx if semester_idx >= 0 else 0)
            semester_combo.setProperty("schedule_id", item.schedule_id)
            semester_combo.currentIndexChanged.connect(
                functools.partial(self._on_schedule_semester_changed, semester_combo)
            )
            self.schedule_table.setCellWidget(row, 4, semester_combo)

            last_run_item = QTableWidgetItem(item.last_run_date)
            last_run_item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.schedule_table.setItem(row, 5, last_run_item)
        self.schedule_table.blockSignals(False)

    def _get_schedules(self: Any) -> list[ScheduleItem]:
        return self.schedule_controller.get_schedules_from_config(self.config)

    def _save_schedules(self: Any, schedules: list[ScheduleItem]) -> None:
        self.schedule_controller.save_schedules_to_config(self.config, schedules)
        self._save_config()

    def _add_schedule(self: Any) -> None:
        weekdays = self._normalize_weekdays(self.selected_weekdays)
        if not weekdays:
            QMessageBox.warning(self, "設定錯誤", "至少要勾選一天。")
            return
        schedule = ScheduleItem(
            schedule_id=str(uuid.uuid4()),
            name=self.schedule_name.text().strip() or "未命名排程",
            time=self.schedule_time.time().toString("HH:mm"),
            weekdays=weekdays,
            semester=self.schedule_semester.currentData() or "__follow__",
        )
        schedules = self._get_schedules()
        schedules.append(schedule)
        self._save_schedules(schedules)
        self._load_schedules_to_table()

    def _remove_selected_schedule(self: Any) -> None:
        rows = self.schedule_table.selectionModel().selectedRows()
        if not rows:
            QMessageBox.information(self, "提示", "請先選取要移除的排程列。")
            return
        remove_ids: list[str] = []
        for idx in rows:
            item = self.schedule_table.item(idx.row(), 0)
            if item is None:
                continue
            schedule_id = item.data(Qt.ItemDataRole.UserRole)
            if isinstance(schedule_id, str) and schedule_id.strip() != "":
                remove_ids.append(schedule_id)
        schedules = [item for item in self._get_schedules() if item.schedule_id not in remove_ids]
        self._save_schedules(schedules)
        self._load_schedules_to_table()

    def _edit_schedule_weekdays(self: Any, schedule_id: str) -> None:
        schedules = self._get_schedules()
        target_schedule = next((item for item in schedules if item.schedule_id == schedule_id), None)
        if target_schedule is None:
            QMessageBox.warning(self, "錯誤", "找不到排程資料。")
            return

        dialog = WeekdaySelectDialog(target_schedule.weekdays, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        selected = dialog.get_selected_days()
        if len(selected) == 0:
            QMessageBox.warning(self, "設定錯誤", "至少要勾選一天。")
            return
        target_schedule.weekdays = self._normalize_weekdays(selected)
        self._save_schedules(schedules)
        self._load_schedules_to_table()

    def _on_schedule_item_changed(self: Any, item: QTableWidgetItem) -> None:
        if item.column() not in (0, 1):
            return
        schedule_id = item.data(Qt.ItemDataRole.UserRole)
        schedules = self._get_schedules()
        for schedule in schedules:
            if schedule.schedule_id == schedule_id:
                if item.column() == 0:
                    schedule.enabled = item.checkState() == Qt.CheckState.Checked
                elif item.column() == 1:
                    schedule.name = item.text().strip() or "未命名排程"
        self._save_schedules(schedules)

    def _on_schedule_table_double_click(self: Any, row: int, column: int) -> None:
        if column != 3:
            return
        weekday_item = self.schedule_table.item(row, 3)
        if weekday_item is None:
            return
        schedule_id = weekday_item.data(Qt.ItemDataRole.UserRole)
        if not schedule_id:
            return
        self._edit_schedule_weekdays(schedule_id)

    def _on_schedule_time_changed(self: Any, qtime: QTime) -> None:
        sender = self.sender()
        if sender is None:
            return
        schedule_id = sender.property("schedule_id")
        if not schedule_id:
            return
        schedules = self._get_schedules()
        for schedule in schedules:
            if schedule.schedule_id == schedule_id:
                schedule.time = qtime.toString("HH:mm")
                break
        self._save_schedules(schedules)

    def _on_schedule_semester_changed(self: Any, combo: QComboBox, _index: int) -> None:
        schedule_id = combo.property("schedule_id")
        if not schedule_id:
            return
        semester_value = combo.currentData() or ""
        schedules = self._get_schedules()
        for schedule in schedules:
            if schedule.schedule_id == schedule_id:
                schedule.semester = semester_value
                break
        self._save_schedules(schedules)

    def _build_schedule_semester_options(self: Any) -> list[tuple[str, str]]:
        return self.schedule_controller.build_schedule_semester_options(self.config)

    def _on_scheduler_tick(self: Any) -> None:
        now = datetime.now()
        schedules = self._get_schedules()
        follow_semester = self.semester_combo.currentData() or ""
        due_semesters, has_schedule_state_update = self.schedule_controller.collect_due_semesters(
            schedules=schedules,
            now=now,
            follow_semester=follow_semester,
        )

        if has_schedule_state_update:
            self._save_schedules(schedules)
            self._load_schedules_to_table()
        if len(due_semesters) == 0:
            return

        for semester in due_semesters:
            self.check_flow_controller.enqueue({
                "type": "schedule",
                "semester": semester,
            })
        if not self.service_boot_ready:
            self.statusBar().showMessage(
                f"ScholarshipService 啟動中，{len(due_semesters)} 筆排程已加入等待佇列",
                5000,
            )
            return
        self._update_check_ipc_queue_ahead()
        self._drain_pending_check_queue()

    def _open_weekday_dialog(self: Any) -> None:
        dialog = WeekdaySelectDialog(self.selected_weekdays, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        selected = dialog.get_selected_days()
        if len(selected) == 0:
            QMessageBox.warning(self, "設定錯誤", "至少要勾選一天。")
            return
        self.selected_weekdays = selected
        self.weekday_display_label.setText(self._format_weekday_display(selected))

    def _normalize_weekdays(self: Any, weekdays: list[int] | list[str]) -> list[int]:
        return self.schedule_controller.normalize_weekdays(weekdays)

    def _format_weekday_display(self: Any, weekdays: list[int] | list[str]) -> str:
        return self.schedule_controller.format_weekday_display(weekdays)

    def _resolve_semester(self: Any, semester: str) -> str:
        return self.schedule_controller.resolve_semester(
            semester,
            self.semester_combo.currentData() or "",
        )

    def _extract_last_run_date(self: Any, value: str) -> str:
        return self.schedule_controller.extract_last_run_date(value)

    def _check_now(self: Any) -> None:
        if not self.service_boot_ready:
            self.statusBar().showMessage("ScholarshipService 啟動中，暫時無法立即檢查", 5000)
            return
        semester = self.semester_combo.currentData() or ""
        self.config["selected_semester"] = semester
        self._save_config()
        self.check_flow_controller.begin_manual_context(semester)
        self._start_check(semester)

    def _start_check(self: Any, semester: str) -> None:
        if not self.check_flow_controller.can_start_now(self.service_boot_ready):
            return
        self.check_flow_controller.mark_started()
        self.check_now_btn.setEnabled(False)
        self.check_progress_bar.setValue(0)
        self.check_progress_label.setText("準備檢查")
        self.statusBar().showMessage("檢查中，請稍候...")
        worker = CheckWorker(
            service_factory=self._service_factory,
            semester=semester,
            google_sheet_format=self._current_google_sheet_format_config(),
        )
        worker.progress.connect(self._on_check_progress)
        self._run_worker(worker, self._on_check_finished, self._on_worker_failed)

    def _on_check_progress(self: Any, value: int, message: str) -> None:
        progress = max(0, min(100, int(value)))
        text = str(message)
        self.check_progress_bar.setValue(progress)
        self.check_progress_label.setText(text)
        self._mark_current_check_context_progress(progress, text)

    def _mark_current_check_context_running(self: Any) -> None:
        self.check_queue_coordinator.mark_context_running(self.check_flow_controller.current_context())

    def _mark_current_check_context_progress(self: Any, progress: int, message: str) -> None:
        self.check_queue_coordinator.mark_context_progress(
            context=self.check_flow_controller.current_context(),
            progress=progress,
            message=message,
        )

    def _mark_current_check_context_finished(self: Any, result_dicts: list[dict]) -> None:
        context = self.check_flow_controller.clear_current_context() or {}
        self.check_queue_coordinator.mark_context_finished(context, result_dicts)

    def _mark_current_check_context_failed(self: Any, message: str) -> None:
        context = self.check_flow_controller.clear_current_context() or {}
        self.check_queue_coordinator.mark_context_failed(context, message)

    def _run_worker(self: Any, worker_obj: QObject, ok_handler, err_handler) -> None:
        self.worker_runner.run(worker_obj, ok_handler, err_handler)

    def _on_check_finished(self: Any, result_dicts: list[dict], semester: str) -> None:
        self.check_flow_controller.mark_finished()
        self.check_now_btn.setEnabled(self.service_boot_ready)
        self.check_progress_bar.setValue(100)
        self.check_progress_label.setText("檢查完成")
        self._mark_current_check_context_finished(result_dicts)
        self._render_results(result_dicts, semester)
        self.statusBar().showMessage("檢查完成", 5000)
        self._update_check_ipc_queue_ahead()
        self._drain_pending_check_queue()

    def _on_worker_failed(self: Any, message: str) -> None:
        self.check_flow_controller.mark_finished()
        self.check_now_btn.setEnabled(self.service_boot_ready)
        self.check_progress_label.setText("檢查失敗")
        self._mark_current_check_context_failed(message)
        self.statusBar().showMessage("執行失敗", 5000)
        QMessageBox.critical(self, "執行失敗", message)
        self._update_check_ipc_queue_ahead()
        self._drain_pending_check_queue()

    def _drain_pending_check_queue(self: Any) -> None:
        entry = self.check_flow_controller.dequeue_next_for_start(self.service_boot_ready)
        if entry is None:
            return
        semester = self._resolve_semester(str(entry.get("semester", "")).strip())
        entry["semester"] = semester
        self._mark_current_check_context_running()
        self._update_check_ipc_queue_ahead()
        self._start_check(semester)

    def _render_results(self: Any, results: list[dict], semester: str) -> None:
        payload = self.check_result_processor.build_payload(results, semester, datetime.now())
        self.history_store.append_entries(payload.get("history_entries", []))
        for notify_payload in payload.get("notifications", []):
            self._dispatch_notification_async(
                self._current_notifier_config(),
                title=str(notify_payload.get("title", "")),
                summary_text=str(notify_payload.get("summary_text", "")),
                patch_text=str(notify_payload.get("patch_text", "")),
            )
        self.diff_view.setPlainText(str(payload.get("diff_text", "")))
        self._load_history_table()
