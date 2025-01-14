import requests

import pandas as pd
import unicodedata, os
from dotenv import load_dotenv
from pandas import DataFrame
import numpy as np

from bs4 import BeautifulSoup

import datetime
from io import StringIO

from tqdm import tqdm

import pygsheets
from pygsheets import DataRange, HorizontalAlignment, FormatType, Worksheet, ValueRenderOption
from pygsheets.client import Client

from CYUTLogin import CYUTLogin


def calculate_column_width(text):
    return sum(2 if unicodedata.east_asian_width(t) in "FWA" else 1 for t in text)
    # # 計算中文字符數
    # chinese_char_count = len(re.findall(r'[\u4e00-\u9fff]', text))
    # # 計算英文字符數
    # non_chinese_char_count = len(text) - chinese_char_count
    # # 假設英文字符寬度為 1，中文字符寬度為 2
    # total_width = non_chinese_char_count * 1 + chinese_char_count * 2
    # return total_width


def calculate_column_width_with_title(data_frame: DataFrame) -> int:
    if data_frame is None: return -1
    return int(data_frame.apply(calculate_column_width).max())


class CYUTScholarships(CYUTLogin):
    log: bool = False

    __gc: Client
    # __creds:
    # __sheet_url: str | None = None
    # __email: str = None

    __spreadsheet: Worksheet | None = None

    @staticmethod
    def __get_class_name():
        return CYUTScholarships.__name__

    def __init__(
            self,
            client_secret_file: str = "./OAuthCredentials.json",
            service_file: str = "./ServiceAccountCredentials.json",
            # sheet_url: str = "https://docs.google.com/spreadsheets/d/1N5ujLg2NE8JRJPXhGIDFXfSBRp_q0s0XFeDjIiJsp-w/edit?usp=sharing",
            log: bool = False
    ) -> None:
        super().__init__(log = log)
        if self.log: f"{self.__get_class_name()} __init__"

        # 載入區域環境變數
        load_dotenv()
        # 從環境變數取得email(RIP)
        # self.__email = os.getenv("email")

        # 初始化
        self.log = log

        # 取得 Google OAuth 驗證
        # self.__gc = pygsheets.authorize(service_file = service_file)
        self.__gc = pygsheets.authorize(
            client_secret = client_secret_file,
        )


    # def authenticate_oauth(self, oauth_file):
    #     # 設定權限範圍
    #     SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
    #
    #     creds = None
    #     # 檢查是否已經保存了有效的憑證
    #     if os.path.exists("token.pickle"):
    #         with open("token.pickle", "rb") as token:
    #             creds = pickle.load(token)
    #
    #     # 如果憑證無效或不存在，就讓用戶進行登錄
    #     if not creds or not creds.valid:
    #         if creds and creds.expired and creds.refresh_token:
    #             creds.refresh(Request())
    #         else:
    #             flow = InstalledAppFlow.from_client_secrets_file(
    #                 oauth_file, SCOPES)
    #             creds = flow.run_local_server(port=0)
    #
    #         # 保存憑證，以便下次使用
    #         with open("token.pickle", "wb") as token:
    #             pickle.dump(creds, token)
    #
    #     return creds

    def load_scholarships(self) -> bool:
        if self.log: print(f"{self.__get_class_name()} load_scholarships")

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

        academic_year_select = html_bs.find("select", {
            "id": "acy",
            "name": "acy",
        })
        academic_year_option = academic_year_select.find("option", {
            "selected": "selected",
        })

        academic_year_value = academic_year_option["value"]
        self.__spreadsheet = self.__get_create_google_spreadsheet(academic_year_value)
        # print(self.__spreadsheet)

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

        success, has_update = self.__write_google_sheet(
            general_table_df,
            general_table_df_max_length,
            sheet_title="學校資料"
        )
        if success:
            if has_update:
                if self.log: print("Updated successful!")
            else:
                if self.log: print("No updates!")
        else:
            if self.log: print("Updated failed!")

        return True

    def __check_google_sheet(
            self,
            table_df: DataFrame = None,
            spreadsheet = None,
            sheet_title: str = "學校資料",
    ) -> (bool, Worksheet | None):
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
            table_df_max_length,
            spreadsheet = None,
            sheet_title: str = "學校資料"
    ) -> (bool, bool):
        if self.log: print(f"{self.__get_class_name()} __write_google_sheet")

        if spreadsheet is None:
            if self.__spreadsheet is None:
                return False, False
            spreadsheet = self.__spreadsheet

        need_update, worksheet = self.__check_google_sheet(
            table_df,
            spreadsheet= spreadsheet,
            sheet_title= sheet_title
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
        font_size = 16
        # 設定欄位寬度
        for i in range(4, 8):
            worksheet.adjust_column_width(i, pixel_size = int(table_df_max_length[i - 4] * font_size * x))

        # 將所有資料都先條成 fontSize 16，以及置中
        DataRange(f'A1',
                  f'{chr(ord("A") + cols - 1)}{rows + 1}',
                  worksheet=worksheet
        ).apply_format(
            pygsheets.Cell('A1')
                .set_text_format("fontSize", font_size)
                .set_horizontal_alignment(HorizontalAlignment.CENTER)
        )
        # 再將獎學金名稱調整成向左靠齊
        # 不加 ".set_text_format("fontSize", font_size)"，會出現都變回原本預設的字體大小
        DataRange(f'D2',
                  f'D{rows + 1}',
                  worksheet=worksheet
        ).apply_format(
            pygsheets.Cell('D2')
                .set_text_format("fontSize", font_size)
                .set_horizontal_alignment(HorizontalAlignment.LEFT)
        )
        # 再將金錢調整成向右靠齊，並設定數字格式
        # 不加 ".set_text_format("fontSize", font_size)"，會出現都變回原本預設的字體大小
        DataRange(f'G2',
                  f'G{rows + 1}',
                  worksheet=worksheet
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
                  worksheet=worksheet
        ).apply_format(
            pygsheets.Cell('F2')
                .set_text_format("fontSize", font_size)
                .set_horizontal_alignment(HorizontalAlignment.CENTER)
                .set_number_format(format_type = FormatType.DATE, pattern = "yyyy/MM/dd")
        )

        return True, True


    def load_apply_scholarships(self) -> bool:
        if self.log: print(f"{self.__get_class_name()} load_apply_scholarships")
        if not self.login_success: return False

        url = f"{self.system_domain}/ST0075/Apply"
        return True

    def delete_google_spreadsheet(
            self,
            spreadsheet: Worksheet
    ) -> bool:
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
            # spread_sheet_name: str,
            academic_year_value: str,
            spread_sheet_name: str = "%academic_year% 獎學金"
    ) -> Worksheet:
        if self.log: print(f"{self.__get_class_name()} __get_create_google_spreadsheet")
        if len(academic_year_value) != 4:
            raise ValueError("選擇數值不是 4 位數")

        academic_year = f"{academic_year_value[:len(academic_year_value) - 1]}-{academic_year_value[-1]}"
        spread_sheet_name = spread_sheet_name.replace("%academic_year%", academic_year)

        query = "mimeType='application/vnd.google-apps.spreadsheet' and trashed = false"
        # query = "mimeType='application/vnd.google-apps.spreadsheet' or sharedWithMe"
        # sheet_dict = self.__gc.drive.list(q = query, fields = "files(id, name)")
        sheet_dict = self.__gc.drive.list(q = query)
        sheet_names = [file for file in sheet_dict if file["name"] == spread_sheet_name]

        # print(sheet_names)
        match len(sheet_names):
            case 0:
                spreadsheet = self.__gc.create(spread_sheet_name)
            case 1:
                spreadsheet = self.__gc.open_by_key(sheet_names[0]["id"])
            case _:
                # if self.__email is not None:
                #     for sheet in sheet_names:
                #         self.__gc.open_by_key(sheet["id"]) \
                #             .share(self.__email, role='writer')
                raise FileExistsError("存在多個相同名稱 Google 表單，請檢查")
                # return None

        if spreadsheet is None:
            raise FileNotFoundError("找不到 Google 表單")
        # print(spreadsheet.permissions)
        
        # if self.__email is not None:
        #     has_writer_permission = False
        #     for permission in spreadsheet.permissions:
        #         # print(permission)
        #         if permission.get("emailAddress", "") == self.__email and \
        #             permission.get("role", "") =="owner":
        #             has_writer_permission = True
        #             break
        #
        #     if not has_writer_permission:
        #         # 需要先把帳戶改成編輯者，才能升級至擁有者
        #         spreadsheet.share(self.__email, role = "writer")
        #         self.__gc.drive.create_permission(
        #             file_id = spreadsheet.id,
        #             role = 'owner',
        #             type = 'user',
        #             emailAddress = self.__email,
        #             transferOwnership = True  # 這裡必須設置為 True
        #         )
        return spreadsheet

    def test(self):
        if self.log: print(f"{self.__get_class_name()} test")
        # spreadsheet = self.__get_create_google_spreadsheet("1131")
        # print(self.delete_google_spreadsheet(spreadsheet))




if __name__ == "__main__":
    cyut_scholarships = CYUTScholarships(log = True)
    cyut_scholarships.load_scholarships()