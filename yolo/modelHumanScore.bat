@echo off
@chcp 65001
@title 人工人智慧檢查
cd /d %~dp0
cls

call conda activate YOLO_CollageLoginVerify
cd yolo
python modelScore.py
timeout 10