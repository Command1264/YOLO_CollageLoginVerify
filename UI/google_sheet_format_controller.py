from __future__ import annotations

from pathlib import Path


class GoogleSheetFormatController:
    """Handle Google Sheet format option normalization and alignment mapping."""

    def default_column_alignments(self) -> dict[str, dict[str, str]]:
        """Return default dataset column alignment map."""
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

    def build_font_family_options(self, available_fonts: list[str]) -> list[str]:
        """Build sorted font options with preferred fonts first."""
        preferred_fonts = [
            "Arial",
            "Calibri",
            "Times New Roman",
            "Cambria",
            "Georgia",
            "Verdana",
            "Tahoma",
            "Trebuchet MS",
            "Comic Sans MS",
            "Courier New",
            "Noto Sans TC",
            "Microsoft JhengHei",
            "PMingLiU",
            "MingLiU",
            "SimSun",
            "Roboto",
        ]
        available = set(available_fonts)
        ordered: list[str] = []
        for font_name in preferred_fonts:
            if font_name in ordered:
                continue
            ordered.append(font_name)
        remaining = sorted(
            [font_name for font_name in available if font_name not in ordered],
            key=str.casefold,
        )
        ordered.extend(remaining)
        return ordered

    def get_dataset_columns_from_cache(self, cache_dir: Path, dataset_name: str) -> list[str]:
        """Read cached dataset columns from latest cache file."""
        if not cache_dir.exists():
            return []
        files = sorted(cache_dir.glob(f"{dataset_name}_*.json"), key=lambda path: path.stat().st_mtime, reverse=True)
        for file_path in files:
            try:
                raw = self._read_json(file_path)
                if not isinstance(raw, list) or len(raw) == 0:
                    continue
                header_line = str(raw[0]).strip()
                if header_line == "":
                    continue
                columns = [item.strip() for item in header_line.split("|")]
                return [item for item in columns if item != ""]
            except Exception:
                continue
        return []

    def build_ordered_alignment_map(
        self,
        dataset_name: str,
        source_map: dict[str, str],
        dataset_columns: list[str],
    ) -> dict[str, str]:
        """Build ordered alignment map by cache columns and defaults."""
        defaults = self.default_column_alignments()
        default_map = defaults.get(dataset_name, {})
        ordered_keys: list[str] = []
        if len(dataset_columns) != 0:
            ordered_keys.extend(dataset_columns)
        for key in default_map.keys():
            if key not in ordered_keys:
                ordered_keys.append(key)

        result: dict[str, str] = {}
        for column_name in ordered_keys:
            default_alignment = default_map.get(column_name, "center")
            value = str(source_map.get(column_name, default_alignment)).strip().lower()
            if value not in {"left", "center", "right"}:
                value = default_alignment
            result[column_name] = value
        return result

    def normalize_column_alignments(self, cache_dir: Path, raw_value: object) -> dict[str, dict[str, str]]:
        """Normalize full column alignment config payload."""
        defaults = self.default_column_alignments()
        normalized: dict[str, dict[str, str]] = {}
        for dataset_name in defaults.keys():
            source_map = {}
            if isinstance(raw_value, dict):
                raw_dataset = raw_value.get(dataset_name, {})
                if isinstance(raw_dataset, dict):
                    source_map = raw_dataset
            dataset_columns = self.get_dataset_columns_from_cache(cache_dir, dataset_name)
            normalized[dataset_name] = self.build_ordered_alignment_map(
                dataset_name=dataset_name,
                source_map=source_map,
                dataset_columns=dataset_columns,
            )
        return normalized

    def _read_json(self, path: Path) -> dict | list:
        with path.open("r", encoding="utf-8") as file:
            import json
            return json.load(file)
