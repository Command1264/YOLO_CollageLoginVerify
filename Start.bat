@echo off
@chcp 65001
@title 更新校內外獎助學金
cd /d %~dp0
cls

call conda activate YOLO_CollageLoginVerify
cd collageLogin
python CYUTScholarships.py
timeout 10
:: pause
