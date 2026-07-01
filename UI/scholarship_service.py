import hashlib
import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd
from bs4 import BeautifulSoup

from collageLogin.CYUTScholarships import CYUTScholarships
from UI.diff_patch import PatchSummary, build_patch
from UI.scholarship_sheet_client import ScholarshipSheetClient
from UI.scholarship_table_processor import ScholarshipTableProcessor
from UI.scholarship_web_client import ScholarshipWebClient
from utils.app_paths import get_cache_dir


@dataclass
class SemesterOption:
    value: str
    label: str
    selected: bool = False


@dataclass
class DataSetUpdate:
    name: str
    success: bool
    message: str
    summary: PatchSummary | None = None


class ScholarshipService:
    def __init__(self, config_dir: Path | None = None, log: bool = False) -> None:
        self.cache_dir = config_dir / ".cache" if config_dir else get_cache_dir()
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.log = log
        self.table_processor = ScholarshipTableProcessor()
        self.web_client = ScholarshipWebClient()
        self.sheet_client = ScholarshipSheetClient(
            cache_dir=self.cache_dir,
            table_processor=self.table_processor,
        )

    def get_semesters(self) -> tuple[list[SemesterOption], str | None]:
        client = CYUTScholarships(log=self.log)
        if not client.login_success:
            raise RuntimeError("登入失敗，無法取得學期清單")

        response = self.web_client.get_semester_page(client)
        if response.status_code != 200:
            raise RuntimeError(f"取得學期頁面失敗: {response.status_code}")

        soup = BeautifulSoup(response.text, "html.parser")
        select = soup.find("select", {"id": "acy", "name": "acy"})
        if not select:
            raise RuntimeError("找不到學期欄位（acy）")

        semesters: list[SemesterOption] = []
        selected_value = None
        for option in select.find_all("option"):
            value = str(option.get("value", "")).strip()
            label = option.text.strip()
            selected = option.has_attr("selected")
            if selected:
                selected_value = value
            semesters.append(SemesterOption(value=value, label=label, selected=selected))
        return semesters, selected_value

    def check_updates(
        self,
        semester_value: str | None,
        progress_callback=None,
        google_sheet_format: dict | None = None,
    ) -> list[DataSetUpdate]:
        self._emit_progress(progress_callback, 5, "初始化登入與 Google 連線")
        client = CYUTScholarships(log=self.log)
        if not client.login_success:
            return [DataSetUpdate(name="系統", success=False, message="登入失敗，請檢查帳號密碼與驗證碼模型")]
        if not semester_value:
            semester_value = self._get_default_semester(client)

        sheet_client = self._get_google_client(client)
        if sheet_client is None:
            return [DataSetUpdate(name="系統", success=False, message="Google 授權失敗，無法比對雲端資料")]
        spreadsheet = self.sheet_client.get_or_create_spreadsheet(sheet_client, semester_value)

        targets = [
            ("校內外獎助學金", "/ST0075/", "校內外獎助學金"),
            ("個人申請結果", "/ST0075/Apply", "個人申請結果"),
        ]
        results: list[DataSetUpdate] = []
        total_steps = max(len(targets) * 3, 1)
        current_step = 0

        for display_name, path, sheet_title in targets:
            try:
                current_step += 1
                self._emit_progress(
                    progress_callback,
                    10 + int(current_step / total_steps * 75),
                    f"抓取校務系統資料：{display_name}",
                )
                latest_df = self._fetch_table(client, path, semester_value, display_name)
                latest_lines = self._df_to_lines(latest_df)

                current_step += 1
                self._emit_progress(
                    progress_callback,
                    10 + int(current_step / total_steps * 75),
                    f"同步雲端資料：{display_name}",
                )
                worksheet, cloud_df, cloud_raw_df = self.sheet_client.load_cloud_sheet(spreadsheet, sheet_title)
                cloud_lines = self._df_to_lines(cloud_df) if cloud_df is not None else []
                cloud_hash = self._calc_lines_hash(cloud_lines)
                cloud_raw_lines = self._df_to_lines(self._normalize_df(cloud_raw_df)) if cloud_raw_df is not None else []
                cloud_raw_hash = self._calc_lines_hash(cloud_raw_lines)
                latest_hash = self._calc_lines_hash(latest_lines)
                has_style_update = self.sheet_client.has_google_sheet_style_update(google_sheet_format or {})
                format_apply_mode = self.sheet_client.resolve_google_sheet_format_apply_mode(google_sheet_format or {})
                style_state_key = self.sheet_client.build_style_state_key(display_name, semester_value)
                style_hash = self.sheet_client.calc_style_config_hash(google_sheet_format or {})
                style_changed = self.sheet_client.is_style_changed(style_state_key, style_hash)

                if cloud_hash == latest_hash:
                    if cloud_raw_hash != latest_hash:
                        summary = build_patch(cloud_lines, latest_lines, f"{display_name}-{semester_value or 'current'}")
                        should_apply = has_style_update and self.sheet_client.should_apply_google_sheet_format(
                            mode=format_apply_mode,
                            content_changed=True,
                            first_time=False,
                            style_changed=style_changed,
                        )
                        style_apply_ok = self.sheet_client.sync_cloud_sheet(
                            spreadsheet,
                            worksheet,
                            latest_df,
                            sheet_title,
                            apply_format=should_apply,
                            google_sheet_format=google_sheet_format,
                        )
                        if should_apply and style_apply_ok:
                            self.sheet_client.mark_style_applied(style_state_key, style_hash)
                        message = "雲端已校正資料格式"
                    else:
                        summary = build_patch(cloud_lines, latest_lines, f"{display_name}-{semester_value or 'current'}")
                        should_apply = self.sheet_client.should_apply_google_sheet_format(
                            mode=format_apply_mode,
                            content_changed=False,
                            first_time=False,
                            style_changed=style_changed,
                        )
                        if worksheet is not None and has_style_update and should_apply:
                            style_apply_ok = self.sheet_client.apply_google_sheet_format(
                                worksheet,
                                latest_df,
                                google_sheet_format or {},
                                sheet_title=sheet_title,
                            )
                            if style_apply_ok:
                                self.sheet_client.mark_style_applied(style_state_key, style_hash)
                        message = "沒有更新（已與雲端同步）"
                else:
                    summary = build_patch(cloud_lines, latest_lines, f"{display_name}-{semester_value or 'current'}")
                    first_time_create = worksheet is None
                    should_apply = has_style_update and self.sheet_client.should_apply_google_sheet_format(
                        mode=format_apply_mode,
                        content_changed=True,
                        first_time=first_time_create,
                        style_changed=style_changed,
                    )
                    style_apply_ok = self.sheet_client.sync_cloud_sheet(
                        spreadsheet,
                        worksheet,
                        latest_df,
                        sheet_title,
                        apply_format=should_apply,
                        google_sheet_format=google_sheet_format,
                    )
                    if should_apply and style_apply_ok:
                        self.sheet_client.mark_style_applied(style_state_key, style_hash)
                    message = f"雲端已同步：新增 {summary.added} 筆，刪除 {summary.removed} 筆"

                current_step += 1
                self._emit_progress(
                    progress_callback,
                    10 + int(current_step / total_steps * 75),
                    f"更新本地快取：{display_name}",
                )
                cache_key = self._build_cache_key(display_name, semester_value)
                self._save_cache(cache_key, latest_lines)

                results.append(DataSetUpdate(name=display_name, success=True, message=message, summary=summary))
            except Exception as exc:
                results.append(DataSetUpdate(name=display_name, success=False, message=f"檢查失敗: {exc}"))

        self._emit_progress(progress_callback, 95, "完成資料同步")
        return results

    def _fetch_table(
        self,
        client: CYUTScholarships,
        path: str,
        semester_value: str | None,
        dataset_name: str,
    ) -> pd.DataFrame:
        response = self._request_dataset_page(
            client=client,
            path=path,
            semester_value=semester_value,
        )
        if response.status_code != 200:
            raise RuntimeError(f"HTTP {response.status_code}")

        soup = BeautifulSoup(response.text, "html.parser")
        table_node = soup.select_one("#contentTable")
        if table_node is None:
            return pd.DataFrame(columns=["無資料"])

        table_df = self._safe_read_table_df(table_node)
        if dataset_name == "校內外獎助學金":
            table_df = self._preprocess_internal_external_table(table_df, soup)
        elif dataset_name == "個人申請結果":
            table_df = self._preprocess_apply_table(table_df)
        return self._normalize_df(table_df)

    def _request_dataset_page(
        self,
        client: CYUTScholarships,
        path: str,
        semester_value: str | None,
    ):
        return self.web_client.request_dataset_page(
            client=client,
            path=path,
            semester_value=semester_value,
        )

    def _safe_read_table_df(self, table_node) -> pd.DataFrame:
        return self.table_processor.safe_read_table_df(table_node)

    def _normalize_df(self, table_df: pd.DataFrame) -> pd.DataFrame:
        return self.table_processor.normalize_df(table_df)

    def _preprocess_internal_external_table(self, table_df: pd.DataFrame, soup: BeautifulSoup) -> pd.DataFrame:
        return self.table_processor.preprocess_internal_external_table(table_df, soup)

    def _preprocess_apply_table(self, table_df: pd.DataFrame) -> pd.DataFrame:
        return self.table_processor.preprocess_apply_table(table_df)

    def _df_to_lines(self, table_df: pd.DataFrame) -> list[str]:
        return self.table_processor.df_to_lines(table_df)

    def _get_google_client(self, client: CYUTScholarships):
        return getattr(client, "_CYUTScholarships__gc", None)

    def _get_default_semester(self, client: CYUTScholarships) -> str | None:
        return self.web_client.get_default_semester(client)

    def _build_cache_key(self, dataset_name: str, semester_value: str | None) -> str:
        safe_name = dataset_name.replace("/", "_")
        safe_semester = semester_value if semester_value else "current"
        return f"{safe_name}_{safe_semester}.json"

    def _load_cache(self, cache_key: str) -> list[str]:
        cache_file = self.cache_dir / cache_key
        if not cache_file.exists():
            return []
        with cache_file.open("r", encoding="utf-8") as file:
            return json.load(file)

    def _save_cache(self, cache_key: str, lines: list[str]) -> None:
        cache_file = self.cache_dir / cache_key
        with cache_file.open("w", encoding="utf-8") as file:
            json.dump(lines, file, ensure_ascii=False, indent=2)

    def _calc_lines_hash(self, lines: list[str]) -> str:
        raw = "\n".join(lines).encode("utf-8")
        return hashlib.sha256(raw).hexdigest()

    def _emit_progress(self, callback, value: int, message: str) -> None:
        if callback is None:
            return
        callback(max(0, min(value, 100)), message)
