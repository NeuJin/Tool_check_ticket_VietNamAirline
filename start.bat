@echo off
REM Khởi động VNA Flight Check (desktop window + Python backend)
REM Double-click file này để chạy

cd /d "%~dp0"

REM Đảm bảo pywebview & requests đã được cài
python -c "import webview, requests" 2>nul
if %errorlevel% neq 0 (
    echo Cai pywebview va requests truoc...
    python -m pip install pywebview requests
)

python run_local.py --window
pause
