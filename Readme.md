# YOLO_CollageLoginVerify

YOLO_CollageLoginVerify 是一個以 Python 建立的校園系統影像辨識與個人工具自動化專案。專案結合 YOLO 影像辨識、學生資訊系統資料擷取、Google Sheets 整合，以及 Telegram / Discord 通知流程，用於減少重複人工操作並整理查詢結果。

> 本專案以個人學習、影像辨識實作與自動化流程整合為主。使用前請確認符合目標系統規範，並妥善保護帳號、API token 與 Google 憑證。

## 專案重點

- 使用 YOLOv11 與監督式學習建立影像辨識流程。
- 整合 OpenCV / Ultralytics / PyTorch 進行資料處理、模型訓練與推論。
- 將辨識結果串接至自動化流程，降低重複手動操作。
- 整合 Google API / Google Sheets，整理與同步查詢資料。
- 提供 Telegram / Discord bot 相關模組，探索通知與互動流程。
- 逐步加入 PySide6 GUI、排程、歷史紀錄與背景工作流程。

## 功能模組

### 影像辨識

詳細說明：[readme/Readme-YOLO.md](readme/Readme-YOLO.md)

- 使用 YOLOv11 訓練特定小型目標辨識模型。
- 支援資料收集、標註、訓練、模型評分與推論測試。
- 提供公開資料集連結與模型下載資訊。

### 學生資訊系統資料擷取

詳細說明：[readme/Readme-CollageLogin.md](readme/Readme-CollageLogin.md)

- 將影像辨識結果整合到自動化查詢流程。
- 透過 Google API / pygsheets 將資料整理到 Google Sheets。
- 包含獎學金資料查詢、格式化與比對相關模組。

### 通知與互動

詳細說明：[readme/Readme-Telegram.md](readme/Readme-Telegram.md)

- 包含 Telegram bot 與 Discord bot 相關模組。
- 支援使用者綁定資料與通知流程探索。
- 可作為查詢結果推送、狀態通知與互動命令的基礎。

### GUI 與排程流程

目前程式中包含 PySide6 GUI、排程檢查、結果處理、歷史紀錄與系統托盤相關模組。這些模組用於把原本分散的查詢、自動化與通知流程整合成桌面工具。

## 技術棧

- Python 3.12
- PySide6
- OpenCV
- Ultralytics YOLO
- PyTorch
- pandas
- Google API / pygsheets
- Telegram bot / Discord bot
- requests / BeautifulSoup

完整依賴請見 [`requirements.txt`](requirements.txt)。

## 目錄結構

```text
yolo/           影像資料處理、模型訓練、推論測試與模型評分
collageLogin/   學生資訊系統查詢、Google Sheets 整合與資料處理
MessagingApp/   Telegram / Discord bot 與使用者綁定資料
UI/             PySide6 GUI、排程、背景工作與通知流程
utils/          共用工具模組
readme/         子模組說明文件
workflow/       專案工作流程與 agent 操作規範
```

## 快速開始

建立環境：

```powershell
py -3.12 -m venv CollageLoginEnv
.\CollageLoginEnv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

啟動流程依使用情境而定：

```powershell
.\Start.bat
```

或啟動影像辨識服務：

```powershell
.\StartLoginVerifyServer.bat
```

## 憑證與設定

本專案可能需要：

- 學生資訊系統帳號設定
- Google API OAuth 憑證
- Telegram bot token
- Discord bot token
- Google Sheet ID 或相關設定

請勿將任何帳號、token、cookie、OAuth credential 或私密設定提交到 GitHub。

## 代表性學習成果

- 完成 YOLOv11 影像辨識資料集、訓練與推論流程。
- 將模型推論整合到實際自動化查詢流程中。
- 串接 Google Sheets 與 messaging bot，建立資料整理與通知流程。
- 以 PySide6 嘗試將查詢、排程、通知與歷史紀錄整合成桌面工具。

## 注意事項

- 本專案為個人學習與自動化工具實作，使用時請遵守學校與相關服務規範。
- 對外公開前請檢查是否包含個資、帳號、token、憑證或查詢結果。
- 自動化流程可能受網站改版、驗證流程或 API 限制影響。
