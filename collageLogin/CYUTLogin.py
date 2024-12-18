import requests
from bs4 import BeautifulSoup
import json, os, re
from urllib import parse

from requests import Response

from CYUTLoginVerifyModel import CYUTLoginVerifyModel


class ServerNotConnectException(Exception):
    def __init__(self, message: str):
        super().__init__(message)

class CYUTLogin:
    __class_name = "CYUTLogin"

    # session = requests.Session()

    auth_domain = "https://auth2.cyut.edu.tw"
    system_domain = "https://student.cyut.edu.tw"

    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Sec-Fetch-Dest': 'document',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }

    cookies_file_path = f"cyutLoginCookies.json"
    cookies = {}

    account_file_path = f"account.json"
    account = {
        "account": "",
        "password": ""
    }

    login_tmp_cookie = None
    img_url = None

    model = CYUTLoginVerifyModel("../yolo/yoloSuccessCore/YOLO11x-google-best.pt")

    try_count = 3

    log = True
    login_success = False

    def __init__(self):
        if self.log: print(f"{self.__class_name} __init__")

        # 讀取初始資料
        self.load_account()
        self.load_cookies()

        # 取得最新的 cookies
        # self.get_login_cookies()

        # 嘗試登入(如果 cookies 過期，會嘗試用帳號密碼登入)
        if self.cookies_login():
            self.login_success = True
            print("login successful!")
        else:
            self.login_success = False
            print("login failed!")

    def get_login_cookies(self, path: str = "/User/Login"):
        if self.log: print(f"{self.__class_name} get_login_cookies")

        url = f"{self.auth_domain}{path}"
        # self.session.max_redirects = 1000
        response = requests.get(
            url,
            headers = self.headers,
            # headers = self.headers.update({
            #     "Origin": self.auth_domain,
            # }),
            cookies = self.cookies,
            allow_redirects = False,
        )

        status_code = response.status_code
        if status_code < 200 or status_code >= 400:
            raise ServerNotConnectException(message = f"status_code: {status_code}")
        elif status_code == 302:
            # 目前發現處理重新導向可以使用清除 cookies 來完成處理
            # print(f"{self.class_name} get_login_cookies Status Code: {status_code}")
            # print(f"{self.class_name} get_login_cookies Location: {response.headers.get('Location')}")
            self.clear_cookies()
            self.get_login_cookies()

        self.cookies.update(response.cookies.get_dict())
        # print(f"Cookies: {self.cookies}")

        html_bs = BeautifulSoup(response.text, "html.parser")

        img_lst = html_bs.find_all('img', alt = '驗證碼')
        if len(img_lst) != 1:
            return
        img = img_lst[0]

        tmp_cookie_input_lst = html_bs.find_all("input")
        for item in tmp_cookie_input_lst:
            if item.get("name") == "__RequestVerificationToken":
                self.login_tmp_cookie = item.get("value")
                break

        self.img_url = self.auth_domain + img['src']

        self.save_cookies()
        # print(f"{self.img_url}")

        # print(f"{self.login_tmp_cookie}")

    def re_login(self, try_count: int = 0, path: str = "/User/Login") -> bool:
        if self.log: print(f"{self.__class_name} re_login")

        if try_count >= self.try_count: return False
        if (
            self.img_url is None or
            self.login_tmp_cookie is None
        ):
            # if not self.load_cookies():
            self.get_login_cookies()
            # self.get_login_cookies()
            return self.re_login(try_count = try_count + 1)

        # YOLO 判斷驗證碼
        verify_code = self.model.url_gif_get_verify_code(
            url = self.img_url,
            cookies = self.cookies,
            show = False,
            save = False,
            verbose = True,
            # project = output_date_time_path,
            log = True
        )

        # Body
        payload = {
            "__RequestVerificationToken": self.login_tmp_cookie,
            "ReturnUrl": "",
            "Account": self.account["account"],
            "Password": parse.quote(self.account["password"]),
            "VerificationCode": verify_code
        }

        # print(self.cookies)

        # 第一階段登入
        first_login_url = f"{self.auth_domain}{path}"
        first_response = requests.post(
            first_login_url,
            headers = self.headers,
            cookies = self.cookies,
            # cookies = {
            #     k: v for k, v in self.cookies.items() if k in [
            #         "__RequestVerificationToken",
            #         "ASP.NET_SessionId"
            #     ]
            # },
            data = payload,
            allow_redirects = False,
        )

        self.login_tmp_cookie = None
        self.img_url = None

        self.cookies.update(first_response.cookies.get_dict())
        # print("login successful!")
        # 帳號、密碼、驗證碼錯誤
        if first_response.status_code == 200:
            html_bs = BeautifulSoup(first_response.text, "html.parser")

            # 尋找是哪個部分出錯
            error_msg = []
            for item in html_bs.find_all("span"):
                if (item.get("data-valmsg-for") in ["VerificationCode", "Password", "Account"] and
                        item.text != ""):
                    print(item.text)
                    error_msg.append(item.text)
            if error_msg == ["驗證碼錯誤!!"]:
                return self.re_login(try_count = try_count + 1)


            # print(f"first failed: {first_response.status_code}")
            return False

        elif first_response.status_code != 302:
            print(f"first failed: {first_response.status_code}")
            return False


        # 第二階段登入
        second_response = self.__location_request__(
            name = "second",
            domain = self.auth_domain,
            response = first_response,
            status_code = 302,
        )
        if second_response is None:
            return False


        # 第三階段登入
        third_response = self.__location_request__(
            name = "third",
            domain = self.auth_domain,
            response = second_response,
            status_code = 302,
        )
        if third_response is None: return False
        self.save_cookies(third_response.cookies.get_dict())
        # third_loc = first_response.headers.get('Location')
        # third_login_url = f"{self.auth_domain}{third_loc}" if re.match(r"https?://]", third_loc) else third_loc
        # third_response = requests.get(
        #     third_login_url,
        #     headers = self.headers,
        #     cookies = self.cookies,
        #     allow_redirects = False,
        # )
        # if third_response.status_code != 302:
        #     print(f"third failed: {third_response.status_code}")
        #     return False

        # 第四階段登入
        forth_response = self.__location_request__(
            name = "forth",
            domain = self.system_domain,
            response = third_response,
            status_code = 200,
        )
        if forth_response is None: return False

        # forth_loc = third_response.headers.get('Location')
        # forth_login_url = f"{self.auth_domain}{forth_loc}" if re.match(r"https?://]", str(forth_loc)) else forth_loc
        #
        # forth_response = requests.get(
        #     second_login_url,
        #     headers=self.headers,
        #     cookies=self.cookies,
        #     allow_redirects=False,
        # )
        # if second_response.status_code != 302:
        #     print(f"second failed: {second_response.status_code}")
        #     return False

        html_bs = BeautifulSoup(forth_response.text, "html.parser")

        # 先尋找有無登出 form 的物件，如果沒有，代表登入失敗
        if not html_bs.select("#logoutForm"): return False

            # 尋找是哪個部分出錯
            # for item in html_bs.find_all("span"):
            #     if (item.get("data-valmsg-for") in ["VerificationCode", "Password", "Account"] and
            #         item.text != ""):
            #         print(item.text)

            # print(f"first failed: {first_response.status_code}")

        return True

    def __location_request__(
            self,
            name: str,
            domain,
            response,
            headers = None,
            cookies: dict = None,
            data: dict = None,
            status_code: int = 200,

    ) -> Response | None:
        if self.log: print(f"{self.__class_name} __location_request")

        if headers is None: headers = self.headers
        if cookies is None: cookies = self.cookies
        if data is None: data = {}
        
        loc = response.headers.get('Location')
        url = f"{domain}{loc}" if (not re.match(r"https?://", loc)) else loc

        result_response = requests.get(
            url,
            headers = headers,
            cookies = cookies,
            data = data,
            allow_redirects = False,
        )
        if result_response.status_code != status_code:
            # TODO
            print(f"{name} failed: {result_response.status_code}")
            return None

        return result_response


    def cookies_login(self, try_count: int = 0) -> bool:
        if self.log: print(f"{self.__class_name} cookies_login")

        if try_count >= self.try_count: return False
        url = f"{self.system_domain}/ST0000"
        # print(json.dumps(self.cookies, indent=4))
        response = requests.get(
            url,
            headers = self.headers.update({
                "Origin": self.system_domain,
            }),
            cookies = self.cookies,
            allow_redirects = False
        )
        # 如果是重新導向，也是需要重新登入
        if response.status_code == 302:
            if not self.re_login(): return False
            return self.cookies_login(try_count = try_count + 1)

        if response.status_code != 200: return False

        html_bs = BeautifulSoup(response.text, "html.parser")

        # 如果是未登入畫面，也是需要重新登入
        for item in html_bs.find_all("h1"):
            if item.text == r"您未登入!!":
                if not self.re_login(): return False
                return self.cookies_login(try_count = try_count + 1)


        # 先尋找有無登出 form 的物件，如果沒有，代表登入失敗
        if not html_bs.select("#logoutForm"): return False

        return True

    def save_cookies(self, cookies: dict = None):
        if self.log: print(f"{self.__class_name} save_cookies")

        if cookies is not None: self.cookies.update(cookies)
        with open(self.cookies_file_path, "w") as file:
            file.write(json.dumps(self.cookies, indent = 4))

    def load_cookies(self) -> bool:
        if self.log: print(f"{self.__class_name} load_cookies")

        if not os.path.isfile(self.cookies_file_path): return False
        with open(self.cookies_file_path, "r") as file:
            self.cookies = json.load(fp = file)
            self.cookies["culture"] = "zh-TW"
        return True

    def load_account(self):
        if self.log: print(f"{self.__class_name} load_account")

        if not os.path.isfile(self.account_file_path): return False
        with open(self.account_file_path, "r") as file:
            self.account = json.load(fp = file)

    def clear_cookies(self):
        self.cookies.clear()
        if os.path.isfile(self.cookies_file_path):
            os.remove(self.cookies_file_path)

if __name__ == "__main__":
    cyutLogin = CYUTLogin()
    # cyutLogin.save_cookies()








