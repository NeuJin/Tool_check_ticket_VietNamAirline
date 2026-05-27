#!/usr/bin/env bash
# Khởi động VNA Flight Check (mở trong browser hoặc desktop window nếu có pywebview)
cd "$(dirname "$0")"

if python3 -c "import webview" 2>/dev/null; then
    python3 run_local.py --window
else
    python3 run_local.py
fi
