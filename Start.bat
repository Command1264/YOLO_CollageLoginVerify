@echo off
@chcp 65001
@title 更新校內外獎助學金
cd /d %~dp0
cls

cd collageLogin
"..\CollageLoginEnv\Scripts\python.exe" CYUTScholarships.py
:: timeout 10
pause
