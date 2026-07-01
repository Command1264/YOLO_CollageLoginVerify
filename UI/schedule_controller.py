from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime


@dataclass
class ScheduleItem:
    """Schedule configuration item."""

    schedule_id: str
    name: str
    time: str
    weekdays: list[int]
    semester: str
    enabled: bool = True
    last_run_date: str = ""


class ScheduleController:
    """Handle schedule model normalization and tick evaluation."""

    def get_schedules_from_config(self, config: dict) -> list[ScheduleItem]:
        """Load schedules from config and normalize weekdays.

        Args:
            config (dict): Application config dict.

        Returns:
            list[ScheduleItem]: Parsed schedule list.
        """
        schedules: list[ScheduleItem] = []
        for raw in config.get("schedules", []):
            item = ScheduleItem(**raw)
            item.weekdays = self.normalize_weekdays(item.weekdays)
            schedules.append(item)
        return schedules

    def save_schedules_to_config(self, config: dict, schedules: list[ScheduleItem]) -> None:
        """Save schedules back to config dict.

        Args:
            config (dict): Application config dict.
            schedules (list[ScheduleItem]): Schedule list.
        """
        for item in schedules:
            item.weekdays = self.normalize_weekdays(item.weekdays)
        config["schedules"] = [asdict(item) for item in schedules]

    def build_schedule_semester_options(self, config: dict) -> list[tuple[str, str]]:
        """Build semester options for schedule combo box.

        Args:
            config (dict): Application config dict.

        Returns:
            list[tuple[str, str]]: (label, value) pairs.
        """
        options: list[tuple[str, str]] = [("跟隨主控台選擇", "__follow__")]
        for item in config.get("semesters", []):
            label = item.get("label", item.get("value", ""))
            value = item.get("value", "")
            if value:
                options.append((label, value))
        return options

    def normalize_weekdays(self, weekdays: list[int] | list[str]) -> list[int]:
        """Normalize weekday values to sorted unique integers (1-7)."""
        normalized: list[int] = []
        for raw in weekdays:
            try:
                value = int(raw)
            except (TypeError, ValueError):
                continue
            if 1 <= value <= 7:
                normalized.append(value)
        return sorted(set(normalized))

    def format_weekday_display(self, weekdays: list[int] | list[str]) -> str:
        """Format weekday list to display text."""
        normalized = self.normalize_weekdays(weekdays)
        day_set = set(normalized)
        if day_set == {1, 2, 3, 4, 5, 6, 7}:
            return "每天"
        if day_set == {1, 2, 3, 4, 5}:
            return "工作日"
        if day_set == {6, 7}:
            return "假日"
        day_names = {
            1: "星期一",
            2: "星期二",
            3: "星期三",
            4: "星期四",
            5: "星期五",
            6: "星期六",
            7: "星期日",
        }
        return "、".join([day_names[item] for item in normalized if item in day_names])

    def resolve_semester(self, semester: str, follow_semester: str) -> str:
        """Resolve schedule semester, following dashboard when requested."""
        if semester == "__follow__":
            return follow_semester
        return semester

    def extract_last_run_date(self, value: str) -> str:
        """Extract date part from last run datetime string."""
        text = str(value or "").strip()
        if text == "":
            return ""
        for fmt in ("%Y/%m/%d %H:%M:%S", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(text, fmt).date().isoformat()
            except ValueError:
                continue
        return ""

    def collect_due_semesters(
        self,
        schedules: list[ScheduleItem],
        now: datetime,
        follow_semester: str,
    ) -> tuple[list[str], bool]:
        """Collect due semesters and update matching schedule last_run_date.

        Args:
            schedules (list[ScheduleItem]): Schedule list.
            now (datetime): Current time.
            follow_semester (str): Dashboard selected semester.

        Returns:
            tuple[list[str], bool]: (due semesters, whether schedules were updated)
        """
        now_hhmm = now.strftime("%H:%M")
        today = now.date().isoformat()
        weekday = now.weekday() + 1
        due_semesters: list[str] = []
        has_schedule_state_update = False
        for schedule in schedules:
            if not schedule.enabled:
                continue
            if weekday not in schedule.weekdays:
                continue
            if schedule.time != now_hhmm:
                continue
            if self.extract_last_run_date(schedule.last_run_date) == today:
                continue
            semester = self.resolve_semester(schedule.semester, follow_semester)
            schedule.last_run_date = now.strftime("%Y/%m/%d %H:%M:%S")
            due_semesters.append(semester)
            has_schedule_state_update = True
        return due_semesters, has_schedule_state_update
