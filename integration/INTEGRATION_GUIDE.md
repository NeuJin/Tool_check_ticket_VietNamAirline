# Integration Guide — VNA Flight Check

Hướng dẫn tích hợp UI mới (web) với codebase Python hiện tại (`main.py`).

`main.py` chứa tất cả business logic cần giữ:
- API clients: `VNADirectAPI`, `AmadeusAPI`, `KiwiAPI`
- Background services: `PriceMonitor`, `ExchangeRate`
- Domain data: `HolidayData`, `Settings`

Chỉ có **tầng GUI Tkinter** (class `App`, `DateRangePicker`, etc.) bị thay thế.

---

## Option A — Pywebview (đơn giản nhất, giữ Python)

Wrap web UI trong một desktop window dùng `pywebview`. Vẫn là một file `.exe` chạy local.

### Cấu trúc
```
vna_flight_check/
├── backend/
│   ├── __init__.py
│   ├── api.py            ← tách VNADirectAPI, AmadeusAPI, KiwiAPI từ main.py
│   ├── monitor.py        ← PriceMonitor
│   ├── exchange.py       ← ExchangeRate
│   ├── holidays.py       ← HolidayData
│   ├── settings.py       ← Settings
│   └── bridge.py         ← JS-callable methods (đối tượng exposed cho pywebview)
├── frontend/
│   └── dist/             ← React build output (Vite)
├── run.py                ← entry point
└── requirements.txt
```

### `backend/bridge.py`
```python
import threading
from .api import VNADirectAPI, AmadeusAPI, KiwiAPI
from .monitor import PriceMonitor
from .exchange import ExchangeRate
from .holidays import HolidayData
from .settings import Settings

class Bridge:
    """Methods exposed to JS via window.pywebview.api.<method>()."""
    def __init__(self):
        self.settings = Settings()
        self.api = VNADirectAPI()  # hoặc theo settings.apiType
        self.monitor = None

    def search_range(self, origin, dest, start_date, end_date, direct_only=False):
        results = self.api.search_range(origin, dest, start_date, end_date, direct_only)
        # Serialize FlightResult instances
        return {
            d: [{
                'date': f.date, 'price': f.price,
                'depTime': f.departure_time, 'arrTime': f.arrival_time,
                'stops': f.stops, 'durationMin': f.duration,
                'flightNum': f.flight_number,
            } for f in (flights or [])]
            for d, flights in results.items()
        }

    def get_exchange_rate(self):
        ExchangeRate.fetch_now()
        return ExchangeRate._rate_vnd_per_jpy

    def save_settings(self, data: dict):
        self.settings.data.update(data)
        self.settings.save()
        return True

    def load_settings(self):
        return dict(self.settings.data)

    def start_monitor(self, searches):
        if self.monitor:
            self.monitor.stop()
        import queue
        q = queue.Queue()
        self.monitor = PriceMonitor(q)
        self.monitor.set_api(self.api)
        self.monitor.set_searches(searches)
        self.monitor.start()
        return True

    def stop_monitor(self):
        if self.monitor: self.monitor.stop()
        return True
```

### `run.py`
```python
import webview
from backend.bridge import Bridge

if __name__ == '__main__':
    bridge = Bridge()
    window = webview.create_window(
        'VNA Flight Check',
        'frontend/dist/index.html',
        js_api=bridge,
        width=1280, height=820,
        min_size=(900, 620),
        resizable=True,
    )
    webview.start(debug=False)
```

### Frontend wiring
Trong React code, thay `mockRangeResults(...)` bằng:
```jsx
async function search(origin, dest, from, to, directOnly) {
  return await window.pywebview.api.search_range(origin, dest, from, to, directOnly);
}
```

### Build
```bash
# Frontend: copy design/ files vào Vite project, build
npm create vite@latest frontend -- --template react
# import các .jsx files, convert sang .jsx ESM modules
npm run build  # → frontend/dist/

# Backend
pip install pywebview requests playwright
python run.py
```

### Ưu nhược
- ✅ Single .exe, không cần web server
- ✅ Giữ toàn bộ Python business logic
- ✅ Native desktop feel
- ❌ Cần đóng gói chromium webview trên Windows (qua Edge WebView2)

---

## Option B — FastAPI server + React (đa platform)

Chạy backend Python local listen `http://127.0.0.1:8765`, React frontend gọi REST.

### Cấu trúc
```
vna_flight_check/
├── backend/  ... (tương tự Option A)
├── server.py
└── frontend/  ... (React/Vite)
```

### `server.py`
```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from backend.api import VNADirectAPI
from backend.exchange import ExchangeRate

app = FastAPI()
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"])
api = VNADirectAPI()

class SearchReq(BaseModel):
    origin: str; dest: str
    start_date: str; end_date: str
    direct_only: bool = False

@app.post("/api/search")
def search(req: SearchReq):
    results = api.search_range(req.origin, req.dest, req.start_date, req.end_date, req.direct_only)
    return {d: [f.__dict__ for f in (fs or [])] for d, fs in results.items()}

@app.get("/api/rate")
def rate():
    ExchangeRate.fetch_now()
    return {"rate": ExchangeRate._rate_vnd_per_jpy}

# Serve frontend build in production
app.mount("/", StaticFiles(directory="frontend/dist", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765)
```

