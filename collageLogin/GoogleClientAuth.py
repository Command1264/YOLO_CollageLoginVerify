import os
import sys
import webbrowser
import traceback
from contextlib import contextmanager
from pathlib import Path
from typing import Any, cast

from google.auth.credentials import Credentials as BaseCredentials
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

import pygsheets
from pygsheets.client import Client

project_root_path = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root_path not in sys.path:
    sys.path.append(project_root_path)
from utils.app_paths import get_token_path, to_universal_path

class CertificateNotEnabledException(Exception):
    def __init__(self, message: str):
        super().__init__(message)

class GoogleClientAuth:
    oauth_file: str
    token_file: str

    def __init__(
            self,
            oauth_file: str,
            token_file: str | None = None,
            scope: list[str] | None = None,
    ):
        self.oauth_file = oauth_file
        self.token_file = token_file if token_file is not None else to_universal_path(get_token_path())
        Path(self.token_file).parent.mkdir(parents = True, exist_ok = True)
        # 設定需要的範圍
        self.scopes = scope if scope is not None else [
            "https://www.googleapis.com/auth/drive",       # 雲端硬碟完整存取
            "https://www.googleapis.com/auth/spreadsheets" # 試算表完整存取
        ]

    @contextmanager
    def _use_original_std_streams(self):
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        try:
            sys.stdout = sys.__stdout__
            sys.stderr = sys.__stderr__
            yield
        finally:
            sys.stdout = original_stdout
            sys.stderr = original_stderr

    def authenticate_oauth(self) -> BaseCredentials | None:
        creds: BaseCredentials | None = None

        # 如果 token 檔案存在，嘗試讀取已保存的憑證
        if os.path.exists(self.token_file):
            try:
                with self._use_original_std_streams():
                    creds = cast(
                        Credentials,
                        Credentials.from_authorized_user_file(self.token_file, self.scopes)
                    )
            except RecursionError as e:
                print(f"讀取憑證時發生遞迴錯誤，將刪除舊 token 並重新授權: {e}")
                self._delete_token_file()
                creds = None
            except Exception as e:
                print(f"讀取憑證檔案失敗: {e}")
                self._delete_token_file()
                creds = None

        # 先嘗試延展 token 期限
        if creds and not creds.valid and creds.expired and creds.refresh_token:
            try:
                with self._use_original_std_streams():
                    creds.refresh(Request())
            except RecursionError as e:
                print(f"憑證更新時發生遞迴錯誤，將刪除舊 token 並重新授權: {e}")
                self._delete_token_file()
                creds = None
            except Exception as e:
                print(f"憑證更新失敗，將刪除舊 token 並重新授權: {e}")
                self._delete_token_file()
                creds = None

        # 如果憑證無效或不存在，進行新的驗證（會自動跳瀏覽器）
        if not creds or not creds.valid:
            with self._use_original_std_streams():
                creds = self._run_oauth_flow()

            # 保存新的憑證到 token 檔案
            with open(self.token_file, "w") as token:
                token.write(cast(Any, creds).to_json())

        return creds

    def _run_oauth_flow(self) -> BaseCredentials:
        if not os.path.isfile(self.oauth_file):
            webbrowser.open("https://pygsheets.readthedocs.io/en/stable/authorization.html#oauth-credentials")
            raise CertificateNotEnabledException("OAuth 憑證檔案不存在，請下載並提供。")

        flow = InstalledAppFlow.from_client_secrets_file(
            self.oauth_file,
            self.scopes
        )
        try:
            return flow.run_local_server(
                port=0,
                host="127.0.0.1",
                access_type="offline",
                prompt="consent",
                include_granted_scopes="true",
            )
        except RecursionError as e:
            print(f"OAuth 本機授權發生遞迴錯誤，改用手動授權流程: {e}")
        except Exception as e:
            print(f"OAuth 本機授權失敗，改用手動授權流程: {e}")
            traceback.print_exc()

        return flow.run_local_server(
            port=0,
            host="127.0.0.1",
            open_browser=False,
            access_type="offline",
            prompt="consent",
            include_granted_scopes="true",
        )

    def _delete_token_file(self) -> None:
        if os.path.exists(self.token_file):
            os.remove(self.token_file)

    def authorize_pygsheets(self) -> Client | None:
        # 使用憑證進行 pygsheets 授權
        gc = None
        creds = self.authenticate_oauth()
        if creds is not None:
            gc = pygsheets.authorize(custom_credentials = creds)
        return gc
