import requests, json, os, re, sys
from bs4 import BeautifulSoup
from urllib import parse
from dotenv import load_dotenv
from pathlib import Path
from typing import Any

collage_login_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'collageLogin'))
sys.path.append(collage_login_path)
project_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root_path not in sys.path:
    sys.path.append(project_root_path)

from utils.app_paths import get_app_data_dir, get_cookies_path, get_runtime_base_dir, to_universal_path
from utils.verify_model_provider import get_shared_verify_model, get_shared_verify_model_lock
try:
    from .CYUTLoginVerifyModel import CYUTLoginVerifyModel
except ImportError:
    from CYUTLoginVerifyModel import CYUTLoginVerifyModel


class ServerNotConnectException(Exception):
    def __init__(self, message: str):
        super().__init__(message)

# TODO 需寫出檢查登入狀態的程式
class CYUTLogin:
    auth_domain = "https://auth2.cyut.edu.tw"
    system_domain = "https://student.cyut.edu.tw"

    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Sec-Fetch-Dest': 'document',
        'Accept-Encoding': 'gzip, deflate, br',
        'Connection': 'keep-alive',
    }

    cookies_file_path = to_universal_path(get_cookies_path())
    cookies = {}

    account: dict[str, str | None]

    login_tmp_cookie = None
    img_url = None
    login_success = False

    log: bool
    verbose: bool
    try_count: int
    model: CYUTLoginVerifyModel
    model_lock: Any

    @staticmethod
    def __get_class_name():
        return CYUTLogin.__name__

    def __init__(
        self,
        log: bool = False,
        verbose: bool = False,
        try_count: int = 3,
        model_path: str | None = None,
    ):
        self.log = log
        self.verbose = verbose
        self.try_count = try_count
        model_name = "YOLO11x-google-best.pt"
        runtime_model_candidates: list[Path] = []
        if getattr(sys, "frozen", False):
            exe_dir = Path(sys.executable).resolve().parent
            mei_root = getattr(sys, "_MEIPASS", "")
            if mei_root:
                runtime_model_candidates.append(Path(str(mei_root)).resolve() / "model" / model_name)
            runtime_model_candidates.append(exe_dir / "_internal" / "model" / model_name)
            runtime_model_candidates.append(exe_dir / "model" / model_name)
        else:
            script_dir = Path(__file__).resolve().parents[1] / "UI"
            runtime_model_candidates.append(script_dir / "CYUTScholarshipRadar" / "model" / model_name)
            runtime_model_candidates.append(Path(__file__).resolve().parents[1] / "model" / model_name)
        runtime_default_model = runtime_model_candidates[0]
        for candidate in runtime_model_candidates:
            if candidate.is_file():
                runtime_default_model = candidate
                break
        legacy_default_model = (
            Path(__file__).resolve().parents[1] /
            "yolo" /
            "yoloSuccessCore" /
            "YOLO11x-google-best.pt"
        )
        configured_model_path = (model_path or "").strip()
        env_model_path = os.getenv("CYUT_VERIFY_MODEL_PATH", "").strip()
        selected_model_path = configured_model_path or env_model_path or to_universal_path(runtime_default_model)
        selected_model_file = Path(selected_model_path)
        if (not selected_model_file.is_file()) and legacy_default_model.is_file():
            selected_model_path = to_universal_path(legacy_default_model)
        self.model = get_shared_verify_model(selected_model_path)
        self.model_lock = get_shared_verify_model_lock()

        if self.log: print(f"{self.__get_class_name()} __init__")

        # 載入區域環境變數
        load_dotenv()
        self.cookies_file_path = to_universal_path(get_cookies_path())
        Path(self.cookies_file_path).parent.mkdir(parents = True, exist_ok = True)
        # 從環境變數載入帳號密碼
        self.account = {
            "account": os.getenv("CYUT_LOGIN_ACCOUNT", None) or os.getenv("account", None),
            "password": os.getenv("CYUT_LOGIN_PASSWORD", None) or os.getenv("password", None)
        }

        # 檢查登入帳號密碼
        for key, value in self.account.items():
            if (value is None) or (value == ""):
                raise Exception(
                    f"{self.__get_class_name()} {key} is None or empty, please check environment variables!"
                )

        # 讀取初始資料
        self.load_cookies()

        # 嘗試登入(如果 cookies 過期，會嘗試用帳號密碼登入)
        if self.cookies_login():
            self.login_success = True
            if self.log: print("login successful!")
        else:
            self.login_success = False
            if self.log: print("login failed!")

    def get_login_cookies(self, path: str = "/User/Login"):
        if self.log: print(f"{self.__get_class_name()} get_login_cookies")

        url = f"{self.auth_domain}{path}"
        # self.session.max_redirects = 1000
        response = requests.get(
            url,
            headers = self.headers,
            cookies = self.cookies,
            allow_redirects = False,
        )

        status_code = response.status_code
        if status_code < 200 or status_code >= 400:
            raise ServerNotConnectException(message = f"status_code: {status_code}")
        elif status_code == 302:
            # 目前發現處理重新導向可以使用清除 cookies 來完成處理
            self.clear_cookies()
            self.get_login_cookies()

        self.cookies.update(response.cookies.get_dict())

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

        img_src = str(img.get("src", "")).strip()
        self.img_url = f"{self.auth_domain}{img_src}"

        self.save_cookies()

    def re_login(
            self,
            try_count: int = 0,
            path: str = "/User/Login"
    ) -> bool:
        if self.log: print(f"{self.__get_class_name()} re_login")

        if try_count >= self.try_count: return False
        if (
            self.img_url is None or
            self.login_tmp_cookie is None
        ):
            self.get_login_cookies()
            return self.re_login(try_count = try_count + 1)

        # YOLO 判斷驗證碼
        with self.model_lock:
            verify_code = self.model.url_gif_get_verify_code(
                url = self.img_url,
                cookies = self.cookies,
                show = False,
                save = False,
                verbose = self.verbose,
                log = self.log
            )
        if verify_code is None:
            return self.re_login(try_count = try_count + 1)

        # Body
        payload = {
            "__RequestVerificationToken": self.login_tmp_cookie,
            "ReturnUrl": "",
            "Account": self.account["account"],
            "Password": parse.quote(str(self.account["password"] or "")),
            "VerificationCode": verify_code
        }

        # 第一階段登入
        first_login_url = f"{self.auth_domain}{path}"
        first_response = requests.post(
            first_login_url,
            headers = self.headers,
            cookies = self.cookies,
            data = payload,
            allow_redirects = False,
        )

        self.login_tmp_cookie = None
        self.img_url = None

        self.cookies.update(first_response.cookies.get_dict())
        # 帳號、密碼、驗證碼錯誤
        if first_response.status_code == 200:
            html_bs = BeautifulSoup(first_response.text, "html.parser")

            # 尋找是哪個部分出錯
            error_msgs = []
            for item in html_bs.find_all("span"):
                if (item.get("data-valmsg-for") in ["VerificationCode", "Password", "Account"] and
                        item.text != ""):
                    print(item.text)
                    error_msgs.append(item.text)
            if error_msgs == ["驗證碼錯誤!!"]:
                return self.re_login(try_count = try_count + 1)

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

        # 第四階段登入
        forth_response = self.__location_request__(
            name = "forth",
            domain = self.system_domain,
            response = third_response,
            status_code = 200,
        )
        if forth_response is None: return False

        html_bs = BeautifulSoup(forth_response.text, "html.parser")

        # 先尋找有無登出 form 的物件，如果沒有，代表登入失敗
        if not html_bs.select("#logoutForm"): return False
        return True

    def __location_request__(
            self,
            name: str,
            domain,
            response,
            headers: dict | None = None,
            cookies: dict | None = None,
            data: dict | None = None,
            status_code: int = 200,

    ) -> requests.Response | None:
        if self.log: print(f"{self.__get_class_name()} __location_request__")

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
        if self.log: print(f"{self.__get_class_name()} cookies_login")

        if try_count >= self.try_count: return False
        url = f"{self.system_domain}/ST0000"

        request_headers = dict(self.headers)
        request_headers.update({
            "Origin": self.system_domain,
        })
        response = requests.get(
            url,
            headers = request_headers,
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

    # 儲存網頁 cookies，用於下次登入
    def save_cookies(self, cookies: dict | None = None):
        if self.log: print(f"{self.__get_class_name()} save_cookies")

        if cookies is not None: self.cookies.update(cookies)
        with open(self.cookies_file_path, "w", encoding = "utf-8") as file:
            file.write(json.dumps(self.cookies, indent = 4))

    # 載入 cookies
    def load_cookies(self) -> bool:
        if self.log: print(f"{self.__get_class_name()} load_cookies")

        if not os.path.isfile(self.cookies_file_path): return False
        with open(self.cookies_file_path, "r", encoding = "utf-8") as file:
            self.cookies = json.load(fp = file)
            self.cookies["culture"] = "zh-TW"
        return True

    # 清除 cookies
    def clear_cookies(self):
        self.cookies.clear()
        if os.path.isfile(self.cookies_file_path):
            os.remove(self.cookies_file_path)

if __name__ == "__main__":
    cyutLogin = CYUTLogin()