### Frontend wiring
```jsx
async function search(origin, dest, from, to, directOnly) {
  const r = await fetch('http://127.0.0.1:8765/api/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ origin, dest, start_date: from, end_date: to, direct_only: directOnly })
  });
  return r.json();
}
```

### Ưu nhược
- ✅ Có thể chia sẻ qua mạng LAN
- ✅ Frontend/backend tách bạch, dễ test
- ❌ Phải start 2 process
- ❌ Không single .exe (trừ khi đóng gói thêm PyInstaller)

---

## Option C — Tauri (Rust shell, no Python)

Port toàn bộ business logic sang TypeScript/Rust. Build ra binary cực nhẹ (~5-10MB).

Phù hợp nếu muốn distribute rộng và bỏ Python dependency. **Effort cao** — phải rewrite ~2500 dòng Python.

```
src-tauri/
├── src/
│   ├── main.rs
│   └── api/
│       ├── vna_direct.rs   ← port VNADirectAPI sang Rust + reqwest
│       └── ...
└── ...
src/
├── App.tsx                 ← React (copy từ design/)
└── ...
```

Tauri command:
```rust
#[tauri::command]
async fn search_range(origin: String, dest: String, /* ... */) -> Result<...> { ... }
```

Frontend gọi:
```jsx
import { invoke } from '@tauri-apps/api/tauri';
const results = await invoke('search_range', { origin, dest, /* ... */ });
```

### Ưu nhược
- ✅ Tiny binary, native performance
- ✅ Auto-update, code-signing built-in
- ❌ Rewrite hoàn toàn business logic
- ❌ Khó tái dùng `playwright` cho VNA token (phải dùng `headless_chrome` crate hoặc tương đương)

---

## Khuyến nghị

**Bắt đầu với Option A (pywebview)** — đỡ effort nhất, giữ nguyên Python code. Khi nào cần distribute rộng → cân nhắc Tauri.

## Migration steps (Option A khuyến nghị)

1. Tách `main.py` thành các module backend (xem cấu trúc ở trên). Bỏ class `App`, `DateRangePicker`, `DetailPopup`, `NameDialog` (Tkinter).
2. Init Vite React project: `npm create vite@latest frontend -- --template react`
3. Copy các file `.jsx` từ `design/` vào `frontend/src/`, convert sang ESM module syntax (`import`/`export` thay cho `window.X`)
4. Replace `mockRangeResults`, `mockFlights` bằng `window.pywebview.api.search_range(...)`
5. Thêm error handling: API có thể return mảng rỗng nếu token hết hạn → UI hiển thị banner "Đang làm mới token..." + retry
6. Đóng gói: `pyinstaller --onefile --windowed --add-data "frontend/dist:frontend/dist" run.py`

## API endpoints cần expose

| Method | Mục đích |
|---|---|
| `search_range(origin, dest, from, to, direct_only)` | Quét giá theo khoảng ngày |
| `get_exchange_rate()` | Lấy tỷ giá JPY/VND |
| `fetch_vna_token()` | Trigger refresh x-d-token qua playwright |
| `load_settings()` / `save_settings(dict)` | Đọc/ghi settings.json |
| `start_monitor(searches)` / `stop_monitor()` | Bật/tắt background monitor |
| `get_alerts()` | Pull alerts từ monitor queue |
| `save_search(cfg)` / `delete_search(id)` / `list_searches()` | CRUD saved configs |

Tất cả methods đã có tương đương trong `main.py` — chỉ cần wrap.

## Performance notes

- `search_range` đã có `ThreadPoolExecutor(max_workers=6)` → song song 6 ngày một lúc. UI nên gửi progress qua callback (pywebview hỗ trợ `window.evaluate_js` từ Python để push event).
- Để có progress realtime trong pywebview Option A:
  ```python
  def search_range(self, origin, dest, ...):
      def cb(done, total):
          window.evaluate_js(f"window.__searchProgress({done}, {total})")
      return self.api.search_range(..., progress_cb=cb)
  ```
  React side:
  ```jsx
  React.useEffect(() => {
    window.__searchProgress = (done, total) => setProgress({done, total});
    return () => { delete window.__searchProgress; };
  }, []);
  ```

## Security

- Token (x-d-token, Amadeus secret, Kiwi key) lưu trong `~/.vna_tracker/settings.json` — KHÔNG commit. Đảm bảo file permission 600 trên macOS/Linux.
- Không gửi token cho bên thứ ba. UI có dòng "Token được lưu cục bộ" để trấn an user.
- Pywebview chạy local → không expose API ra ngoài. Option B cần bind `127.0.0.1` (KHÔNG bind `0.0.0.0`).
