import warnings

import requests

import pandas as pd
import unicodedata, os, re
from dotenv import load_dotenv
from pandas import DataFrame
import numpy as np

from bs4 import BeautifulSoup

import datetime
from io import StringIO

from tqdm import tqdm

import pygsheets
from pygsheets import DataRange, HorizontalAlignment, FormatType, Worksheet, ValueRenderOption, Spreadsheet
from pygsheets.client import Client

from CYUTLogin import CYUTLogin
from GoogleClientAuth import GoogleClientAuth, CertificateNotEnabledException
from GoogleSheetCellFormat import GoogleSheetFormat, SheetCellFormat, SheetNumberFormat


def calculate_column_width(text):
    return sum(2 if unicodedata.east_asian_width(t) in "FWA" else 1 for t in str(text))


def calculate_column_width_with_title(data_frame: DataFrame) -> int:
    if data_frame is None: return -1
    return int(data_frame.apply(calculate_column_width).max())


class CYUTScholarships(CYUTLogin):
    log: bool = False

    __gc: Client

    @staticmethod
    def __get_class_name():
        return CYUTScholarships.__name__

    def check_certificate_enabled(self):
        """
        檢查 Google 憑證是否已啟用。

        參數: 無

        可能的例外:
        CertificateNotEnabledException: 如果憑證沒有正確啟用，則引發此例外。
        """
        if self.__gc is None:
            raise CertificateNotEnabledException("Google 憑證沒有被正確啟用！")

    def __init__(
            self,
            client_secret_file: str | None = None,
            token_file: str | None = None,
            log: bool = False
    ) -> None:
        super().__init__(log = log)
        if self.log: f"{self.__get_class_name()} __init__"
        if client_secret_file is None:
            client_secret_file = "./OAuthCredentials.json"

        # 載入區域環境變數
        load_dotenv()

        # 初始化
        self.log = log

        # 取得 Google OAuth 驗證
        gc_auth = GoogleClientAuth(client_secret_file, token_file)
        self.__gc = gc_auth.authorize_pygsheets()


    def load_scholarships(self) -> (bool, bool):
        self.check_certificate_enabled()

        if self.log: print(f"{self.__get_class_name()} load_scholarships")

        if not self.login_success: return False, False

        url = f"{self.system_domain}/ST0075/"
        response = requests.get(
            url,
            headers = self.headers,
            cookies = self.cookies,
            allow_redirects = False,
        )
        if response.status_code != 200: return False, False

        # 讀取網頁的 html，並將其轉成 BS4 物件
        html_bs = BeautifulSoup(response.text, "html.parser")
        # 讀取獎助學金的資料部分
        scholarships_table = html_bs.select("#contentTable")
        scholarships_table_str = str(scholarships_table)

        academic_year_select = html_bs.find("select", {
            "id": "acy",
            "name": "acy",
        })
        academic_year_option = academic_year_select.find("option", {
            "selected": "selected",
        })

        academic_year_value = academic_year_option["value"]
        spreadsheet = self.__get_create_google_spreadsheet(academic_year_value)

        # 將主資料表獨立出來
        # 並做一些資料預處理
        general_table_df = pd.read_html(
            StringIO(scholarships_table_str)
        )[0].drop(columns = ["Unnamed: 0", "名額"])
        general_table_df.insert(4, "外部連結", "LINK")
        general_table_df["類型"] = general_table_df["類型"].replace({
            "校外自行申請": "自申",
            "校外學校彙整": "校彙"
        })
        general_table_df["金額"] = general_table_df["金額"].replace({
            "待確定": "0"
        })
        general_table_df["申請期限"] = general_table_df["申請期限"].apply(
            lambda __x : __x.replace("-", "/")
        )

        # 根據編號進行排序
        general_table_df.sort_values(
            by = "編號-獎學金名稱",
            ascending = True,
            inplace = True
        )
        # 重新更新 index，必須在 sort 後面做，不然沒用
        general_table_df = general_table_df.reset_index(drop = True)
        # 創一個有 title 的 DataFrame，方便後面做事
        general_table_df_with_title = \
            pd.DataFrame(
                [general_table_df.columns.values.tolist()] + general_table_df.values.tolist()
            )

        # 先在這裡拿到各自 column 裡面最長字串的長度，不然超連結蓋過去就取不出來了
        general_table_df_max_length = [
            calculate_column_width_with_title(general_table_df_with_title.iloc[:, i]) if (3 <= i < 7) else 0 \
            for i in range(7)
        ]
        font_size = 16


        # 要在字數統計後，再將數值轉整數，不然無法統計數字
        general_table_df["金額"] = general_table_df["金額"].astype(dtype=np.int64)

        # 取得超連結，並將其想入 DataFrame
        for i, name in tqdm(enumerate(general_table_df.iloc[:, 3]),
                            desc="run google sheet hyperlink",
                            total=general_table_df.shape[0]):
            split_name = name.split("-", 1)
            if len(split_name) != 2:
                continue

            sub_html = html_bs.select(f"#tr_{split_name[0]}")
            if not sub_html:
                continue

            sub_df_lst = pd.read_html(StringIO(str(sub_html)))
            if len(sub_df_lst) != 1:
                continue
            sub_df = sub_df_lst[0].iloc[8:10, 0:2].dropna()

            for j in range(0, sub_df.shape[0]):
                link = sub_df.iloc[j, 1]
                if link and link.lower() != "nan":
                    text = f'=HYPERLINK("{link}", "{name if (j == 0) else "LINK"}")'
                    general_table_df.iloc[i, 3 + j] = text

        return self.__write_google_sheet(
            general_table_df,
            spreadsheet = spreadsheet,
            # general_table_df_max_length,
            sheet_format = GoogleSheetFormat(
                column_width = general_table_df_max_length,
                font_size = font_size,
                formats = [
                    SheetCellFormat(
                        format_range = "ALL",
                        text_format = {
                            "fontSize": font_size
                        },
                        horizontal_alignment = HorizontalAlignment.CENTER,
                    ),
                    SheetCellFormat(
                        format_range = "D2:D",
                        text_format = {
                            "fontSize": font_size
                        },
                        horizontal_alignment = HorizontalAlignment.LEFT,
                    ),
                    SheetCellFormat(
                        format_range = "G2:G",
                        text_format = {
                            "fontSize": font_size
                        },
                        horizontal_alignment = HorizontalAlignment.RIGHT,
                        number_format = SheetNumberFormat(
                            format_type = FormatType.NUMBER,
                            pattern = "#,##0",
                        ),
                    ),
                    SheetCellFormat(
                        format_range = "F2:F",
                        text_format = {
                            "fontSize": font_size
                        },
                        horizontal_alignment = HorizontalAlignment.CENTER,
                        number_format = SheetNumberFormat(
                            format_type = FormatType.DATE,
                            pattern = "yyyy/MM/dd",
                        ),
                    ),
                ]
            ),
            sheet_title = "校內外獎助學金"
        )

    def __check_google_sheet(
            self,
            table_df: DataFrame = None,
            spreadsheet: Spreadsheet | None = None,
            sheet_title: str = "學校資料",
    ) -> (bool, Worksheet | None):
        self.check_certificate_enabled()

        if self.log: print(f"{self.__get_class_name()} __check_google_sheet")

        if spreadsheet is None or table_df is None: return False, None
        # 將 index 預處理，避免出現忘記處理的事情
        table_df = table_df.reset_index(drop = True)


        # 連結 google sheet
        worksheet: Worksheet | None = None
        old_df: DataFrame | None = None

        # 如果資料表存在，就檢查資料是否有變動
        if sheet_title in [ws.title for ws in spreadsheet.worksheets()]:
            worksheet = spreadsheet.worksheet_by_title(sheet_title)
            # 使用公式的方式讀取出來，才能讀出 hyperlink，不然只有顯示文字
            old_df = worksheet.get_as_df(
                value_render = ValueRenderOption.FORMULA,
            )
            # 因為使用公式讀取的原因，所以日期需要從 excel 日期轉換成一般日期
            if old_df.get("申請期限") is not None:
                old_df["申請期限"] = old_df["申請期限"].apply(
                    # timedelta -2 是為了修復 Excel 的 bug
                    lambda __x : (datetime.datetime(1900, 1, 1) + datetime.timedelta(days=__x - 2)).strftime('%Y/%m/%d')
                )

        # 如果資料相同，那就不用上傳資料，避免浪費
        if not old_df is None:
            if old_df.equals(table_df): return False, worksheet

        return True, worksheet

    def __write_google_sheet(
            self,
            table_df: DataFrame,
            spreadsheet: Spreadsheet,
            sheet_format: GoogleSheetFormat,
            sheet_title: str = "學校資料"
    ) -> (bool, bool):
        self.check_certificate_enabled()

        if self.log: print(f"{self.__get_class_name()} __write_google_sheet")

        if spreadsheet is None:
            # if self.__spreadsheet is None:
            return False, False
            # spreadsheet = self.__spreadsheet

        need_update, worksheet = self.__check_google_sheet(
            table_df,
            spreadsheet = spreadsheet,
            sheet_title = sheet_title
        )
        if not need_update:
            return True, False

        # 格式化 Google Sheet
        rows = table_df.shape[0]
        cols = table_df.shape[1]
        # 如果 work_sheet 是 None，代表沒有創建過資料表
        if worksheet is None:
            # 創建 sheet
            worksheet = spreadsheet.add_worksheet(
                title = sheet_title,
                rows = rows,
                cols = cols,
            )
        else:
            # 清除內容並重新寫入
            worksheet.clear()
            worksheet.resize(
                rows = rows,
                cols = cols,
            )

        # 更新資料至 Google Sheet
        worksheet.set_dataframe(
            table_df,
            (1, 1),  # 從 A1 開始寫入
            copy_head = True  # 包含欄位名稱
        )


        x = 0.70
        font_size = 16 if sheet_format.font_size is None else sheet_format.font_size
        # 設定欄位寬度
        if sheet_format.column_width is not None:
            for i, width in enumerate(sheet_format.column_width):
                if width > 0:
                    # 因為 adjust_column_width 的初始位置為 1，所以需要加 1
                    worksheet.adjust_column_width(i + 1, pixel_size = int(width * font_size * x))

        def set_cells_format(start, end, worksheet, cell_format):
            data_range = DataRange(start = start, end = end, worksheet = worksheet)
            cell = pygsheets.Cell(start)

            if cell_format.text_format is not None:
                for key, value in cell_format.text_format.items():
                    cell.set_text_format(key, value)

            if cell_format.horizontal_alignment is not None:
                cell.set_horizontal_alignment(cell_format.horizontal_alignment)

            if cell_format.number_format is not None:
                number_format = cell_format.number_format
                cell.set_number_format(number_format.format_type, number_format.pattern)

            data_range.apply_format(cell)

        for cell_format in sheet_format.formats:
            # 先 upper，方便後續辨識
            cell_format.format_range = cell_format.format_range.upper()
            format_flag = False
            start, end = None, None

            # 對應到處理全部
            if cell_format.format_range == "ALL":
                start, end = f'A1', f'{chr(ord("A") + cols - 1)}{rows + 1}'
                format_flag = True

            # 對應到 A3:D10 或是 D2:D10 的場景
            elif re.fullmatch(r"[A-Z][0-9]+?:[A-Z][0-9]+", cell_format.format_range):
                start, end = cell_format.format_range.split(":")
                format_flag = True

            # 對應到 D:D10 或是 D2:D 的場景
            elif re.fullmatch(r"[A-Z](?:[0-9]+)?:[A-Z](?:[0-9]+)?", cell_format.format_range):
                start, end = cell_format.format_range.split(":")
                if re.fullmatch(r"[A-Z]+", start): start = start + "1"
                if re.fullmatch(r"[A-Z]+", end): end = end + str(rows + 1)
                format_flag = True
            else:
                warnings.warn(f"未知的範圍: {cell_format.format_range}")

            if format_flag:
                set_cells_format(start, end, worksheet, cell_format)

        return True, True


    def load_apply_scholarships(self) -> (bool, bool):
        self.check_certificate_enabled()

        if self.log: print(f"{self.__get_class_name()} load_apply_scholarships")
        if not self.login_success: return False

        url = f"{self.system_domain}/ST0075/Apply"
        response = requests.get(
            url,
            headers = self.headers,
            cookies = self.cookies,
            allow_redirects = False,
        )
        if response.status_code != 200: return False, False

        # 讀取網頁的 html，並將其轉成 BS4 物件
        html_bs = BeautifulSoup(response.text, "html.parser")
        # 讀取獎助學金的資料部分
        scholarships_table = html_bs.select("#contentTable")
        scholarships_table_str = str(scholarships_table)

        academic_year_select = html_bs.find("select", {
            "id": "acy",
            "name": "acy",
        })
        academic_year_option = academic_year_select.find("option", {
            "selected": "selected",
        })

        academic_year_value = academic_year_option["value"]
        spreadsheet = self.__get_create_google_spreadsheet(academic_year_value)

        # 將主資料表獨立出來
        # 並做一些資料預處理
        general_table_df = pd.read_html(
            StringIO(scholarships_table_str)
        )[0]

        # 根據編號進行排序
        general_table_df.sort_values(
            by = "申請項目",
            ascending = True,
            inplace = True
        )
        # 重新更新 index，必須在 sort 後面做，不然沒用
        general_table_df = general_table_df.reset_index(drop = True)
        # 創一個有 title 的 DataFrame，方便後面做事
        general_table_df_with_title = \
            pd.DataFrame(
                [general_table_df.columns.values.tolist()] + general_table_df.values.tolist()
            )

        general_table_df["獲獎金額"] = general_table_df["獲獎金額"].fillna("0")
        # 先在這裡拿到各自 column 裡面最長字串的長度，不然超連結蓋過去就取不出來了
        general_table_df_max_length = [
            calculate_column_width_with_title(general_table_df_with_title.iloc[:, i]) if (2 <= i < 7) else 0 \
            for i in range(7)
        ]
        font_size = 16


        # 要在字數統計後，再將數值轉整數，不然無法統計數字
        general_table_df["獲獎金額"] = general_table_df["獲獎金額"].astype(dtype = np.int64)

        return self.__write_google_sheet(
            general_table_df,
            spreadsheet = spreadsheet,
            # general_table_df_max_length,
            sheet_format = GoogleSheetFormat(
                column_width = general_table_df_max_length,
                font_size = font_size,
                formats = [
                    SheetCellFormat(
                        format_range = "ALL",
                        text_format = {
                            "fontSize": font_size
                        },
                        horizontal_alignment = HorizontalAlignment.CENTER,
                    ),
                    SheetCellFormat(
                        format_range = "C2:C",
                        text_format = {
                            "fontSize": font_size
                        },
                        horizontal_alignment = HorizontalAlignment.LEFT,
                    ),
                    SheetCellFormat(
                        format_range = "E2:E",
                        text_format = {
                            "fontSize": font_size
                        },
                        horizontal_alignment = HorizontalAlignment.RIGHT,
                        number_format = SheetNumberFormat(
                            format_type = FormatType.NUMBER,
                            pattern = "#,##0",
                        ),
                    ),
                ]
            ),
            sheet_title = "個人申請結果"
        )

    def delete_google_spreadsheet(
            self,
            spreadsheet: Spreadsheet
    ) -> bool:
        self.check_certificate_enabled()

        if self.log: print(f"{self.__get_class_name()} delete_google_spreadsheet")

        if spreadsheet is None:
            return False
        try:
            self.__gc.drive.delete(file_id = spreadsheet.id)
            return True
        except Exception as e:
            print(e)
            return False


    def __get_create_google_spreadsheet(
            self,
            academic_year_value: str,
            spread_sheet_name: str = "%academic_year% 獎學金"
    ) -> Spreadsheet:
        self.check_certificate_enabled()

        if self.log: print(f"{self.__get_class_name()} __get_create_google_spreadsheet")
        if len(academic_year_value) != 4:
            raise ValueError("選擇數值不是 4 位數")

        academic_year = f"{academic_year_value[:len(academic_year_value) - 1]}-{academic_year_value[-1]}"
        spread_sheet_name = spread_sheet_name.replace("%academic_year%", academic_year)

        query = "mimeType='application/vnd.google-apps.spreadsheet' and trashed = false"

        sheet_dict = self.__gc.drive.list(q = query)
        sheet_names = [file for file in sheet_dict if file["name"] == spread_sheet_name]

        # print(sheet_names)
        match len(sheet_names):
            case 0:
                spreadsheet = self.__gc.create(spread_sheet_name)
            case 1:
                spreadsheet = self.__gc.open_by_key(sheet_names[0]["id"])
            case _:
                raise FileExistsError("存在多個相同名稱 Google 表單，請檢查")

        if spreadsheet is None:
            raise FileNotFoundError("找不到 Google 表單")
        return spreadsheet

    def test(self):
        if self.log: print(f"{self.__get_class_name()} test")




if __name__ == "__main__":
    cyut_scholarships = CYUTScholarships(log = True)
    for title, (success, has_update) in [
        ["校內外獎助學金", cyut_scholarships.load_scholarships()],
        ["個人申請結果", cyut_scholarships.load_apply_scholarships()],
    ]:
        if success:
            if has_update:
                print(f"{title} 上傳成功!")
            else:
                print(f"{title} 沒有更新。")
        else:
            warnings.warn(f"{title} 上傳失敗！！！")