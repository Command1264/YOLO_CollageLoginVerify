import requests

import pandas as pd
from pandas import DataFrame
import numpy as np

from bs4 import BeautifulSoup

import datetime
from io import StringIO
import re

from tqdm import tqdm

import pygsheets
from pygsheets import DataRange, HorizontalAlignment, FormatType, Worksheet, ValueRenderOption
from pygsheets.client import Client

from CYUTLogin import CYUTLogin


def calculate_column_width(text):
    # 計算中文字符數
    chinese_char_count = len(re.findall(r'[\u4e00-\u9fff]', text))
    # 計算英文字符數
    non_chinese_char_count = len(text) - chinese_char_count
    # 假設英文字符寬度為 1，中文字符寬度為 2
    total_width = non_chinese_char_count * 1 + chinese_char_count * 2
    return total_width


def calculate_column_width_with_title(data_frame: DataFrame) -> int:
    if data_frame is None: return -1
    return int(data_frame.apply(calculate_column_width).max())


class CYUTScholarships(CYUTLogin):
    __gc: Client | None = None
    __sheet_url: str | None = None
    __class_name: str = "CYUTScholarships"

    def __init__(
            self,
            service_file: str = "./yolocollageloginverify-c5d1a6096db6.json",
            sheet_url: str = "https://docs.google.com/spreadsheets/d/1N5ujLg2NE8JRJPXhGIDFXfSBRp_q0s0XFeDjIiJsp-w/edit?usp=sharing"
    ) -> None:
        super().__init__()

        if self.log: f"{self.__class_name} __init__"
        # 取得 google sheet 驗證
        self.__gc = pygsheets.authorize(service_file = service_file)
        self.__sheet_url = sheet_url

    def load_scholarships(self) -> bool:
        if self.log: print(f"{self.__class_name} load_scholarships")

        if not self.login_success: return False

        url = f"{self.system_domain}/ST0075/"
        response = requests.get(
            url,
            headers = self.headers,
            cookies = self.cookies,
            allow_redirects = False,
        )
        if response.status_code != 200: return False

        # 讀取網頁的 html，並將其轉成 BS4 物件
        html_bs = BeautifulSoup(response.text, "html.parser")
        # 讀取獎助學金的資料部分
        scholarships_table = html_bs.select("#contentTable")
        scholarships_table_str = str(scholarships_table)


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
            # by = ["申請期限", "編號-獎學金名稱"],
            # ascending = [True, True],
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
            calculate_column_width_with_title(general_table_df_with_title.iloc[:, i])
            for i in range(3, 7)
        ]

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
                if link and link != "nan":
                    text = f'=HYPERLINK("{link}", "{name if (j == 0) else "LINK"}")'
                    general_table_df.iloc[i, 3 + j] = text

        if self.__write_google_sheet(
                general_table_df,
                general_table_df_max_length,
                "testSheet"
        ):
            print("Updated successful!")
        else:
            print("No update")


        # work_sheet.range(f'D2:D{rows + 1}').apply_format(
        #     pygsheets.Cell('D2').set_horizontal_alignment("LEFT")
        # )
        # work_sheet.range(f'G2:G{rows + 1}').apply_format(
        #     pygsheets.Cell('G2').set_horizontal_alignment("RIGHT")
        # )

        # sheet = self.__gs.open_by_url(self.__sheet_url)

        # work_sheet_names = [ws.title for ws in sheet.worksheets()]
        # if "testSheet" in work_sheet_names:
        #     test_sheet = sheet.worksheet("testSheet")
        #     sheet.del_worksheet(test_sheet)
        #
        # work_sheet = sheet.add_worksheet(
        #     "testSheet",
        #     rows = general_table_df.shape[0],
        #     cols = general_table_df.shape[1]
        # )
        # work_sheet.update(
        #     [general_table_df.columns.values.tolist()] + general_table_df.values.tolist()
        # )
        #
        # update_cells_lst = []
        # # 上傳完成後，才能處理超連結的問題
        # for i, name in tqdm(enumerate(general_table_df.iloc[:, 3]),
        #                     desc = "run google sheet hyperlink",
        #                     total=general_table_df.shape[0]):
        #     split_name = name.split("-", 1)
        #     if not split_name: continue
        #
        #     sub_html = html_bs.select(f"#tr_{split_name[0]}")
        #     if not sub_html: continue
        #
        #     sub_df_lst = pd.read_html(
        #         StringIO(str(sub_html))
        #     )
        #     if len(sub_df_lst) != 1:
        #         print(f"len: {len(sub_df_lst)}")
        #         continue
        #     sub_df = sub_df_lst[0].iloc[8:10, 0:2].dropna()
        #
        #     for j in range(0, sub_df.shape[0]):
        #         link = sub_df.iloc[j, 1]
        #         if link and link != "nan":
        #             # work_sheet.update_cell(i + 2, 5 + j, name if j == 0 else "LINK")  # 行列是從1開始，DataFrame是從0開始
        #             # cell = work_sheet.cell(i + 2, 5 + j)
        #             # cell_value = cell.value
        #
        #             # cell_loc = f"{chr(ord('D') + j)}{i + 2}"
        #             text = f'=HYPERLINK("{link}", "{name if (j == 0) else "LINK"}")'
        #             update_cells_lst.append(Cell(i + 2, j + 4, text))
        #
        #             # batch_update_lst.append({
        #             #     'range': cell_loc,
        #             #     'values': [[text]]
        #             # })
        #             # work_sheet.update_cells()
        #
        #             # 請求次數過多
        #             # work_sheet.update_cell(i + 2, 4 + j, text)
        #
        #             # 傳統 Excel 做法
        #             # general_table_df.iloc[i, 3 + j] = \
        #             #     f'=HYPERLINK("{link}", "{name if (j == 0) else "LINK"}")'
        #
        #
        # rows = general_table_df.shape[0]
        # cols = general_table_df.shape[1]
        # if update_cells_lst:
        #     work_sheet.update_cells(update_cells_lst, ValueInputOption.user_entered)
        #
        #
        # work_sheet.format(
        #     f'A1:{chr(ord("A") + cols - 1)}{rows + 1}',
        #     {
        #         "horizontalAlignment": "CENTER",
        #         "textFormat": {
        #             "fontSize": 16
        #         }
        #     }
        # )
        # work_sheet.format(
        #     f'D2:D{rows + 1}',
        #     {
        #         "horizontalAlignment": "LEFT"
        #     }
        # )
        # work_sheet.format(
        #     f'G2:G{rows + 1}',
        #     {
        #         "horizontalAlignment": "RIGHT"
        #     }
        # )

        return True

    def __write_google_sheet(
            self,
            table_df: DataFrame,
            table_df_max_length,
            sheet_url = None,
            work_sheet_title: str = "testSheet"
    ) -> bool:
        if self.log: print(f"{self.__class_name} __write_google_sheet")

        if (sheet_url is None) or (sheet_url == ""):
            sheet_url = self.__sheet_url

        # 將 index 預處理，避免出現忘記處理的事情
        table_df = table_df.reset_index(drop = True)

        # 連結 google sheet
        sheet = self.__gc.open_by_url(self.__sheet_url)
        work_sheet: Worksheet | None = None
        old_df: DataFrame | None = None

        # 如果資料表存在，就檢查資料是否有變動
        if work_sheet_title in [ws.title for ws in sheet.worksheets()]:
            work_sheet = sheet.worksheet_by_title(work_sheet_title)
            # 使用公式的方式讀取出來，才能讀出 hyperlink，不然只有顯示文字
            old_df = work_sheet.get_as_df(
                value_render = ValueRenderOption.FORMULA,
            )
            # 因為使用公式讀取的原因，所以日期需要從 excel 日期轉換成一般日期
            old_df["申請期限"] = old_df["申請期限"].apply(
                # timedelta -2 是為了修復 Excel 的 bug
                lambda __x : (datetime.datetime(1900, 1, 1) + datetime.timedelta(days=__x - 2)).strftime('%Y/%m/%d')
            )

        # 如果資料相同，那就不用上傳資料，避免浪費
        if not old_df is None:
            if old_df.equals(table_df): return False

            # print(old_df.compare(
            #     other = table_df,
            #     keep_shape = True,
            #     keep_equal=False
            # ))

        # 如果 work_sheet 是 None，代表沒有創見過資料表
        if work_sheet is None:
            # 創建 sheet
            work_sheet = sheet.add_worksheet(
                tilte = work_sheet_title,
                rows = table_df.shape[0],
                cols = table_df.shape[1]
            )
        else:
            # 清除內容並重新寫入
            work_sheet.clear()
            work_sheet.resize(
                rows = table_df.shape[0],
                cols = table_df.shape[1]
            )

        # 更新資料至 Google Sheet
        work_sheet.set_dataframe(
            table_df,
            (1, 1),  # 從 A1 開始寫入
            copy_head = True  # 包含欄位名稱
        )

        # 格式化 Google Sheet
        rows = table_df.shape[0]
        cols = table_df.shape[1]

        x = 0.70
        font_size = 16
        # 設定欄位寬度
        for i in range(4, 8):
            work_sheet.adjust_column_width(i, pixel_size = int(table_df_max_length[i - 4] * font_size * x))

        # 將所有資料都先條成 fontSize 16，以及置中
        DataRange(f'A1',
                  f'{chr(ord("A") + cols - 1)}{rows + 1}',
                  worksheet=work_sheet
        ).apply_format(
            pygsheets.Cell('A1')
                .set_text_format("fontSize", font_size)
                .set_horizontal_alignment(HorizontalAlignment.CENTER)
        )
        # 再將獎學金名稱調整成向左靠齊
        # 不加 ".set_text_format("fontSize", font_size)"，會出現都變回原本預設的字體大小
        DataRange(f'D2',
                  f'D{rows + 1}',
                  worksheet=work_sheet
        ).apply_format(
            pygsheets.Cell('D2')
                .set_text_format("fontSize", font_size)
                .set_horizontal_alignment(HorizontalAlignment.LEFT)
        )
        # 再將金錢調整成向右靠齊，並設定數字格式
        # 不加 ".set_text_format("fontSize", font_size)"，會出現都變回原本預設的字體大小
        DataRange(f'G2',
                  f'G{rows + 1}',
                  worksheet=work_sheet
        ).apply_format(
            pygsheets.Cell('G2')
                .set_text_format("fontSize", font_size)
                .set_horizontal_alignment(HorizontalAlignment.RIGHT)
                .set_number_format(format_type = FormatType.NUMBER, pattern = "#,##0")
        )
        # 再將日期調整成向右靠齊，並設定日期格式
        # 不加 ".set_text_format("fontSize", font_size)"，會出現都變回原本預設的字體大小
        DataRange(f'F2',
                  f'F{rows + 1}',
                  worksheet=work_sheet
        ).apply_format(
            pygsheets.Cell('F2')
                .set_text_format("fontSize", font_size)
                .set_horizontal_alignment(HorizontalAlignment.CENTER)
                .set_number_format(format_type = FormatType.DATE, pattern = "yyyy/MM/dd")
        )

        return True


    def load_apply_scholarships(self) -> bool:
        if self.log: print(f"{self.__class_name} load_apply_scholarships")
        if not self.login_success: return False

        url = f"{self.system_domain}/ST0075/Apply"
        return True

    def test(self):
        if self.log: print(f"{self.__class_name} test")
        pass



if __name__ == "__main__":
    cyut_scholarships = CYUTScholarships()
    cyut_scholarships.load_scholarships()