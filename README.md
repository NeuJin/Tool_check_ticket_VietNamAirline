# Handoff: VNA Flight Check — GUI Redesign

> Tài liệu bàn giao thiết kế cho developer (Claude Code).
> Bộ này gồm **prototype HTML hi-fi** + **hướng dẫn tích hợp** với codebase Python hiện tại (`main.py`).

---

## 1. Tổng quan

**VNA Flight Check** là tool theo dõi giá vé máy bay (route VN ↔ JP, nội địa VN). Codebase hiện tại là một **Tkinter desktop app** (`main.py`, ~2500 dòng) gồm:

- Tầng API: `VNADirectAPI`, `AmadeusAPI`, `KiwiAPI` (gọi REST, parse JSON)
- Tầng business: `PriceMonitor` (background thread), `ExchangeRate`, `HolidayData`
- Tầng GUI (Tkinter): 5 tab — Search · Results · Combo · Monitor · Settings

Bộ handoff này redesign **toàn bộ tầng GUI** thành web app responsive hiện đại. Backend Python giữ nguyên — chỉ cần thay UI và expose qua local HTTP bridge.

## 2. Về các file trong bundle

**Quan trọng:** Các file HTML/JSX trong thư mục `design/` là **design reference** — prototype thể hiện look & feel và behavior, KHÔNG phải code production để copy thẳng.

Nhiệm vụ là **recreate các thiết kế HTML này trong môi trường của codebase mục tiêu**:
- Nếu giữ Python + native desktop → port sang **PySide6/Qt** hoặc dùng **pywebview** wrap web UI
- Nếu chuyển sang Electron/Tauri → giữ JSX nhưng convert sang React build chuẩn (Vite + TypeScript)
- Nếu chuyển sang web app server → Flask/FastAPI + serve React build

Xem `integration/INTEGRATION_GUIDE.md` để biết các phương án cụ thể.

## 3. Fidelity

**Hi-fi**: Đầy đủ màu sắc, typography, spacing, micro-interactions. Hex chính xác. Developer cần recreate pixel-perfect bằng library/pattern có sẵn của codebase mục tiêu.

## 4. Các màn hình (Screens)

App có **1 single-page với 5 tab**. Tab navigation ở thanh header sticky trên cùng.

### 4.1 Header (chung mọi tab)

- **Layout**: Sticky top, `position: sticky; top: 0; z-index: 50`
  - Background: `linear-gradient(180deg, rgba(255,255,255,.92), rgba(255,255,255,.78))` + `backdrop-filter: saturate(180%) blur(14px)`
  - Border bottom: `1px solid #E2E8F0`
  - Inner max-width: `1320px`, padding `14px 28px`, flex row
- **Brand block** (trái): mark icon 36×36 gradient `linear-gradient(135deg, #0EA5E9, #0369A1 70%, #112B4D)` border-radius 11px + title "VNA Flight Check" / subtitle "THEO DÕI & SĂN VÉ RẺ" uppercase 11px
- **Nav** (giữa, ml-auto): 5 button trong segmented container, active button có background white + box-shadow nhẹ
- **Status pill** (phải): chấm tròn `8px` (green/yellow/grey) + text "Sẵn sàng" / "Đang quét..." / "Theo dõi bật"

### 4.2 Tab — Tìm chuyến bay

**Mục đích**: User chọn route + khoảng ngày + tùy chọn, sau đó bấm Tìm.

**Layout**:
- Card 1 (form): padding `18px 22px 22px`, border-radius 14px, border `1px solid #E2E8F0`
  - **Card head**: tiêu đề "Tìm chuyến bay rẻ nhất" (700, 15px) + subtitle (12.5px text-2) + **segmented control "Một chiều / Khứ hồi"** (right)
  - **Route row**: `grid-template-columns: 1fr auto 1fr`, gap 12px
    - Airport picker × 2 (custom combobox): card 64px tall, icon 38×38 left, label nhỏ uppercase + code 20px bold + subtitle nhỏ
    - Swap button ở giữa: nút tròn 40×40, hover → rotate(180deg), background → `#0EA5E9` color white
  - **Date row** (margin-top 16px): grid 2 cột (1 cột nếu OW)
    - "Date range button": 64px tall, icon 38×38 + label uppercase + value `dd/mm/yyyy → dd/mm/yyyy (N đêm)` font-weight 700
    - Click → mở **Calendar modal** (xem 4.7)
    - Return leg có tint hồng nhẹ (`#FEF3F2` icon background)
  - **Options row** (margin-top 16px): `grid-template-columns: repeat(auto-fit, minmax(220px, 1fr))`, gap 10px
    - Optcard "Bay thẳng" (toggle checkbox card, 22×22 check)
    - Optcard "Hành khách" với stepper (− 1 +)
    - Optcard "Tự động làm mới mỗi 15 phút" (toggle)
  - **Action row**: button primary `Tìm giá rẻ nhất` (height 48px, gradient `linear-gradient(180deg, #0EA5E9, #0284C7)`, shadow `0 6px 16px -6px rgba(14,165,233,.5)`) + button ghost "Lưu cấu hình" + progress bar (hiển thị khi đang quét)
