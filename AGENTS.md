Behavior rules: see `workflow/SYSTEM.md`.
行為規則請見 `workflow/SYSTEM.md`。
When you read this file, re-read `workflow/SYSTEM.md` and follow it, even if it has not changed.
讀到這裡時，不論 `workflow/SYSTEM.md` 是否有更新，都要重新讀取一次並且遵守

# Project Overview (English)
This project trains and validates YOLO models to detect fire and smoke.

## Tech Stack
- Python 3.10.16
- Python environment path: `./CollageLoginEnv/Scripts/python.exe"`
- ultralytics 8.4.12
- torch 2.10.0+cu126
- See `requirements.txt` for the rest

## Disallowed Packages
- None

## Directory Layout
- `/colageLogin/` - log in to the university student information system and retrieve required data
- `/MessageingApp/` - send notifications to communication software
- `/UI/` - responsible for integrating all components and running them in the GUI
- `/yolo/` - responsible for training, manual testing, and model invocation

# Coding Standards

## Naming Conventions
- Files: snake_case (e.g., yolo_server.py)
- Classes: PascalCase (e.g., UserController)
- Functions: snake_case (e.g., get_user_by_id)
- Variables: snake_case (e.g., user_count)
- Constants: UPPER_SNAKE_CASE (e.g., MAX_RETRY_COUNT)
- Private members: prefix "_" (e.g., _validate_input)

## Typing & Static Analysis
- Untyped public APIs are not allowed.
- All public functions and methods must be type-annotated.
- Use `typing` standard types first.
- Prefer `@dataclass` for data structures.
- Avoid `Any`; if required, document the reason.

## Docstrings
- All public functions/classes must have Google-style docstrings.
- Include functionality, arguments, return values, and possible raised exceptions.

Example:
```
def get_user_by_id(user_id: int) -> User:
    """
    Retrieve user information by user ID.

    Args:
        user_id (int): Unique identifier of the user.

    Returns:
        User: User data object.

    Raises:
        UserNotFoundError: If the user does not exist.
    """
```

## Error Handling
- All business errors must use custom exceptions.
- Uniformly inherit from `Exception` or a dedicated project base error.

Example:
```
class ApplicationError(Exception):
    """Base class for application-level errors."""
class UserNotFoundError(ApplicationError):
    def __init__(self, user_id: int):
        super().__init__(f"User not found. user_id={user_id}")
        self.user_id = user_id
```

## try / except Rules
- All async functions must use try/except.
- Error messages must include context.
- Catching bare `Exception` and doing nothing is not allowed.

Example:
```
async def get_user_profile(user_id: int) -> User:
    try:
        return await fetch_user(user_id)
    except UserNotFoundError as exc:
        raise
    except Exception as exc:
        raise ApplicationError(
            f"Failed to get user profile. user_id={user_id}"
        ) from exc
```


---

# 專案概述（繁體中文）
這是一個 YOLO 訓練與驗證專案，用於偵測火焰與煙霧。

## 技術棧
- Python 3.10.16
- Python 環境路徑：`./CollageLoginEnv/Scripts/python.exe"`
- ultralytics 8.4.12
- torch 2.10.0+cu126
- 其餘請見 `requirements.txt`

## 禁止使用的套件
- 無

## 目錄結構
- `/colageLogin/` - 登入大學學生資訊系統，以及取得需要資料
- `/MessageingApp/` - 發送通知至通訊軟體
- `/UI/` - 負責將所有組件統整起來，在 GUI 上執行
- `/yolo/` - 負責訓練、人工測試以及調用模型

# 程式碼規範

## 命名慣例
- 檔案名稱：snake_case（例：yolo_server.py）
- 類別名稱：PascalCase（例：UserController）
- 函數名稱：snake_case（例：get_user_by_id）
- 變數名稱：snake_case（例：user_count）
- 常數：UPPER_SNAKE_CASE（例：MAX_RETRY_COUNT）
- 私有成員：前綴底線 _（例：_validate_input）

## 型別與靜態檢查（Typing & Static Analysis）
- 禁止使用未標註型別的公開 API。
- 所有公開函式與方法必須標註型別。
- 優先使用 `typing` 標準型別。
- 資料結構優先使用 `@dataclass`。
- 避免使用 `Any`，若必要需明確註解原因。

## 文件註解（Docstring）
- 所有公開函式 / 類別都必須有 Docstring。
- 採用 Google Style Docstring。
- Docstring 需說明功能、參數、回傳值、可能拋出的例外。

範例：
```
def get_user_by_id(user_id: int) -> User:
    """
    Retrieve user information by user ID.

    Args:
        user_id (int): Unique identifier of the user.

    Returns:
        User: User data object.

    Raises:
        UserNotFoundError: If the user does not exist.
    """
```

## 錯誤處理（Error Handling）
- 所有業務錯誤必須使用 `自訂例外`。
- 統一繼承 `Exception` 或專用基底錯誤類。

範例：
```
class ApplicationError(Exception):
    """Base class for application-level errors."""
class UserNotFoundError(ApplicationError):
    def __init__(self, user_id: int):
        super().__init__(f"User not found. user_id={user_id}")
        self.user_id = user_id
```

## try / except 規範
- 所有 async 函式必須使用 try / except。
- 錯誤訊息必須包含上下文資訊。
- 不允許裸捕捉 `Exception` 後什麼都不做。

範例：
```
async def get_user_profile(user_id: int) -> User:
    try:
        return await fetch_user(user_id)
    except UserNotFoundError as exc:
        raise
    except Exception as exc:
        raise ApplicationError(
            f"Failed to get user profile. user_id={user_id}"
        ) from exc
```
