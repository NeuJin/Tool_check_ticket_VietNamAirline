# Quick Start — Chạy VNA Flight Check local trong 30 giây

## Cách 1 — Double-click (đơn giản nhất)

Mở thư mục `standalone/` → double-click file **`VNA-Flight-Check-standalone.html`**.

App mở trong browser mặc định (Chrome/Edge/Firefox/Safari). Hoạt động 100% offline.

> ✅ Không cần cài gì. File đã chứa tất cả CSS, JS, fonts.
> ⚠ Đây là UI mock — data giả lập, không gọi API thật. Để có data thật xem `integration/INTEGRATION_GUIDE.md`.

## Cách 2 — Desktop window (giống .exe)

Cần Python 3.8+ và pywebview.

```bash
pip install pywebview
```

Sau đó:
- **Windows**: double-click `start.bat`
- **Mac/Linux**: `chmod +x start.sh && ./start.sh`

Hoặc trực tiếp:
```bash
python run_local.py --window
```

Mở cửa sổ desktop riêng 1280×820, không có thanh URL, giống native app.

## Cách 3 — Tích hợp API thật (production)

Đây là design package. Để build app thật có gọi API VNA:

1. Đọc `README.md` (chi tiết design tokens & components)
2. Đọc `integration/INTEGRATION_GUIDE.md` (3 phương án integrate với Python backend)
3. Khuyến nghị: **Option A (pywebview + FastAPI bridge)** — giữ nguyên `main.py` business logic, chỉ thay UI.

## Cấu trúc thư mục

```
design_handoff_vna_flight_check/
├── QUICK_START.md         ← Tài liệu này
├── README.md              ← Design specs đầy đủ
├── run_local.py           ← Python launcher
├── start.bat / start.sh   ← Shortcut launcher
├── standalone/            ← File HTML single-file (mở trực tiếp)
├── design/                ← Source HTML/JSX (reference cho developer)
├── integration/           ← Hướng dẫn tích hợp với Python backend
└── reference/             ← main.py gốc + requirements.txt
```

## Cần help?

Mở Claude Code và prompt: "Implement design package trong folder này — bắt đầu từ Option A trong INTEGRATION_GUIDE.md".
