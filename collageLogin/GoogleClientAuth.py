import os
import webbrowser

from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

import pygsheets
from pygsheets.client import Client

class CertificateNotEnabledException(Exception):
    def __init__(self, message: str):
        super().__init__(message)

class GoogleClientAuth:
    oauth_file: str | None
    token_file: str | None

    def __init__(
            self,
            oauth_file: str,
            token_file: str | None = None,
            scope: list[str] | None = None,
    ):
        self.oauth_file = oauth_file
        self.token_file = token_file if token_file is not None else "token.json"
        # 設定需要的範圍
        self.scopes = scope if scope is not None else [
            "https://www.googleapis.com/auth/drive",       # 雲端硬碟完整存取
            "https://www.googleapis.com/auth/spreadsheets" # 試算表完整存取
        ]

    def authenticate_oauth(self):
        creds = None

        # 如果 token 檔案存在，嘗試讀取已保存的憑證
        if os.path.exists(self.token_file):
            creds = Credentials.from_authorized_user_file(self.token_file, self.scopes)

        # 如果憑證無效或不存在，進行新的驗證
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                if not os.path.isfile(self.oauth_file):
                    webbrowser.open("https://pygsheets.readthedocs.io/en/stable/authorization.html#oauth-credentials")
                    return None
                flow = InstalledAppFlow.from_client_secrets_file(
                    self.oauth_file,
                    self.scopes
                )
                creds = flow.run_local_server(port = 0)

            # 保存新的憑證到 token 檔案
            with open(self.token_file, "w") as token:
                token.write(creds.to_json())

        return creds

    def authorize_pygsheets(self) -> Client | None:
        # 使用憑證進行 pygsheets 授權
        gc = None
        creds = self.authenticate_oauth()
        if creds is not None: gc = pygsheets.authorize(custom_credentials = creds)
        return gc