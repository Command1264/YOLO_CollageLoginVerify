from typing import Any

from pygsheets import FormatType, HorizontalAlignment


class SheetNumberFormat:
    format_type: FormatType
    pattern: str

    def __init__(self, format_type: FormatType, pattern: str,):
        self.format_type = format_type
        self.pattern = pattern


class SheetCellFormat:
    format_range: str
    text_format: dict[str, Any]
    horizontal_alignment: HorizontalAlignment
    number_format: SheetNumberFormat

    def __init__(
            self,
            format_range: str,
            text_format: dict[str, Any] = None,
            horizontal_alignment: HorizontalAlignment = None,
            number_format: SheetNumberFormat = None,
    ):
        self.format_range = format_range
        self.text_format = text_format
        self.horizontal_alignment = horizontal_alignment
        self.number_format = number_format

class GoogleSheetFormat:
    column_width: list[int]
    font_size: int
    formats: list[SheetCellFormat]

    def __init__(
        self,
        column_width: list[int],
        font_size: int,
        formats: list[SheetCellFormat],
    ):
        self.column_width = column_width
        self.font_size = font_size
        self.formats = formats