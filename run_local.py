"""
run_local.py — Chạy VNA Flight Check như một desktop app local.

Cách 1 (đơn giản nhất, không cần thêm gì):
    python run_local.py
→ Mở design/index.html qua HTTP server cục bộ rồi mở browser mặc định.

Cách 2 (desktop window thực sự, không có thanh URL):
    pip install pywebview
    python run_local.py --window
→ Mở trong cửa sổ desktop riêng (1280x820, resizable).

Cách 3 (dùng bundle standalone cũ — fallback nếu cần):
    python run_local.py --standalone
→ Mở file standalone HTML (không nhận được edit JSX mới nhất).

LƯU Ý: Đây mới chỉ là UI thuần (mock data). Để có data thật từ VNA, làm theo
hướng dẫn trong integration/INTEGRATION_GUIDE.md (Option A khuyến nghị).
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
    """Start a local HTTP server serving design/ and return the index URL."""
    if not (DESIGN_DIR / "index.html").exists():
        print(f"❌ Không tìm thấy {DESIGN_DIR / 'index.html'}", file=sys.stderr)
        sys.exit(1)

    port = _find_free_port()

    class Handler(http.server.SimpleHTTPRequestHandler):
        def __init__(self, *args, **kw):
            super().__init__(*args, directory=str(DESIGN_DIR), **kw)

        def end_headers(self):
            # Disable cache so JSX edits show up on refresh
            self.send_header("Cache-Control", "no-store, must-revalidate")
            self.send_header("Pragma", "no-cache")
            self.send_header("Expires", "0")
            super().end_headers()

        def log_message(self, fmt, *args):
            pass  # silence

    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", port), Handler)
    httpd.daemon_threads = True
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    return f"http://127.0.0.1:{port}/index.html"


def open_in_browser(use_standalone: bool = False):
    if use_standalone:
        if not STANDALONE.exists():
            print(f"❌ Không tìm thấy {STANDALONE}", file=sys.stderr)
            sys.exit(1)
        url = STANDALONE.as_uri()
    else:
        url = _start_design_server()

    print(f"✈  Mở VNA Flight Check trong browser...")
    print(f"   {url}")
    webbrowser.open(url)

    if not use_standalone:
        print("   (HTTP server đang chạy — đóng cửa sổ này để dừng)")
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

    if use_standalone:
        if not STANDALONE.exists():
            print(f"❌ Không tìm thấy {STANDALONE}", file=sys.stderr)
            sys.exit(1)
        url = str(STANDALONE)
    else:
        url = _start_design_server()

    webview.create_window(
        "VNA Flight Check",
        url,
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
    parser.add_argument("--standalone", action="store_true",
                        help="Dùng bundle standalone cũ thay vì design/ live")
    args = parser.parse_args()

    if args.window:
        open_in_window(use_standalone=args.standalone)
    else:
        open_in_browser(use_standalone=args.standalone)