- Card 2 (tips): info icon + text mẹo, background nhẹ

### 4.3 Tab — Kết quả giá

**Empty state** (khi chưa search): card centered, plane icon 48px opacity .3, message + CTA "Đi tới tìm kiếm".

**Khi có data**:
- **KPI grid** (`grid-template-columns: repeat(auto-fit, minmax(180px, 1fr))`, gap 12px):
  - Card "Giá rẻ nhất chuyến đi" — variant `--best` (gradient `linear-gradient(135deg, #0284C7, #075985 90%)`, text white)
  - Card "Rẻ nhất chuyến về"
  - Card "Tổng cộng" (variant `--total`, value màu sky-700)
  - Card "Đã quét"
  - Mỗi card: label uppercase 11.5px + value mono 22px 800 + subtitle 12px
- **Toolbar**: segmented currency `VND | JPY | Cả hai` + pill tỷ giá + segmented `Chuyến đi | Chuyến về` (nếu RT) + button "Quét lại"
- **Price chart**: SVG bar chart full-width, height 200px
  - Bars màu: green (`#10B981` rẻ), sky (`#38BDF8` TB), warn (`#F59E0B` đắt), dashed border cho ngày không có chuyến
  - Average line dashed sky-300
  - Holiday dot 3px ở dưới mỗi cột tương ứng ngày lễ
  - Tooltip on hover: navy-900 background, white text, arrow xuống
- **Flight table**: grid rows
  - `grid-template-columns: 130px 1fr 100px 100px 110px 120px` (date | tags | stops | flightNum | dep-arr | price)
  - Best row: variant `--best` (border green, gradient white→green-50, shadow xanh)
  - Hover: border sky-400, translateY(-1px), shadow xanh
  - Tags: "Rẻ nhất" (green pill star), "Giá tốt", "Trung bình", "Bay thẳng" (sky), holiday tags

### 4.4 Tab — Khứ hồi tối ưu

**Empty state**: yêu cầu chuyển sang Khứ hồi.

**Khi có data**:
- **Controls card**: 2 spinbox `Tối thiểu` / `Tối đa` (số đêm hoặc giờ) + segmented đơn vị `Ngày | Giờ` + segmented sort `Tổng giá | Ngày đi | Số đêm` + pill "X tổ hợp khả thi"
- **Hero card "Best combo"**: `grid-template-columns: 1fr auto 1fr auto`, gap 24px, background gradient navy + radial overlays
  - Cột 1: "✈ Chuyến đi" label / ngày bold 22px / chi tiết (flight, time, price)
  - Arrow 56×56 tròn semi-transparent ở giữa
  - Cột 2: "↩ Chuyến về" (tương tự)
  - Cột 3 (right-align): "Tổng rẻ nhất" + value mono 32px 800 + "X đêm · tiết kiệm Y vs top 10"
- **Combo list table**: header row uppercase 11px text-3, rows grid 6 cột; top 3 có variant `--top` (border green, gradient white→green-50). Hiển thị tối đa 50, footer note "+N tổ hợp khác đã ẩn".

### 4.5 Tab — Theo dõi giá

- **Control panel card**: 2 input spinbox (tần suất kiểm tra phút / khoảng cách thông báo phút) + 2 toggle optcard + nút primary "Bắt đầu / Dừng theo dõi"
- **Alerts list**: alertcard có icon 36×36 left + title bold + body + time, variant `--good` (border green, gradient green tint) cho price drop, `--info` cho periodic
- **Saved searches table**: rows với toggle switch (38×22, slide animation) + name + lastPrice + route badge (CODE → CODE) + dates + type tag + direct tag + actions (eye / trash)

### 4.6 Tab — Cài đặt

- **API source selector**: 3 optcard ngang (VNA Direct / Amadeus / Kiwi), card check radio kiểu
- **Settings grid** 2 cột (`@media min-width: 920px`):
  - Card "VNA Direct — Token": password input + eye toggle + status row + info row
  - Card "Amadeus API": Client ID + Secret + test button
  - Card "Kiwi Tequila API": API key + test button
  - Card "Tỷ giá": rate display + manual fallback input
- **About card**: brand mark + version + disclaimer

