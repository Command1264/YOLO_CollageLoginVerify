from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from pathlib import Path

import pandas as pd
from pygsheets import FormatType, HorizontalAlignment, Spreadsheet, Worksheet, ValueRenderOption

from UI.scholarship_table_processor import ScholarshipTableProcessor


class ScholarshipSheetClient:
    """Google Sheets gateway for scholarship synchronization and formatting."""

    def __init__(self, cache_dir: Path, table_processor: ScholarshipTableProcessor) -> None:
        self.cache_dir = cache_dir
        self.table_processor = table_processor

    def get_or_create_spreadsheet(self, gc, semester_value: str | None) -> Spreadsheet:
        if not semester_value or len(semester_value) != 4:
            raise RuntimeError("學期值無效，無法建立或讀取 Google 試算表")
        academic_year = f"{semester_value[:len(semester_value) - 1]}-{semester_value[-1]}"
        spreadsheet_name = f"{academic_year} 獎學金"
        query = "mimeType='application/vnd.google-apps.spreadsheet' and trashed = false"
        sheet_dict = gc.drive.list(q=query)
        matches = [entry for entry in sheet_dict if entry.get("name") == spreadsheet_name]
        if len(matches) == 0:
            return gc.create(spreadsheet_name)
        if len(matches) == 1:
            return gc.open_by_key(matches[0]["id"])
        raise RuntimeError("存在多個相同名稱 Google 試算表，請先整理")

    def load_cloud_sheet(
        self,
        spreadsheet: Spreadsheet,
        sheet_title: str,
    ) -> tuple[Worksheet | None, pd.DataFrame | None, pd.DataFrame | None]:
        if sheet_title not in [ws.title for ws in spreadsheet.worksheets()]:
            return None, None, None
        worksheet = spreadsheet.worksheet_by_title(sheet_title)
        cloud_df = worksheet.get_as_df(value_render=ValueRenderOption.FORMULA)
        if cloud_df is None:
            return worksheet, None, None
        raw_cloud_df = cloud_df.copy()
        cloud_df = self.table_processor.normalize_cloud_df(cloud_df)
        return worksheet, self.table_processor.normalize_df(cloud_df), self.table_processor.normalize_df(raw_cloud_df)

    def sync_cloud_sheet(
        self,
        spreadsheet: Spreadsheet,
        worksheet: Worksheet | None,
        latest_df: pd.DataFrame,
        sheet_title: str,
        apply_format: bool = True,
        google_sheet_format: dict | None = None,
    ) -> bool:
        rows = max(latest_df.shape[0] + 1, 1)
        cols = max(latest_df.shape[1], 1)
        if worksheet is None:
            worksheet = spreadsheet.add_worksheet(title=sheet_title, rows=rows, cols=cols)
        else:
            worksheet.clear()
            worksheet.resize(rows=rows, cols=cols)
        worksheet.set_dataframe(latest_df, (1, 1), copy_head=True)
        style_cfg = google_sheet_format or {}
        if apply_format:
            style_ok = self.apply_google_sheet_format(
                worksheet,
                latest_df,
                style_cfg,
                sheet_title=sheet_title,
            )
            self._apply_semantic_number_formats(worksheet, latest_df, style_cfg, sheet_title=sheet_title)
            return style_ok
        self._apply_semantic_number_formats(worksheet, latest_df, {}, sheet_title=sheet_title)
        return True

    def apply_google_sheet_format(
        self,
        worksheet: Worksheet,
        latest_df: pd.DataFrame,
        format_cfg: dict,
        sheet_title: str | None = None,
    ) -> bool:
        rows = max(latest_df.shape[0] + 1, 1)
        cols = max(latest_df.shape[1], 1)
        if rows <= 0 or cols <= 0:
            return False

        font_size_raw = str(format_cfg.get("font_size", "")).strip()
        font_family = str(format_cfg.get("font_family", "")).strip()
        font_color_hex = str(format_cfg.get("font_color", "")).strip()
        width_mode = str(format_cfg.get("column_width_mode", "default")).strip() or "default"
        width_value = int(format_cfg.get("column_width_value", 120))
        min_width = int(format_cfg.get("column_min_width", 60))
        font_size = int(font_size_raw) if font_size_raw.isdigit() else None

        text_style_ok = self._apply_text_style(
            worksheet=worksheet,
            rows=rows,
            cols=cols,
            font_size=font_size,
            font_family=font_family,
            font_color_hex=font_color_hex,
        )
        column_width_ok = self._apply_column_width(
            worksheet=worksheet,
            latest_df=latest_df,
            cols=cols,
            width_mode=width_mode,
            width_value=width_value,
            min_width=min_width,
            font_size=font_size,
        )
        alignment_ok = self._apply_alignment_style(
            worksheet=worksheet,
            latest_df=latest_df,
            format_cfg=format_cfg,
            sheet_title=sheet_title,
            rows=rows,
            cols=cols,
        )
        return text_style_ok and column_width_ok and alignment_ok

    def has_google_sheet_style_update(self, format_cfg: dict) -> bool:
        font_size_raw = str(format_cfg.get("font_size", "")).strip()
        font_family = str(format_cfg.get("font_family", "")).strip()
        font_color = str(format_cfg.get("font_color", "")).strip()
        header_alignment = str(format_cfg.get("header_alignment", "center")).strip().lower()
        width_mode = str(format_cfg.get("column_width_mode", "default")).strip() or "default"
        min_width = int(format_cfg.get("column_min_width", 60))
        column_alignments = format_cfg.get("column_alignments", {})
        has_width = width_mode != "default"
        has_min_width = width_mode == "auto" and min_width != 60
        has_alignment = header_alignment in {"left", "center", "right"} and isinstance(column_alignments, dict)
        return bool(font_size_raw or font_family or font_color or has_width or has_min_width or has_alignment)

    def resolve_google_sheet_format_apply_mode(self, format_cfg: dict) -> str:
        mode = str(format_cfg.get("apply_mode", "on_change")).strip().lower()
        if mode not in {"always", "first_time", "on_change"}:
            return "on_change"
        return mode

    def should_apply_google_sheet_format(
        self,
        mode: str,
        content_changed: bool,
        first_time: bool,
        style_changed: bool,
    ) -> bool:
        if mode == "always":
            return True
        if mode == "first_time":
            return first_time
        return content_changed or style_changed

    def build_style_state_key(self, dataset_name: str, semester_value: str | None) -> str:
        safe_name = dataset_name.replace("/", "_")
        safe_semester = semester_value if semester_value else "current"
        return f"{safe_name}_{safe_semester}"

    def calc_style_config_hash(self, format_cfg: dict) -> str:
        normalized_alignments = {
            dataset: dict(mapping)
            for dataset, mapping in self._default_google_sheet_column_alignments().items()
        }
        raw_alignments = format_cfg.get("column_alignments", {})
        if isinstance(raw_alignments, dict):
            for dataset_name in list(normalized_alignments.keys()):
                dataset_raw = raw_alignments.get(dataset_name, {})
                if not isinstance(dataset_raw, dict):
                    continue

                ordered_keys: list[str] = []
                for column_name in dataset_raw.keys():
                    if column_name not in ordered_keys:
                        ordered_keys.append(column_name)
                for column_name in normalized_alignments[dataset_name].keys():
                    if column_name not in ordered_keys:
                        ordered_keys.append(column_name)

                normalized_dataset: dict[str, str] = {}
                for column_name in ordered_keys:
                    default_alignment = normalized_alignments[dataset_name].get(column_name, "center")
                    value = str(dataset_raw.get(column_name, default_alignment)).strip().lower()
                    if value not in {"left", "center", "right"}:
                        value = default_alignment
                    normalized_dataset[column_name] = value
                normalized_alignments[dataset_name] = normalized_dataset

        style_payload = {
            "font_size": str(format_cfg.get("font_size", "")).strip(),
            "font_family": str(format_cfg.get("font_family", "")).strip(),
            "font_color": str(format_cfg.get("font_color", "")).strip(),
            "header_alignment": str(format_cfg.get("header_alignment", "center")).strip().lower() or "center",
            "column_width_mode": str(format_cfg.get("column_width_mode", "default")).strip() or "default",
            "column_width_value": int(format_cfg.get("column_width_value", 120)),
            "column_min_width": int(format_cfg.get("column_min_width", 60)),
            "apply_mode": str(format_cfg.get("apply_mode", "on_change")).strip() or "on_change",
            "column_alignments": normalized_alignments,
        }
        raw = json.dumps(style_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def is_style_changed(self, state_key: str, style_hash: str) -> bool:
        state = self._load_style_state()
        return state.get(state_key, "") != style_hash

    def mark_style_applied(self, state_key: str, style_hash: str) -> None:
        state = self._load_style_state()
        state[state_key] = style_hash
        self._save_style_state(state)

    def _apply_text_style(
        self,
        worksheet: Worksheet,
        rows: int,
        cols: int,
        font_size: int | None,
        font_family: str,
        font_color_hex: str,
    ) -> bool:
        if font_size is None and font_family == "" and font_color_hex == "":
            return True
        sheet_id = self._get_sheet_id(worksheet)
        if sheet_id is None:
            return False
        text_format: dict = {}
        fields: list[str] = []
        if font_size is not None:
            text_format["fontSize"] = font_size
            fields.append("userEnteredFormat.textFormat.fontSize")
        if font_family:
            text_format["fontFamily"] = font_family
            fields.append("userEnteredFormat.textFormat.fontFamily")
        rgb = self._hex_to_google_color(font_color_hex)
        if rgb is not None:
            text_format["foregroundColor"] = rgb
            fields.append("userEnteredFormat.textFormat.foregroundColor")
        if len(text_format) == 0:
            return True
        requests = [
            {
                "repeatCell": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 0,
                        "endRowIndex": rows,
                        "startColumnIndex": 0,
                        "endColumnIndex": cols,
                    },
                    "cell": {"userEnteredFormat": {"textFormat": text_format}},
                    "fields": ",".join(fields),
                }
            }
        ]
        return self._send_batch_update_requests(worksheet, requests)

    def _apply_alignment_style(
        self,
        worksheet: Worksheet,
        latest_df: pd.DataFrame,
        format_cfg: dict,
        sheet_title: str | None,
        rows: int,
        cols: int,
    ) -> bool:
        if rows <= 0 or cols <= 0:
            return True
        sheet_id = self._get_sheet_id(worksheet)
        if sheet_id is None:
            return False
        requests: list[dict] = []
        font_size, font_family, font_rgb = self._resolve_text_style_from_format_cfg(format_cfg)
        header_alignment = self._resolve_alignment_value(
            str(format_cfg.get("header_alignment", "center")).strip().lower()
        )
        if header_alignment is not None:
            requests.append(
                self._build_repeat_cell_request(
                    sheet_id=sheet_id,
                    start_row=0,
                    end_row=1,
                    start_col=0,
                    end_col=cols,
                    horizontal_alignment=header_alignment.value,
                    font_size=font_size,
                    font_family=font_family,
                    font_rgb=font_rgb,
                )
            )

        if rows <= 1 or sheet_title is None:
            return self._send_batch_update_requests(worksheet, requests)
        dataset_column_alignments = self._resolve_dataset_column_alignments(format_cfg, sheet_title)
        for column_name, align_value in dataset_column_alignments.items():
            if column_name not in latest_df.columns:
                continue
            alignment = self._resolve_alignment_value(align_value)
            if alignment is None:
                continue
            col_loc = latest_df.columns.get_loc(column_name)
            if not isinstance(col_loc, int):
                continue
            col_idx = col_loc + 1
            requests.append(
                self._build_repeat_cell_request(
                    sheet_id=sheet_id,
                    start_row=1,
                    end_row=rows,
                    start_col=col_idx - 1,
                    end_col=col_idx,
                    horizontal_alignment=alignment.value,
                    font_size=font_size,
                    font_family=font_family,
                    font_rgb=font_rgb,
                )
            )
        return self._send_batch_update_requests(worksheet, requests)

    def _resolve_text_style_from_format_cfg(self, format_cfg: dict) -> tuple[int | None, str, dict | None]:
        font_size_raw = str(format_cfg.get("font_size", "")).strip()
        font_family = str(format_cfg.get("font_family", "")).strip()
        font_color_hex = str(format_cfg.get("font_color", "")).strip()
        font_size = int(font_size_raw) if font_size_raw.isdigit() else None
        font_rgb = self._hex_to_google_color(font_color_hex)
        return font_size, font_family, font_rgb

    def _resolve_alignment_value(self, value: str) -> HorizontalAlignment | None:
        mapping = {
            "left": HorizontalAlignment.LEFT,
            "center": HorizontalAlignment.CENTER,
            "right": HorizontalAlignment.RIGHT,
        }
        return mapping.get(str(value).strip().lower())

    def _default_google_sheet_column_alignments(self) -> dict[str, dict[str, str]]:
        return {
            "校內外獎助學金": {
                "學年": "center",
                "學期": "center",
                "類型": "center",
                "編號-獎學金名稱": "left",
                "外部連結": "center",
                "申請期限": "center",
                "金額": "right",
            },
            "個人申請結果": {
                "學年": "center",
                "學期": "center",
                "申請項目": "left",
                "申請結果": "center",
                "獲獎金額": "right",
                "領獎方式": "center",
                "領獎進度": "left",
            },
        }

    def _resolve_dataset_column_alignments(self, format_cfg: dict, sheet_title: str) -> dict[str, str]:
        defaults = self._default_google_sheet_column_alignments()
        default_map = defaults.get(sheet_title, {})
        raw_map = format_cfg.get("column_alignments", {})
        if not isinstance(raw_map, dict):
            return dict(default_map)
        dataset_raw = raw_map.get(sheet_title, {})
        if not isinstance(dataset_raw, dict):
            return dict(default_map)

        ordered_columns: list[str] = []
        for column_name in dataset_raw.keys():
            if column_name not in ordered_columns:
                ordered_columns.append(column_name)
        for column_name in default_map.keys():
            if column_name not in ordered_columns:
                ordered_columns.append(column_name)

        merged: dict[str, str] = {}
        for column_name in ordered_columns:
            default_alignment = default_map.get(column_name, "center")
            value = str(dataset_raw.get(column_name, default_alignment)).strip().lower()
            if value not in {"left", "center", "right"}:
                value = default_alignment
            merged[column_name] = value
        return merged

    def _apply_column_width(
        self,
        worksheet: Worksheet,
        latest_df: pd.DataFrame,
        cols: int,
        width_mode: str,
        width_value: int,
        min_width: int,
        font_size: int | None,
    ) -> bool:
        if width_mode == "default":
            return True
        sheet_id = self._get_sheet_id(worksheet)
        if sheet_id is None:
            return False
        requests: list[dict] = []
        if width_mode == "fixed":
            pixel_size = max(40, min(int(width_value), 1000))
            requests.append(
                {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": 0,
                            "endIndex": cols,
                        },
                        "properties": {"pixelSize": pixel_size},
                        "fields": "pixelSize",
                    }
                }
            )
            return self._send_batch_update_requests(worksheet, requests)
        if width_mode != "auto":
            return True

        effective_font_size = font_size if font_size is not None else 16
        width_coeff = 0.70
        min_pixel_size = max(20, min(int(min_width), 1000))
        for col_idx in range(cols):
            width_units = self._calc_column_width_units(latest_df, col_idx)
            if width_units <= 0:
                continue
            pixel_size = int(width_units * effective_font_size * width_coeff)
            pixel_size = max(pixel_size, min_pixel_size)
            requests.append(
                {
                    "updateDimensionProperties": {
                        "range": {
                            "sheetId": sheet_id,
                            "dimension": "COLUMNS",
                            "startIndex": col_idx,
                            "endIndex": col_idx + 1,
                        },
                        "properties": {"pixelSize": pixel_size},
                        "fields": "pixelSize",
                    }
                }
            )
        return self._send_batch_update_requests(worksheet, requests)

    def _calc_column_width_units(self, data_frame: pd.DataFrame, col_idx: int) -> int:
        if data_frame.shape[1] <= col_idx:
            return 0
        col_name = str(data_frame.columns[col_idx])
        values = [col_name] + [self._extract_display_text_for_width(item) for item in data_frame.iloc[:, col_idx].tolist()]
        widths = [self._calc_display_width(item) for item in values]
        return int(max(widths)) if len(widths) != 0 else 0

    def _apply_semantic_number_formats(
        self,
        worksheet: Worksheet,
        latest_df: pd.DataFrame,
        style_cfg: dict | None = None,
        sheet_title: str | None = None,
    ) -> None:
        rows = max(latest_df.shape[0] + 1, 1)
        if rows <= 1:
            return
        sheet_id = self._get_sheet_id(worksheet)
        if sheet_id is None:
            return
        format_cfg = style_cfg or {}
        font_size, font_family, font_rgb = self._resolve_text_style_from_format_cfg(format_cfg)
        dataset_alignments = {}
        if sheet_title is not None:
            dataset_alignments = self._resolve_dataset_column_alignments(format_cfg, sheet_title)
        requests: list[dict] = []

        for column_name, format_type, pattern in [
            ("申請期限", FormatType.DATE, "yyyy/MM/dd"),
            ("金額", FormatType.NUMBER, "#,##0"),
            ("獲獎金額", FormatType.NUMBER, "#,##0"),
        ]:
            if column_name not in latest_df.columns:
                continue
            col_loc = latest_df.columns.get_loc(column_name)
            if not isinstance(col_loc, int):
                continue
            col_idx = col_loc + 1
            number_type = "DATE" if format_type == FormatType.DATE else "NUMBER"
            align_value = dataset_alignments.get(column_name, "")
            alignment = self._resolve_alignment_value(str(align_value))
            requests.append(
                self._build_repeat_cell_request(
                    sheet_id=sheet_id,
                    start_row=1,
                    end_row=rows,
                    start_col=col_idx - 1,
                    end_col=col_idx,
                    number_format={"type": number_type, "pattern": pattern},
                    horizontal_alignment=alignment.value if alignment is not None else None,
                    font_size=font_size,
                    font_family=font_family,
                    font_rgb=font_rgb,
                )
            )
        self._send_batch_update_requests(worksheet, requests)

    def _build_repeat_cell_request(
        self,
        sheet_id: int,
        start_row: int,
        end_row: int,
        start_col: int,
        end_col: int,
        number_format: dict | None = None,
        horizontal_alignment: str | None = None,
        font_size: int | None = None,
        font_family: str = "",
        font_rgb: dict | None = None,
    ) -> dict:
        user_entered_format: dict = {}
        fields: list[str] = []
        if number_format is not None:
            user_entered_format["numberFormat"] = number_format
            fields.append("userEnteredFormat.numberFormat")
        if horizontal_alignment is not None:
            user_entered_format["horizontalAlignment"] = horizontal_alignment
            fields.append("userEnteredFormat.horizontalAlignment")

        text_format: dict = {}
        if font_size is not None:
            text_format["fontSize"] = font_size
            fields.append("userEnteredFormat.textFormat.fontSize")
        if font_family:
            text_format["fontFamily"] = font_family
            fields.append("userEnteredFormat.textFormat.fontFamily")
        if font_rgb is not None:
            text_format["foregroundColor"] = font_rgb
            fields.append("userEnteredFormat.textFormat.foregroundColor")
        if len(text_format) != 0:
            user_entered_format["textFormat"] = text_format

        if len(fields) == 0:
            fields = ["userEnteredFormat"]
        return {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": start_row,
                    "endRowIndex": end_row,
                    "startColumnIndex": start_col,
                    "endColumnIndex": end_col,
                },
                "cell": {"userEnteredFormat": user_entered_format},
                "fields": ",".join(fields),
            }
        }

    def _get_sheet_id(self, worksheet: Worksheet) -> int | None:
        try:
            return int(worksheet.id)
        except Exception:
            return None

    def _send_batch_update_requests(self, worksheet: Worksheet, requests: list[dict]) -> bool:
        if len(requests) == 0:
            return True
        try:
            worksheet.client.sheet.batch_update(worksheet.spreadsheet.id, requests)
            return True
        except Exception:
            return False

    def _calc_display_width(self, text: str) -> int:
        return sum(2 if unicodedata.east_asian_width(char) in "FWA" else 1 for char in str(text))

    def _extract_display_text_for_width(self, value) -> str:
        text = str(value).strip()
        hyperlink_pattern = re.compile(
            r'^\s*=\s*HYPERLINK\(\s*"[^"]*"\s*,\s*"(?P<label>(?:[^"]|"")*)"\s*\)\s*$',
            flags=re.IGNORECASE,
        )
        match = hyperlink_pattern.match(text)
        if match is None:
            return text
        label = match.group("label")
        return label.replace('""', '"')

    def _hex_to_google_color(self, color_hex: str) -> dict | None:
        text = color_hex.strip().lstrip("#")
        if len(text) != 6:
            return None
        try:
            red = int(text[0:2], 16) / 255.0
            green = int(text[2:4], 16) / 255.0
            blue = int(text[4:6], 16) / 255.0
        except ValueError:
            return None
        return {"red": red, "green": green, "blue": blue}

    def _style_state_file(self) -> Path:
        return self.cache_dir / "google_sheet_style_state.json"

    def _load_style_state(self) -> dict[str, str]:
        path = self._style_state_file()
        if not path.exists():
            return {}
        try:
            with path.open("r", encoding="utf-8") as file:
                raw = json.load(file)
            if not isinstance(raw, dict):
                return {}
            return {str(key): str(value) for key, value in raw.items()}
        except Exception:
            return {}

    def _save_style_state(self, state: dict[str, str]) -> None:
        path = self._style_state_file()
        with path.open("w", encoding="utf-8") as file:
            json.dump(state, file, ensure_ascii=False, indent=2)
