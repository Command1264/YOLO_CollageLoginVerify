@echo off
@chcp 65001
@title 自動辨識驗證碼
cd /d %~dp0
cls

call conda activate YOLO_CollageLoginVerify
cd collageLogin
start pythonw CYUTLoginVeriftModelApp.py

:: pause