### 4.7 Calendar Modal (Date Range Picker)

**Trigger**: click vào date range button trong Search tab.

**Layout**: overlay `rgba(11,31,58,.4)` + `backdrop-filter: blur(4px)`. Modal card 720px wide, animation `scaleIn 0.22s`.

- **Header**: gradient `linear-gradient(135deg, #0369A1, #112B4D)`, white text, padding 16px 20px. Left: instruction text ("Chọn ngày bắt đầu" → "Chọn ngày kết thúc" → "Khoảng đã chọn"). Right: rangeLabel (`dd/mm/yyyy → dd/mm/yyyy (N đêm)`).
- **Options row**: 3 checkbox toggle lịch nghỉ:
  - `3 kỳ lớn Nhật` (GW · Obon · Tết JP) — màu `#EA580C`
  - `Lễ Nhật` — màu `#FED7AA` background `#EA580C` text
  - `Lễ VN` — màu `#FECACA` background `#DC2626` text
  - Right side: 4 quick preset chips ("Tuần tới", "2 tuần tới", "Tháng tới", "Cuối tuần này")
- **2 months side-by-side**: grid 2 columns. Mỗi tháng có chevron nav, day-of-week header (T2 T3 T4 T5 T6 T7 CN — CN màu đỏ), cells grid 7 cột.
  - Cell: 1:1 aspect, border-radius 8px, font-size 13px
  - **Priority màu** (cao → thấp): selected → range → today (inset ring) → JP big → JP holiday → VN holiday → past (text-3) → sunday (red text) → normal
  - Hover non-past: background sky-100
  - Selected start/end: sky-600 background, white text, shadow
  - In-range: sky-100 background sky-900 text
- **Legend bar**: 6 chip nhỏ mô tả ý nghĩa màu
- **Footer**: status text (hover holiday name) + ghost "Xóa chọn" + ghost "Hủy" + primary "Xác nhận" (disabled nếu chưa chọn start)

## 5. Interactions & Behavior

- **Tab switch**: instant, sync với `state.activeTab`
- **Search execution**:
  - Set `searching: true`, progress = 0
  - Tính `total = depDays + retDays` ngày
  - Loop 1..total: sleep 15-40ms + cập nhật `progressDone, progress`
  - Khi xong: set `outResults, retResults`, switch sang tab Results
- **Airport picker dropdown**: click ngoài để đóng (mousedown listener), search input filter theo code/city/name
- **Swap button**: rotate 180° animation 0.25s
- **Date range click**: open calendar modal, focus trap, ESC để đóng (TODO)
- **Calendar phase machine**: 0 (chọn start) → 1 (chọn end, hover preview range) → 2 (đã chọn cả 2, click lại để reset start)
- **Currency switch (Results tab)**: re-render giá realtime
- **Chart bar click**: highlight ngày tương ứng trong flight table
- **Monitor toggle**: chuyển button primary ↔ danger, status pill green ↔ grey
- **Saved search toggle (switch component)**: thumb slide right, background sky-500

## 6. State Management

```js
{
  // form
  origin, dest, tripType: 'OW'|'RT',
  depFrom, depTo, retFrom, retTo,  // YYYY-MM-DD strings
  directOnly, pax, autoRefresh, refreshInterval,

  // results
  outResults: { 'YYYY-MM-DD': FlightResult[], ... } | null,
  retResults: { ... } | null,
  currency: 'VND'|'JPY'|'BOTH',
  exchangeRate, fallbackRate,
  searching, progress, progressDone, progressTotal,
  lastSearch,

  // combo
  minLayover, maxLayover, layoverUnit,

  // monitor
  monitorOn, monitorInterval, notifyInterval,
  notifyDrop, notifyPeriodic,
  alerts: [{ id, kind: 'good'|'info', title, body, time }],

  // settings
  apiType: 'vna_direct'|'amadeus'|'kiwi',
  xdToken, amadeusId, amadeusSecret, kiwiKey,

  // saved
  savedSearches: [{ id, name, active, lastPrice, cfg: {...} }],

  activeTab,
}
```

Single React `useState` ở root, prop drill xuống các tab. Mock data generator có sẵn (`mockRangeResults`) — thay bằng API call thật khi tích hợp.

## 7. Design Tokens

