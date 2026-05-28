"""
run_local.py — Chạy VNA Flight Check như desktop app.

Cách 1 (KHUYẾN NGHỊ — desktop window + API VNA thật):
    pip install pywebview requests
    python run_local.py --window
→ Mở trong pywebview với Python Bridge → JS gọi window.pywebview.api.* để lấy
  dữ liệu giá vé thật từ Vietnam Airlines.

Cách 2 (mở browser, chỉ UI mock — KHÔNG có API thật vì không có bridge):
    python run_local.py
→ HTTP server serve design/ qua http://127.0.0.1:8765/. JS không gọi được
  Python backend ở chế độ này (window.pywebview không tồn tại) — UI sẽ rơi
  về mock data.

Cách 3 (bundle standalone cũ):
    python run_local.py --standalone

LƯU Ý: Lần đầu mở Settings cần paste x-d-token từ DevTools (booking.vietnamairlines.com).
"""
import argparse
import http.server
import os
import socket
import socketserver
import sys
import threading
import webbrowser
from pathlib import Path

HERE = Path(__file__).resolve().parent
DESIGN_DIR = HERE / "design"
STANDALONE = HERE / "standalone" / "VNA-Flight-Check-standalone.html"


def _find_free_port(preferred: int = 8765) -> int:
    for port in (preferred, 8766, 8767, 8080, 0):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.bind(("127.0.0.1", port))
                return s.getsockname()[1]
        except OSError:
            continue
    return preferred


def _start_design_server() -> str:
    if not (DESIGN_DIR / "index.html").exists():
        print(f"❌ Không tìm thấy {DESIGN_DIR / 'index.html'}", file=sys.stderr)
        sys.exit(1)

    port = _find_free_port()

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kw):
            super().__init__(*args, directory=str(DESIGN_DIR), **kw)

        def end_headers(self):
            self.send_header("Cache-Control", "no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            super().end_headers()

        def log_message(self, fmt, *args):
            pass

    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", port), Handler)
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return f"http://127.0.0.1:{port}/index.html"


def open_in_browser(use_standalone: bool = False):
    if use_standalone:
        if not STANDALONE.exists():
            print(f"❌ Không tìm thấy {STANDALONE}", file=sys.stderr)
            sys.exit(1)
        url = STANDALONE.as_uri()
    else:
        url = _start_design_server()
        print("⚠  Chế độ browser KHÔNG có cầu nối Python — UI sẽ chạy với mock data.")
        print("   Để xem giá vé thật, dùng:  python run_local.py --window")

    print(f"✈  Mở VNA Flight Check trong browser...")
    print(f"   {url}")
    webbrowser.open(url)

    if not use_standalone:
        try:
            threading.Event().wait()
        except KeyboardInterrupt:
            pass


def open_in_window(use_standalone: bool = False):
    try:
        import webview
    except ImportError:
        print("❌ Chưa cài pywebview. Chạy: pip install pywebview", file=sys.stderr)
        sys.exit(1)

    # Build the JS-callable bridge that exposes Python backend to React UI
    from backend.bridge import Bridge
    bridge = Bridge()

    if use_standalone:
        if not STANDALONE.exists():
            print(f"❌ Không tìm thấy {STANDALONE}", file=sys.stderr)
            sys.exit(1)
        url = str(STANDALONE)
    else:
        # Still start the HTTP server (Babel needs to fetch JSX files; file:// is blocked)
        url = _start_design_server()
        print(f"   Serving design/ via {url}")

    print("✈  Mở VNA Flight Check (pywebview + Python backend)")
    webview.create_window(
        "VNA Flight Check",
        url,
        js_api=bridge,
        width=1320,
        height=860,
        min_size=(900, 620),
        resizable=True,
    )
    webview.start(debug=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Chạy VNA Flight Check local")
    parser.add_argument("--window", action="store_true",
                        help="Mở trong cửa sổ desktop pywebview + Python backend (khuyến nghị)")
    parser.add_argument("--standalone", action="store_true",
                        help="Dùng bundle standalone cũ")
    args = parser.parse_args()

    if args.window:
        open_in_window(use_standalone=args.standalone)
    else:
        open_in_browser(use_standalone=args.standalone)
