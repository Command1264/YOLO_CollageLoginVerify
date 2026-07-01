@echo off
@chcp 65001 >nul
setlocal
cd /d %~dp0

set "PYTHON=.\CollageLoginEnv\Scripts\python.exe"

if not exist "%PYTHON%" (
  echo [ERROR] Python not found: %PYTHON%
  exit /b 1
)

echo [1/2] Running compileall...
"%PYTHON%" -m compileall -q UI MessagingApp collageLogin utils
if errorlevel 1 (
  echo [ERROR] compileall failed.
  exit /b 1
)

echo [2/2] Running pyright...
"%PYTHON%" -m pyright
if errorlevel 1 (
  echo [ERROR] pyright failed.
  exit /b 1
)

echo [OK] All checks passed.
exit /b 0
