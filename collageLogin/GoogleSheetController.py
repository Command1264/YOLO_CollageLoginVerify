import pygsheets
from pygsheets import DataRange, HorizontalAlignment, FormatType, Worksheet, ValueRenderOption
from pygsheets.client import Client

import pandas as pd
from pandas import DataFrame

import re


class GoogleSheetController:
    def __init__(self):
        pass

    def __calculate_column_width(self, text):
        # 計算中文字符數
        chinese_char_count = len(re.findall(r'[\u4e00-\u9fff]', text))
        # 計算英文字符數
        non_chinese_char_count = len(text) - chinese_char_count
        # 假設英文字符寬度為 1，中文字符寬度為 2
        total_width = non_chinese_char_count * 1 + chinese_char_count * 2
        return total_width

    def __calculate_column_width_with_title(self, data_frame: DataFrame) -> int:
        if data_frame is None: return -1
        return int(data_frame.apply(self.__calculate_column_width).max())
