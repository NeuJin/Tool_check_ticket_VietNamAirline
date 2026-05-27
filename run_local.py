"""
run_local.py — Chạy VNA Flight Check như một desktop app local.

Cách 1 (đơn giản nhất, không cần thêm gì):
    python run_local.py
→ Mở file standalone HTML trong browser mặc định.

Cách 2 (desktop window thực sự, không có thanh URL):
    pip install pywebview
    python run_local.py --window
→ Mở trong cửa sổ desktop riêng (1280x820, resizable).

LƯU Ý: Đây mới chỉ là UI thuần (mock data). Để có data thật từ VNA, làm theo
hướng dẫn trong integration/INTEGRATION_GUIDE.md (Option A khuyến nghị).
"""
import argparse
import os
import sys
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
HTML = HERE / "standalone" / "VNA-Flight-Check-standalone.html"


def open_in_browser():
    if not HTML.exists():
        print(f"❌ Không tìm thấy {HTML}", file=sys.stderr)
        sys.exit(1)
    url = HTML.as_uri()
    print(f"✈  Mở VNA Flight Check trong browser...")
    print(f"   {url}")
    webbrowser.open(url)


def open_in_window():
    try:
        import webview
    except ImportError:
        print("❌ Chưa cài pywebview. Chạy: pip install pywebview", file=sys.stderr)
        sys.exit(1)
    if not HTML.exists():
        print(f"❌ Không tìm thấy {HTML}", file=sys.stderr)
        sys.exit(1)

    webview.create_window(
        "VNA Flight Check",
        str(HTML),
        width=1280,
        height=820,
        min_size=(900, 620),
        resizable=True,
    )
    webview.start(debug=False)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chạy VNA Flight Check local")
    parser.add_argument("--window", action="store_true",
                        help="Mở trong cửa sổ desktop (cần pywebview)")
    args = parser.parse_args()

    if args.window:
        open_in_window()
    else:
        open_in_browser()
