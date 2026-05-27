@echo off
REM Khởi động VNA Flight Check (mở trong browser)
REM Double-click file này để chạy

cd /d "%~dp0"

REM Thử dùng pywebview nếu đã cài, nếu không thì mở browser
python -c "import webview" 2>nul
if %errorlevel% == 0 (
    python run_local.py --window
) else (
    python run_local.py
)

pause