### Colors
```
/* Sky (primary, accent) */
--sky-50:  #F0F9FF
--sky-100: #E0F2FE
--sky-200: #BAE6FD
--sky-300: #7DD3FC
--sky-400: #38BDF8
--sky-500: #0EA5E9   /* brand primary */
--sky-600: #0284C7
--sky-700: #0369A1
--sky-800: #075985
--sky-900: #0C4A6E

/* Ink (navy, depth) */
--ink-900: #0B1F3A
--ink-800: #112B4D
--ink-700: #1E3A5F

/* Neutrals (cool slate) */
--bg:        #F4F7FB
--surface:   #FFFFFF
--surface-2: #F8FAFC
--line:      #E2E8F0
--line-2:    #CBD5E1
--text:      #0F172A
--text-2:    #475569
--text-3:    #94A3B8

/* Status */
--good: #10B981  / good-bg: #D1FAE5
--warn: #F59E0B  / warn-bg: #FEF3C7
--bad:  #EF4444  / bad-bg:  #FEE2E2

/* Holiday accents */
--jp-big:  #EA580C  (kỳ lớn Nhật)
--jp-soft: #FED7AA  (lễ Nhật)
--vn-soft: #FECACA  (lễ VN)
--vn-big:  #DC2626
```

### Spacing
4px grid. Common: 6, 8, 10, 12, 14, 16, 18, 20, 22, 24, 28px.

### Typography
- **UI**: `Plus Jakarta Sans` weights 400/500/600/700/800
- **Mono** (prices, codes): `JetBrains Mono` weights 400/500/600
- Base font-size: 15px / line-height 1.5
- Scale: 11px (micro caps), 12px (hint), 12.5px (sub), 13.5px (label), 14px (input), 15px (body), 16px (brand), 17-22px (KPI), 32px (combo total)

### Radius
- Small: 7-10px (chips, toggles, small buttons)
- Default: 12-14px (cards, buttons, inputs)
- Large: 16-20px (modal, hero cards)
- Pill: 999px

### Shadows
```
--shadow-sm: 0 1px 2px rgba(15,23,42,.04), 0 1px 1px rgba(15,23,42,.03);
--shadow:    0 4px 16px -4px rgba(11,31,58,.08), 0 2px 4px -2px rgba(11,31,58,.04);
--shadow-lg: 0 20px 50px -20px rgba(11,31,58,.25), 0 8px 16px -8px rgba(11,31,58,.10);
```

## 8. Assets

Không có asset external. Mọi icon đều inline SVG (Lucide-style, stroke 2). Logo chỉ là plane SVG trong gradient square.

Khi port qua framework khác, dùng **lucide-react** hoặc tương đương:
- `Plane`, `Search`, `List`, `RotateCw`, `Bell`, `Settings`, `Calendar`, `ArrowLeftRight`, `Check`, `X`, `ChevronLeft`, `ChevronRight`, `TrendingDown`, `Eye`, `EyeOff`, `Trash`, `Save`, `Play`, `Pause`, `Info`, `Zap`, `Copy`, `Star`

## 9. Files trong bundle

```
design_handoff_vna_flight_check/
├── README.md                         ← Tài liệu này
├── design/                           ← Prototype HTML (reference)
│   ├── index.html                    Entry, load order các script
│   ├── styles.css                    Tokens + tất cả styling (~840 dòng)
│   ├── app.jsx                       Root component + state + tweaks
│   ├── shared.jsx                    Airports, formatters, holidays, mock data, icons
│   ├── calendar.jsx                  CalendarPicker modal
│   ├── search-tab.jsx                SearchTab + AirportPicker
│   ├── results-tab.jsx               ResultsTab + PriceChart + FlightRow
│   ├── combo-tab.jsx                 ComboTab
│   ├── monitor-tab.jsx               MonitorTab
│   ├── settings-tab.jsx              SettingsTab
│   └── tweaks-panel.jsx              Tweaks UI (có thể bỏ khi production)
├── standalone/
│   └── VNA-Flight-Check-standalone.html  ← Single-file build, double-click chạy được
├── integration/
│   └── INTEGRATION_GUIDE.md          ← 3 phương án integrate với main.py
└── reference/
    └── main.py                        ← Source Python gốc (để dev hiểu business logic)
```

## 10. Lưu ý

- **Branding**: Tên "VNA Flight Check" là tên TOOL độc lập, không phải sản phẩm chính thức của Vietnam Airlines. KHÔNG dùng logo lotus, KHÔNG dùng màu vàng VNA gốc. Palette sky/navy ở đây là **original**.
- **Mock data**: `mockRangeResults` trong `shared.jsx` tạo dữ liệu giả deterministic theo route+date. Khi tích hợp thật, thay bằng API call (xem `INTEGRATION_GUIDE.md`).
- **Calendar holidays**: dữ liệu lễ chỉ approximate (Tết VN hardcoded 2026-2027). Nên dùng `python-lunardate` hoặc thư viện chuyên dụng cho production.
- **Responsive**: breakpoint 1180px (nav nén), 920px (icon-only nav + table compact), 720px (mobile single column).
