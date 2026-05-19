#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vietnam Airlines Flight Price Tracker
======================================
Theo dõi và thông báo giá vé máy bay Vietnam Airlines.
Nguồn dữ liệu: VNA trực tiếp hoặc Amadeus API (miễn phí).
"""

import tkinter as tk
from tkinter import ttk, messagebox
import json
import threading
import time
import os
import subprocess
import queue
import sys
import re
import calendar as _cal
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta, date as _date
from pathlib import Path
from typing import List, Dict, Optional, Tuple

try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_OK = True
except ImportError:
    PLAYWRIGHT_OK = False

try:
    import requests
except ImportError:
    print("Thiếu thư viện 'requests'. Chạy: pip install requests")
    sys.exit(1)

# ─── Constants ────────────────────────────────────────────────────────────────

APP_NAME  = "VNA Flight Price Tracker"
VERSION   = "1.0"
SETTINGS_FILE = Path.home() / ".vna_tracker" / "settings.json"

VNA_AIRPORTS = {
    # ── Việt Nam ──────────────────────────────────────────────────────────────
    "HAN": "🇻🇳 Hà Nội (Nội Bài)",
    "SGN": "🇻🇳 TP.HCM (Tân Sơn Nhất)",
    "DAD": "🇻🇳 Đà Nẵng",
    "CXR": "🇻🇳 Nha Trang (Cam Ranh)",
    "PQC": "🇻🇳 Phú Quốc",
    "VCA": "🇻🇳 Cần Thơ",
    "VII": "🇻🇳 Vinh",
    "HUI": "🇻🇳 Huế (Phú Bài)",
    "VDH": "🇻🇳 Đồng Hới",
    "BMV": "🇻🇳 Buôn Ma Thuột",
    "UIH": "🇻🇳 Quy Nhơn (Phù Cát)",
    "TBB": "🇻🇳 Tuy Hòa",
    "VKG": "🇻🇳 Rạch Giá",
    "CAH": "🇻🇳 Cà Mau",
    "DIN": "🇻🇳 Điện Biên",
    "DLI": "🇻🇳 Đà Lạt",
    "HPH": "🇻🇳 Hải Phòng (Cát Bi)",
    "THD": "🇻🇳 Thanh Hóa",
    "VCS": "🇻🇳 Côn Đảo",
    # ── Nhật Bản ─────────────────────────────────────────────────────────────
    "NRT": "🇯🇵 Tokyo (Narita)",
    "HND": "🇯🇵 Tokyo (Haneda)",
    "KIX": "🇯🇵 Osaka (Kansai)",
    "NGO": "🇯🇵 Nagoya (Centrair)",
    "FUK": "🇯🇵 Fukuoka",
    "CTS": "🇯🇵 Sapporo (Chitose)",
    "OKA": "🇯🇵 Okinawa (Naha)",
}

AIRPORT_LABELS = [f"{c} - {n}" for c, n in VNA_AIRPORTS.items()]

DEFAULT_SETTINGS = {
    "api_type": "vna_direct",
    "amadeus_client_id": "",
    "amadeus_client_secret": "",
    "kiwi_api_key": "",
    "monitor_interval_minutes": 60,
    "min_layover_value": 1,
    "max_layover_value": 30,
    "min_layover_unit": "days",   # "hours" or "days"
    "notify_on_price_drop": True,
    "notify_periodically": True,
    "notify_interval_minutes": 120,
    "currency": "VND",
    "searches": [],
}


# ─── API Layer ────────────────────────────────────────────────────────────────

class FlightResult:
    __slots__ = ("date", "price", "departure_time", "arrival_time",
                 "stops", "duration", "flight_number")

    def __init__(self, date, price, departure_time="", arrival_time="",
                 stops=0, duration="", flight_number=""):
        self.date          = date
        self.price         = price
        self.departure_time = departure_time
        self.arrival_time  = arrival_time
        self.stops         = stops
        self.duration      = duration
        self.flight_number = flight_number


class FlightAPI:
    """Base class – provides search_range on top of search."""

    name = "Base"

    def search(self, origin: str, destination: str, date: str,
               direct_only: bool = False) -> List[FlightResult]:
        raise NotImplementedError

    def search_range(self, origin: str, destination: str,
                     start_date: str, end_date: str,
                     direct_only: bool = False,
                     progress_cb=None,
                     max_workers: int = 6) -> Dict[str, Optional[List[FlightResult]]]:
        """Parallel date search – 6 ngày đồng thời, nhanh hơn ~5x so với tuần tự."""
        current = datetime.strptime(start_date, "%Y-%m-%d")
        end     = datetime.strptime(end_date,   "%Y-%m-%d")
        dates   = []
        while current <= end:
            dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)

        results: Dict[str, Optional[List[FlightResult]]] = {}
        done_count = [0]
        lock = threading.Lock()

        def fetch(ds: str):
            try:
                return ds, self.search(origin, destination, ds, direct_only) or []
            except Exception:
                return ds, []

        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(fetch, ds): ds for ds in dates}
            for future in as_completed(futures):
                ds, flights = future.result()
                results[ds] = flights
                with lock:
                    done_count[0] += 1
                    if progress_cb:
                        progress_cb(done_count[0], len(dates))

        return results


class VNADirectAPI(FlightAPI):
    """
    Gọi trực tiếp API booking của vietnamairlines.com.
    Endpoint và credentials được extract từ network analysis của trang web chính thức.
    Không cần đăng ký – dùng guest token của VNA.
    """
    name = "VNA Direct"
    GATEWAY    = "https://api-des.vietnamairlines.com"
    TOKEN_URL  = f"{GATEWAY}/v1/security/oauth2/token/initialization"
    SEARCH_URL = f"{GATEWAY}/v2/search/air-bounds"
    # client_id và client_secret được embed trong HTML của trang booking VNA
    CLIENT_ID  = "7yA9XUB34tvB8vahz5O3CFVdGmdKT9au"
    CLIENT_SECRET = "vlaA0atz4fjdyEQZ"

    _token: Optional[str] = None
    _token_expiry: float  = 0.0
    _token_lock = threading.Lock()
    x_d_token: str = ""

    @classmethod
    def reset_token(cls):
        with cls._token_lock:
            cls._token = None
            cls._token_expiry = 0.0

    HEADERS = {
        "User-Agent":      ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0"),
        "Accept":          "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type":    "application/json",
        "Origin":          "https://booking.vietnamairlines.com",
        "Referer":         "https://booking.vietnamairlines.com/",
    }

    @classmethod
    def _get_token(cls) -> Optional[str]:
        with cls._token_lock:
            if cls._token and time.time() < cls._token_expiry - 60:
                return cls._token
            try:
                hdrs = {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin":       "https://booking.vietnamairlines.com",
                    "Referer":      "https://booking.vietnamairlines.com/",
                    "User-Agent":   ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                                     "AppleWebKit/537.36 (KHTML, like Gecko) "
                                     "Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0"),
                }
                if cls.x_d_token:
                    hdrs["x-d-token"] = cls.x_d_token
                import json as _json
                fact = _json.dumps({
                    "keyValuePairs": [
                        {"key": "countryCode", "value": "JP"},
                        {"key": "language",    "value": "ja-JP"},
                    ]
                }, separators=(',', ':'))
                r = requests.post(
                    cls.TOKEN_URL,
                    data={
                        "grant_type":    "client_credentials",
                        "client_id":     cls.CLIENT_ID,
                        "client_secret": cls.CLIENT_SECRET,
                        "fact":          fact,
                    },
                    headers=hdrs,
                    timeout=12,
                )
                if r.ok:
                    d = r.json()
                    cls._token = d.get("access_token")
                    cls._token_expiry = time.time() + d.get("expires_in", 1799)
                    return cls._token
            except Exception:
                pass
            return None

    def search(self, origin: str, destination: str, date: str,
               direct_only: bool = False) -> List[FlightResult]:
        token = self._get_token()
        if not token:
            return []

        body = {
            "commercialFareFamilies": ["WEB"],
            "itineraries": [{
                "departureDateTime":     f"{date}T00:00:00.000",
                "originLocationCode":      origin,
                "destinationLocationCode": destination,
                "isRequestedBound":        True,
            }],
            "searchPreferences": {"showMilesPrice": False},
            "travelers": [{"passengerTypeCode": "ADT"}],
        }
        headers = {**self.HEADERS, "Authorization": f"Bearer {token}"}
        if self.x_d_token:
            headers["x-d-token"] = self.x_d_token
        try:
            r = requests.post(self.SEARCH_URL, json=body, headers=headers, timeout=20)
            if not r.ok:
                return []
            return self._parse(r.json(), date, direct_only)
        except Exception:
            return []

    def _parse(self, resp: dict, date: str, direct_only: bool) -> List[FlightResult]:
        data    = resp.get("data", {})
        flights = resp.get("dictionaries", {}).get("flight", {})
        results = []

        for group in data.get("airBoundGroups", []):
            bd       = group.get("boundDetails", {})
            segments = bd.get("segments", [])
            stops    = len(segments) - 1
            if direct_only and stops > 0:
                continue

            # Lấy offer rẻ nhất trong group
            cheapest = None
            for ab in group.get("airBounds", []):
                prices = ab.get("prices", {}).get("totalPrices", [])
                if not prices:
                    continue
                total_jpy = prices[0].get("total", 0)
                if total_jpy <= 0:
                    continue
                if cheapest is None or total_jpy < cheapest[0]:
                    cheapest = (total_jpy, ab, segments)

            if cheapest is None:
                continue

            total_jpy, ab, segs = cheapest
            # Chuyển JPY → VND để lưu nội bộ (dùng exchange rate hiện tại)
            rate = ExchangeRate.jpy_to_vnd(1)
            price_vnd = int(total_jpy * rate) if rate else int(total_jpy * 170)

            dep_info = flights.get(segs[0].get("flightId", ""), {})
            arr_info = flights.get(segs[-1].get("flightId", ""), {})
            dep_dt   = dep_info.get("departure", {}).get("dateTime", "")
            arr_dt   = arr_info.get("arrival",   {}).get("dateTime", "")
            dep_time = dep_dt[11:16] if len(dep_dt) > 11 else ""
            arr_time = arr_dt[11:16] if len(arr_dt) > 11 else ""

            nums = []
            for s in segs:
                fi = flights.get(s.get("flightId", ""), {})
                n  = fi.get("marketingFlightNumber", "")
                al = fi.get("marketingAirlineCode", "VN")
                if n:
                    nums.append(f"{al}{n}")
            flight_num = "/".join(nums) or "VN"

            results.append(FlightResult(
                date           = date,
                price          = price_vnd,
                departure_time = dep_time,
                arrival_time   = arr_time,
                stops          = stops,
                duration       = bd.get("duration", 0) // 60,
                flight_number  = flight_num,
            ))

        return results


class AmadeusAPI(FlightAPI):
    """
    Amadeus Flight Offers API – bao gồm Vietnam Airlines (mã VN).
    Đăng ký miễn phí: https://developers.amadeus.com
    """
    name = "Amadeus"
    AUTH_URL   = "https://test.api.amadeus.com/v1/security/oauth2/token"
    SEARCH_URL = "https://test.api.amadeus.com/v2/shopping/flight-offers"

    def __init__(self, client_id: str, client_secret: str):
        self.client_id     = client_id
        self.client_secret = client_secret
        self._token        = None
        self._token_expiry = 0.0

    def _get_token(self) -> str:
        if self._token and time.time() < self._token_expiry:
            return self._token
        r = requests.post(self.AUTH_URL, data={
            "grant_type":    "client_credentials",
            "client_id":     self.client_id,
            "client_secret": self.client_secret,
        }, timeout=10)
        r.raise_for_status()
        d = r.json()
        self._token        = d["access_token"]
        self._token_expiry = time.time() + d["expires_in"] - 30
        return self._token

    def search(self, origin: str, destination: str, date: str,
               direct_only: bool = False) -> List[FlightResult]:
        try:
            params: Dict = {
                "originLocationCode":      origin,
                "destinationLocationCode": destination,
                "departureDate":           date,
                "adults":                  1,
                "includedAirlineCodes":    "VN",
                "max":                     20,
                "currencyCode":            "VND",
            }
            if direct_only:
                params["nonStop"] = "true"
            r = requests.get(
                self.SEARCH_URL,
                headers={"Authorization": f"Bearer {self._get_token()}"},
                params=params,
                timeout=15,
            )
            r.raise_for_status()
            offers = r.json().get("data", [])
        except Exception:
            return []

        results = []
        for offer in offers:
            try:
                price = float(offer["price"]["grandTotal"])
                itin  = offer["itineraries"][0]
                segs  = itin["segments"]
                dep   = segs[0]["departure"].get("at", "")
                arr   = segs[-1]["arrival"].get("at", "")
                dur   = itin.get("duration", "")
                fn    = segs[0]["carrierCode"] + segs[0]["number"]
                results.append(FlightResult(
                    date=date, price=price,
                    departure_time=dep, arrival_time=arr,
                    stops=len(segs) - 1,
                    duration=dur, flight_number=fn,
                ))
            except Exception:
                continue
        return sorted(results, key=lambda x: x.price)


class KiwiAPI(FlightAPI):
    """
    Kiwi.com Tequila API – miễn phí, có VNA (mã VN).
    Đăng ký API key tại: tequila.kiwi.com  → My account → Add API key
    """
    name = "Kiwi Tequila"
    SEARCH_URL = "https://tequila.kiwi.com/v2/search"

    def __init__(self, api_key: str):
        self.api_key = api_key

    def search(self, origin: str, destination: str, date: str,
               direct_only: bool = False) -> List[FlightResult]:
        try:
            dt = datetime.strptime(date, "%Y-%m-%d")
            params = {
                "fly_from":       origin,
                "fly_to":         destination,
                "date_from":      dt.strftime("%d/%m/%Y"),
                "date_to":        dt.strftime("%d/%m/%Y"),
                "adults":         1,
                "curr":           "VND",
                "select_airlines":"VN",
                "select_airlines_exclude": 0,
                "max_stopovers":  0 if direct_only else 2,
                "limit":          20,
                "sort":           "price",
                "asc":            1,
                "partner_market": "vn",
            }
            r = requests.get(
                self.SEARCH_URL,
                headers={"apikey": self.api_key},
                params=params,
                timeout=15,
            )
            r.raise_for_status()
            data = r.json()
        except Exception:
            return []

        results = []
        for it in data.get("data", []):
            try:
                price   = float(it["price"])
                dep_at  = it.get("local_departure", "")
                dur_sec = it.get("duration", {}).get("total", 0)
                h, m    = divmod(int(dur_sec) // 60, 60)
                dur_str = f"{h}h{m:02d}m"
                stops   = max(len(it.get("route", [])) - 1, 0)
                fn      = (it.get("route") or [{}])[0].get("flight_no", "VN")
                results.append(FlightResult(
                    date=date, price=price,
                    departure_time=dep_at,
                    arrival_time=it.get("local_arrival", ""),
                    stops=stops, duration=dur_str,
                    flight_number=fn,
                ))
            except Exception:
                continue
        return results


# ─── Exchange Rate ────────────────────────────────────────────────────────────

class ExchangeRate:
    """
    Lấy tỷ giá VND↔JPY từ open.er-api.com (miễn phí, không cần key).
    Cache 1 tiếng, tự làm mới khi hết hạn.
    """
    _API = "https://open.er-api.com/v6/latest/JPY"
    _rate_vnd_per_jpy: float = 165.0   # fallback: ~1 JPY = 165 VND
    _fetched_at: float = 0.0
    _TTL = 3600  # giây

    @classmethod
    def vnd_to_jpy(cls, vnd: float) -> float:
        cls._maybe_refresh()
        return vnd / cls._rate_vnd_per_jpy

    @classmethod
    def jpy_to_vnd(cls, jpy: float) -> float:
        cls._maybe_refresh()
        return jpy * cls._rate_vnd_per_jpy

    @classmethod
    def rate_label(cls) -> str:
        cls._maybe_refresh()
        return f"1 JPY ≈ {cls._rate_vnd_per_jpy:,.1f} ₫"

    @classmethod
    def fetch_now(cls) -> bool:
        """Fetch blocking – gọi từ thread phụ."""
        try:
            r = requests.get(cls._API, timeout=8)
            r.raise_for_status()
            data = r.json()
            vnd_per_jpy = data["rates"].get("VND")
            if vnd_per_jpy and float(vnd_per_jpy) > 0:
                cls._rate_vnd_per_jpy = float(vnd_per_jpy)
                cls._fetched_at = time.time()
                return True
        except Exception:
            pass
        return False

    @classmethod
    def _maybe_refresh(cls):
        if time.time() - cls._fetched_at > cls._TTL:
            threading.Thread(target=cls.fetch_now, daemon=True).start()


# ─── Notifications ────────────────────────────────────────────────────────────

class Notifier:
    _last_toast = 0.0

    @classmethod
    def toast(cls, title: str, body: str, min_gap_sec: int = 60):
        now = time.time()
        if now - cls._last_toast < min_gap_sec:
            return
        cls._last_toast = now
        threading.Thread(target=cls._send, args=(title, body), daemon=True).start()

    @staticmethod
    def _send(title: str, body: str):
        # Method 1 – win10toast
        try:
            from win10toast import ToastNotifier
            ToastNotifier().show_toast(title, body, duration=10,
                                       threaded=True, icon_path=None)
            return
        except Exception:
            pass
        # Method 2 – PowerShell balloon tip
        try:
            t  = title.replace("'", "''")
            b  = body.replace("'", "''")
            ps = f"""
[void][System.Reflection.Assembly]::LoadWithPartialName('System.Windows.Forms')
$n = New-Object System.Windows.Forms.NotifyIcon
$n.Icon = [System.Drawing.SystemIcons]::Information
$n.Visible = $true
$n.BalloonTipTitle = '{t}'
$n.BalloonTipText  = '{b}'
$n.BalloonTipIcon  = [System.Windows.Forms.ToolTipIcon]::Info
$n.ShowBalloonTip(10000)
Start-Sleep -Milliseconds 11000
$n.Visible = $false
$n.Dispose()
"""
            subprocess.Popen(
                ["powershell", "-WindowStyle", "Hidden", "-Command", ps],
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
        except Exception:
            pass


# ─── Settings ─────────────────────────────────────────────────────────────────

class Settings:
    def __init__(self):
        self.data = DEFAULT_SETTINGS.copy()
        self._load()

    def _load(self):
        try:
            if SETTINGS_FILE.exists():
                self.data.update(json.loads(SETTINGS_FILE.read_text("utf-8")))
        except Exception:
            pass

    def save(self):
        SETTINGS_FILE.parent.mkdir(parents=True, exist_ok=True)
        SETTINGS_FILE.write_text(json.dumps(self.data, indent=2, ensure_ascii=False), "utf-8")

    def __getitem__(self, k):      return self.data[k]
    def __setitem__(self, k, v):   self.data[k] = v
    def get(self, k, d=None):      return self.data.get(k, d)


# ─── Price Monitor ────────────────────────────────────────────────────────────

class PriceMonitor:
    def __init__(self, q: queue.Queue):
        self.q             = q
        self.api: Optional[FlightAPI] = None
        self.searches:     List[Dict] = []
        self.last_prices:  Dict[str, float] = {}
        self._running      = False
        self._thread: Optional[threading.Thread] = None
        self._notify_times: Dict[str, float] = {}

    def set_api(self, api: FlightAPI):
        self.api = api

    def set_searches(self, searches: List[Dict]):
        self.searches = searches

    def start(self):
        if self._running or not self.api or not self.searches:
            return
        self._running = True
        self._thread  = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    # ── internal ──────────────────────────────────────────────────────────────

    def _loop(self):
        while self._running:
            for cfg in list(self.searches):
                if not self._running:
                    break
                self._check(cfg)
            interval = max(1, self.searches[0].get("monitor_interval", 60)) * 60 if self.searches else 3600
            deadline = time.time() + interval
            while self._running and time.time() < deadline:
                time.sleep(2)

    def _check(self, cfg: Dict):
        origin = cfg["origin"]
        dest   = cfg["destination"]
        s_date = cfg["start_date"]
        e_date = cfg["end_date"]
        direct = cfg.get("direct_only", False)

        range_results = self.api.search_range(origin, dest, s_date, e_date, direct)
        all_flights   = [f for fs in range_results.values() for f in (fs or [])]

        cheapest_flight: Optional[FlightResult] = None
        if all_flights:
            cheapest_flight = min(all_flights, key=lambda f: f.price)

        key        = f"{origin}>{dest}|{s_date}>{e_date}"
        prev_price = self.last_prices.get(key)

        price_dropped = (
            prev_price is not None
            and cheapest_flight is not None
            and cheapest_flight.price < prev_price
        )
        if cheapest_flight:
            self.last_prices[key] = cheapest_flight.price

        self.q.put({
            "type":           "monitor_update",
            "cfg":            cfg,
            "cheapest":       cheapest_flight,
            "range_results":  range_results,
            "price_dropped":  price_dropped,
            "prev_price":     prev_price,
        })


# ─── Popup Detail Dialog ──────────────────────────────────────────────────────

class DetailPopup(tk.Toplevel):
    def __init__(self, parent, title: str, content: str):
        super().__init__(parent)
        self.title(title)
        self.geometry("520x360")
        self.resizable(True, True)
        self.grab_set()

        txt = tk.Text(self, wrap=tk.WORD, font=("Segoe UI", 10),
                      padx=15, pady=10)
        txt.pack(fill=tk.BOTH, expand=True)
        txt.insert("1.0", content)
        txt.configure(state=tk.DISABLED)

        ttk.Button(self, text="Đóng", command=self.destroy).pack(pady=8)


# ─── Save Config Name Dialog ─────────────────────────────────────────────────

class NameDialog(tk.Toplevel):
    def __init__(self, parent, default: str):
        super().__init__(parent)
        self.title("Đặt tên cấu hình")
        self.geometry("360x120")
        self.resizable(False, False)
        self.grab_set()
        self.result: Optional[str] = None

        ttk.Label(self, text="Tên cấu hình:").pack(pady=(15, 5))
        self._var = tk.StringVar(value=default)
        e = ttk.Entry(self, textvariable=self._var, width=40)
        e.pack()
        e.select_range(0, tk.END)
        e.focus()

        btn_row = ttk.Frame(self)
        btn_row.pack(pady=10)
        ttk.Button(btn_row, text="Lưu",  command=self._ok).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_row, text="Hủy",  command=self.destroy).pack(side=tk.LEFT)
        self.bind("<Return>", lambda _: self._ok())

    def _ok(self):
        self.result = self._var.get().strip() or None
        self.destroy()


# ─── Holiday Data ─────────────────────────────────────────────────────────────

class HolidayData:
    """
    Dữ liệu ngày lễ chính thức VN và Nhật Bản (2024-2030).
    jp_big_season()  → tên kỳ nghỉ lớn hoặc None
    jp_holiday()     → tên ngày lễ quốc gia JP hoặc None
    vn_holiday()     → tên ngày lễ VN hoặc None
    """

    # ── Việt Nam – ngày lễ dương lịch cố định ──────────────────────────────
    _VN_FIXED: Dict[Tuple[int,int], str] = {
        (1,  1): "Tết Dương lịch",
        (4, 30): "Ngày Giải phóng miền Nam",
        (5,  1): "Quốc tế Lao động",
        (9,  2): "Quốc khánh",
    }

    # ── Tết Nguyên Đán – ngày 1 tháng 1 âm lịch (đã tính sang dương) ──────
    _VN_TET: Dict[int, _date] = {
        2024: _date(2024, 2, 10), 2025: _date(2025, 1, 29),
        2026: _date(2026, 2, 17), 2027: _date(2027, 2,  6),
        2028: _date(2028, 1, 26), 2029: _date(2029, 2, 13),
        2030: _date(2030, 2,  3),
    }

    # ── Giỗ Tổ Hùng Vương – 10/3 âm lịch ──────────────────────────────────
    _VN_GIO_TO: Dict[int, _date] = {
        2024: _date(2024, 4, 18), 2025: _date(2025, 4,  7),
        2026: _date(2026, 4, 27), 2027: _date(2027, 4, 16),
        2028: _date(2028, 4,  5), 2029: _date(2029, 4, 24),
        2030: _date(2030, 4, 13),
    }

    # ── Nhật Bản – ngày lễ cố định ─────────────────────────────────────────
    _JP_FIXED: Dict[Tuple[int,int], str] = {
        (1,  1): "元日 / Năm mới",
        (2, 11): "建国記念の日 / Lập quốc",
        (2, 23): "天皇誕生日 / Sinh nhật Thiên hoàng",
        (4, 29): "昭和の日 / Ngày Chiêu Hòa",
        (5,  3): "憲法記念日 / Kỷ niệm Hiến pháp",
        (5,  4): "みどりの日 / Ngày Xanh lá",
        (5,  5): "こどもの日 / Ngày Thiếu nhi",
        (8, 11): "山の日 / Ngày Núi",
        (11, 3): "文化の日 / Ngày Văn hóa",
        (11,23): "勤労感謝の日 / Tạ ơn LĐ",
    }

    # ── Nhật Bản – ngày lễ thay đổi theo năm (Happy Monday + tiết khí) ────
    _JP_VAR: Dict[int, Dict[_date, str]] = {
        2024: {_date(2024,1,8):"成人の日",_date(2024,3,20):"春分の日",
               _date(2024,7,15):"海の日",_date(2024,9,16):"敬老の日",
               _date(2024,9,22):"秋分の日",_date(2024,10,14):"スポーツの日"},
        2025: {_date(2025,1,13):"成人の日",_date(2025,3,20):"春分の日",
               _date(2025,7,21):"海の日",_date(2025,9,15):"敬老の日",
               _date(2025,9,23):"秋分の日",_date(2025,10,13):"スポーツの日"},
        2026: {_date(2026,1,12):"成人の日",_date(2026,3,20):"春分の日",
               _date(2026,7,20):"海の日",_date(2026,9,21):"敬老の日",
               _date(2026,9,23):"秋分の日",_date(2026,10,12):"スポーツの日"},
        2027: {_date(2027,1,11):"成人の日",_date(2027,3,21):"春分の日",
               _date(2027,7,19):"海の日",_date(2027,9,20):"敬老の日",
               _date(2027,9,23):"秋分の日",_date(2027,10,11):"スポーツの日"},
        2028: {_date(2028,1,10):"成人の日",_date(2028,3,20):"春分の日",
               _date(2028,7,17):"海の日",_date(2028,9,18):"敬老の日",
               _date(2028,9,22):"秋分の日",_date(2028,10,9):"スポーツの日"},
        2029: {_date(2029,1,8):"成人の日",_date(2029,3,20):"春分の日",
               _date(2029,7,16):"海の日",_date(2029,9,17):"敬老の日",
               _date(2029,9,23):"秋分の日",_date(2029,10,8):"スポーツの日"},
        2030: {_date(2030,1,14):"成人の日",_date(2030,3,20):"春分の日",
               _date(2030,7,15):"海の日",_date(2030,9,16):"敬老の日",
               _date(2030,9,23):"秋分の日",_date(2030,10,14):"スポーツの日"},
    }

    # ── 3 kỳ nghỉ lớn Nhật (Golden Week / Obon / Năm mới) ─────────────────
    @staticmethod
    def jp_big_season(d: _date) -> Optional[str]:
        y = d.year
        if _date(y, 4, 27) <= d <= _date(y, 5, 6):
            return "🎌 Golden Week"
        if _date(y, 8, 10) <= d <= _date(y, 8, 18):
            return "🏮 Obon"
        if _date(y, 12, 27) <= d <= _date(y, 12, 31):
            return "🎍 Năm mới Nhật (年末)"
        if _date(y, 1,  1) <= d <= _date(y, 1,  5):
            return "🎍 Năm mới Nhật (正月)"
        return None

    @classmethod
    def jp_holiday(cls, d: _date) -> Optional[str]:
        name = cls._JP_FIXED.get((d.month, d.day))
        if name:
            return name
        return cls._JP_VAR.get(d.year, {}).get(d)

    @classmethod
    def vn_holiday(cls, d: _date) -> Optional[str]:
        name = cls._VN_FIXED.get((d.month, d.day))
        if name:
            return name
        tet = cls._VN_TET.get(d.year)
        if tet:
            eve = tet - timedelta(days=1)
            if d == eve:
                return "Giao thừa Tết Nguyên Đán"
            for i in range(7):
                if d == tet + timedelta(days=i):
                    return f"Tết Nguyên Đán (ngày {i+1})"
        gio_to = cls._VN_GIO_TO.get(d.year)
        if gio_to and d == gio_to:
            return "Giỗ Tổ Hùng Vương (10/3 âm)"
        return None


# ─── Date Range Picker ────────────────────────────────────────────────────────

class DateRangePicker(tk.Toplevel):
    """
    Calendar popup 2 tháng song song, hỗ trợ highlight lịch nghỉ VN và Nhật.
    Kết quả: self.result_start / self.result_end  (YYYY-MM-DD hoặc None)

    Màu ưu tiên (cao → thấp):
      Endpoint chọn  > Range/Hover  > Kỳ nghỉ lớn JP (cam đậm)
      > Lễ JP (cam nhạt)  > Lễ VN (đỏ nhạt)  > Hôm nay  > Quá khứ  > Thường
    """
    _MONTHS_VI = ["","Tháng 1","Tháng 2","Tháng 3","Tháng 4","Tháng 5",
                  "Tháng 6","Tháng 7","Tháng 8","Tháng 9","Tháng 10",
                  "Tháng 11","Tháng 12"]
    _DAYS_HDR = ["T2","T3","T4","T5","T6","T7","CN"]

    # ── Colour palette ────────────────────────────────────────────────────────
    C_SEL_BG     = "#1565c0";  C_SEL_FG    = "white"
    C_RANGE_BG   = "#bbdefb";  C_RANGE_FG  = "#0d47a1"
    C_HOVER_BG   = "#90caf9";  C_HOVER_FG  = "#0d47a1"
    C_JP_BIG_BG  = "#e65100";  C_JP_BIG_FG = "white"    # 3 kỳ lớn JP
    C_JP_HOL_BG  = "#ffe0b2";  C_JP_HOL_FG = "#bf360c"  # lễ JP khác
    C_VN_HOL_BG  = "#ffcdd2";  C_VN_HOL_FG = "#b71c1c"  # lễ VN
    C_TODAY_BG   = "#fff9c4";  C_TODAY_FG  = "#f57f17"
    C_PAST_FG    = "#bdbdbd";  C_NORMAL_BG = "white"
    C_SUN_FG     = "#e53935";  C_NORMAL_FG = "#212121"

    def __init__(self, parent, title="Chọn khoảng ngày",
                 start_str: str = "", end_str: str = ""):
        super().__init__(parent)
        self.title(title)
        self.resizable(False, False)
        self.grab_set()
        self.transient(parent)

        self.result_start: Optional[str] = None
        self.result_end:   Optional[str] = None

        self._start: Optional[_date] = self._parse(start_str)
        self._end:   Optional[_date] = self._parse(end_str)
        self._hover: Optional[_date] = None
        self._phase = 0 if not self._start else (1 if not self._end else 2)

        ref = self._start or datetime.now().date()
        self._ly, self._lm = ref.year, ref.month

        self._cells: Dict[_date, tk.Label] = {}

        # Holiday toggle vars (default ON)
        self._show_vn = tk.BooleanVar(value=True)
        self._show_jp = tk.BooleanVar(value=True)
        self._show_jp_big = tk.BooleanVar(value=True)

        self._build_ui()
        self._render()

    @staticmethod
    def _parse(s: str) -> Optional[_date]:
        try:
            return datetime.strptime(s.strip(), "%Y-%m-%d").date()
        except Exception:
            return None

    # ── UI scaffold ───────────────────────────────────────────────────────────

    def _build_ui(self):
        # ── Top header bar ────────────────────────────────────────────────────
        top = tk.Frame(self, bg="#1565c0", pady=10)
        top.pack(fill=tk.X)
        self._instr_var = tk.StringVar()
        tk.Label(top, textvariable=self._instr_var, bg="#1565c0", fg="white",
                 font=("Segoe UI", 11)).pack(side=tk.LEFT, padx=15)
        self._range_var = tk.StringVar(value="Chưa chọn")
        tk.Label(top, textvariable=self._range_var, bg="#1565c0", fg="#e3f2fd",
                 font=("Segoe UI", 11, "bold")).pack(side=tk.RIGHT, padx=15)

        # ── Holiday toggle options ─────────────────────────────────────────────
        opts = tk.Frame(self, bg="#f5f5f5", pady=6)
        opts.pack(fill=tk.X, padx=0)
        tk.Label(opts, text="Hiển thị lịch nghỉ:", bg="#f5f5f5",
                 font=("Segoe UI", 9, "bold")).pack(side=tk.LEFT, padx=(12, 8))

        def _chk(var, bg_color, text):
            f = tk.Frame(opts, bg="#f5f5f5")
            f.pack(side=tk.LEFT, padx=(0, 12))
            tk.Label(f, text="■", bg="#f5f5f5", fg=bg_color,
                     font=("Segoe UI", 11)).pack(side=tk.LEFT)
            tk.Checkbutton(f, text=text, variable=var, bg="#f5f5f5",
                           font=("Segoe UI", 9),
                           command=self._recolor).pack(side=tk.LEFT)

        _chk(self._show_jp_big, self.C_JP_BIG_BG,  "3 kỳ lớn Nhật (GW/Obon/Tết JP)")
        _chk(self._show_jp,     self.C_JP_HOL_BG,  "Lễ quốc gia Nhật")
        _chk(self._show_vn,     self.C_VN_HOL_BG,  "Lễ chính thức VN")

        # ── Calendar body ──────────────────────────────────────────────────────
        body = tk.Frame(self, bg="white", padx=15, pady=10)
        body.pack()
        self._left_fr  = tk.Frame(body, bg="white")
        self._right_fr = tk.Frame(body, bg="white")
        self._left_fr.grid(row=0, column=0, padx=(0, 20))
        self._right_fr.grid(row=0, column=1)

        # ── Status bar (hover holiday name) ───────────────────────────────────
        self._hol_var = tk.StringVar(value="")
        status = tk.Frame(self, bg="#fafafa", pady=4)
        status.pack(fill=tk.X)
        tk.Label(status, textvariable=self._hol_var, bg="#fafafa",
                 fg="#555", font=("Segoe UI", 9, "italic"),
                 anchor=tk.W).pack(side=tk.LEFT, padx=12)

        # ── Legend ────────────────────────────────────────────────────────────
        leg = tk.Frame(self, bg="white", pady=4)
        leg.pack(fill=tk.X, padx=12)
        def _leg(bg, fg, text):
            tk.Label(leg, text=f"■ {text}", bg="white", fg=bg,
                     font=("Segoe UI", 8)).pack(side=tk.LEFT, padx=(0, 14))
        _leg(self.C_SEL_BG,    "white",  "Ngày chọn")
        _leg(self.C_RANGE_BG,  "black",  "Khoảng chọn")
        _leg(self.C_JP_BIG_BG, "white",  "Kỳ nghỉ lớn JP")
        _leg(self.C_JP_HOL_BG, "black",  "Lễ JP")
        _leg(self.C_VN_HOL_BG, "black",  "Lễ VN")
        _leg(self.C_TODAY_BG,  "black",  "Hôm nay")

        # ── Footer buttons ─────────────────────────────────────────────────────
        foot = tk.Frame(self, pady=8)
        foot.pack(fill=tk.X, padx=15)
        tk.Button(foot, text="Xóa chọn", relief=tk.FLAT, bg="#f5f5f5",
                  command=self._clear).pack(side=tk.LEFT)
        tk.Button(foot, text="Hủy", relief=tk.FLAT, bg="#f5f5f5",
                  command=self.destroy).pack(side=tk.RIGHT, padx=(8, 0))
        tk.Button(foot, text="  Xác nhận  ", relief=tk.RAISED,
                  bg="#1565c0", fg="white", font=("Segoe UI", 9, "bold"),
                  command=self._confirm).pack(side=tk.RIGHT)

    # ── Render ────────────────────────────────────────────────────────────────

    def _render(self):
        self._cells.clear()
        for w in self._left_fr.winfo_children():  w.destroy()
        for w in self._right_fr.winfo_children(): w.destroy()

        ry, rm = self._next_month(self._ly, self._lm)
        self._draw_month(self._left_fr,  self._ly, self._lm, nav="left")
        self._draw_month(self._right_fr, ry,       rm,       nav="right")
        self._update_labels()

    def _draw_month(self, frame, year, month, nav):
        bg = "white"
        hdr = tk.Frame(frame, bg=bg)
        hdr.grid(row=0, column=0, columnspan=7, pady=(0, 8))

        if nav == "left":
            tk.Button(hdr, text="◀", relief=tk.FLAT, bg=bg, cursor="hand2",
                      command=self._prev).pack(side=tk.LEFT)
        tk.Label(hdr, text=f"{self._MONTHS_VI[month]}  {year}",
                 bg=bg, font=("Segoe UI", 10, "bold"), width=17,
                 anchor=tk.CENTER).pack(side=tk.LEFT, expand=True)
        if nav == "right":
            tk.Button(hdr, text="▶", relief=tk.FLAT, bg=bg, cursor="hand2",
                      command=self._next).pack(side=tk.RIGHT)

        for col, d in enumerate(self._DAYS_HDR):
            fg = self.C_SUN_FG if d == "CN" else "#757575"
            tk.Label(frame, text=d, bg=bg, fg=fg, width=4,
                     font=("Segoe UI", 8, "bold")).grid(row=1, column=col)

        today = datetime.now().date()
        for wk, week in enumerate(_cal.monthcalendar(year, month)):
            for dow, day in enumerate(week):
                if day == 0:
                    tk.Label(frame, text="", bg=bg, width=4).grid(
                        row=2 + wk, column=dow, padx=1, pady=1)
                    continue
                d   = _date(year, month, day)
                lbl = tk.Label(frame, text=str(day), bg=bg, width=4,
                               font=("Segoe UI", 9), relief=tk.FLAT,
                               padx=3, pady=5,
                               cursor="hand2" if d >= today else "arrow")
                lbl.grid(row=2 + wk, column=dow, padx=1, pady=1)
                self._cells[d] = lbl
                lbl.bind("<Enter>",    lambda e, d=d: self._on_enter(d))
                lbl.bind("<Leave>",    lambda e:      self._on_leave())
                lbl.bind("<Button-1>", lambda e, d=d: self._on_click(d))

        self._recolor()

    # ── Colour logic ──────────────────────────────────────────────────────────

    def _holiday_info(self, d: _date) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Returns (bg, fg, tooltip_text) or (None,None,None)."""
        # JP big 3 seasons – highest holiday priority
        if self._show_jp_big.get():
            name = HolidayData.jp_big_season(d)
            if name:
                return self.C_JP_BIG_BG, self.C_JP_BIG_FG, name
        # JP national holiday
        if self._show_jp.get():
            name = HolidayData.jp_holiday(d)
            if name:
                return self.C_JP_HOL_BG, self.C_JP_HOL_FG, name
        # VN official holiday
        if self._show_vn.get():
            name = HolidayData.vn_holiday(d)
            if name:
                return self.C_VN_HOL_BG, self.C_VN_HOL_FG, name
        return None, None, None

    def _recolor(self):
        today = datetime.now().date()
        s, e  = self._start, self._end
        preview_end = (self._hover
                       if self._phase == 1 and self._hover and s else e)

        for d, lbl in self._cells.items():
            is_past   = d < today
            is_today  = d == today
            is_start  = bool(s and d == s)
            is_end    = bool(e and d == e)
            in_range  = bool(e and s and min(s, e) < d < max(s, e))
            in_prev   = bool(preview_end and s and not in_range and
                             min(s, preview_end) < d < max(s, preview_end))
            is_hover  = bool(self._hover and d == self._hover and self._phase == 1)
            sunday_fg = self.C_SUN_FG if d.weekday() == 6 else self.C_NORMAL_FG

            # ── Priority colour assignment ─────────────────────────────────
            if is_start or is_end:
                lbl.configure(bg=self.C_SEL_BG, fg=self.C_SEL_FG,
                               font=("Segoe UI", 9, "bold"), relief=tk.RAISED)
            elif in_range or in_prev:
                lbl.configure(bg=self.C_RANGE_BG, fg=self.C_RANGE_FG,
                               font=("Segoe UI", 9), relief=tk.FLAT)
            elif is_hover:
                lbl.configure(bg=self.C_HOVER_BG, fg=self.C_HOVER_FG,
                               font=("Segoe UI", 9), relief=tk.FLAT)
            else:
                hbg, hfg, _ = self._holiday_info(d)
                if hbg:
                    # Holiday: keep past dates dimmer
                    lbl.configure(bg=hbg,
                                   fg=hfg if not is_past else self.C_PAST_FG,
                                   font=("Segoe UI", 9, "bold"), relief=tk.FLAT)
                elif is_today:
                    lbl.configure(bg=self.C_TODAY_BG, fg=self.C_TODAY_FG,
                                   font=("Segoe UI", 9, "bold"), relief=tk.FLAT)
                elif is_past:
                    lbl.configure(bg=self.C_NORMAL_BG, fg=self.C_PAST_FG,
                                   font=("Segoe UI", 9), relief=tk.FLAT)
                else:
                    lbl.configure(bg=self.C_NORMAL_BG, fg=sunday_fg,
                                   font=("Segoe UI", 9), relief=tk.FLAT)

    # ── Events ────────────────────────────────────────────────────────────────

    def _on_enter(self, d: _date):
        if d < datetime.now().date():
            return
        self._hover = d
        # Show holiday name in status bar
        _, _, tip = self._holiday_info(d)
        self._hol_var.set(tip or "")
        self._recolor()

    def _on_leave(self):
        self._hover = None
        self._hol_var.set("")
        self._recolor()

    def _on_click(self, d: _date):
        if d < datetime.now().date():
            return
        if self._phase in (0, 2):
            self._start, self._end = d, None
            self._phase = 1
        else:
            if d < self._start:
                self._start, self._end = d, self._start
            else:
                self._end = d
            self._phase = 2
        self._recolor()
        self._update_labels()

    def _prev(self):
        self._ly, self._lm = self._prev_month(self._ly, self._lm)
        self._render()

    def _next(self):
        self._ly, self._lm = self._next_month(self._ly, self._lm)
        self._render()

    def _clear(self):
        self._start = self._end = None
        self._phase = 0
        self._recolor()
        self._update_labels()

    def _confirm(self):
        if self._start:
            self.result_start = self._start.strftime("%Y-%m-%d")
        if self._end:
            self.result_end = self._end.strftime("%Y-%m-%d")
        self.destroy()

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _update_labels(self):
        msgs = {0: "Chọn ngày bắt đầu  ▸", 1: "Chọn ngày kết thúc  ▸",
                2: "Khoảng đã chọn  ▸"}
        self._instr_var.set(msgs.get(self._phase, ""))
        if self._start and self._end:
            s = self._start.strftime("%d/%m/%Y")
            e = self._end.strftime("%d/%m/%Y")
            nights = (self._end - self._start).days
            self._range_var.set(f"{s}  →  {e}  ({nights} đêm)")
        elif self._start:
            self._range_var.set(self._start.strftime("%d/%m/%Y") + "  →  ?")
        else:
            self._range_var.set("Chưa chọn")

    @staticmethod
    def _prev_month(y, m):
        m -= 1
        if m < 1: m, y = 12, y - 1
        return y, m

    @staticmethod
    def _next_month(y, m):
        m += 1
        if m > 12: m, y = 1, y + 1
        return y, m


# ─── Main Application ─────────────────────────────────────────────────────────

class App:
    def __init__(self):
        self.settings = Settings()
        self.q        = queue.Queue()
        self.monitor  = PriceMonitor(self.q)
        self.api: Optional[FlightAPI] = None
        self._monitor_on  = False
        self._last_notify = 0.0
        self._auto_refresh_job: Optional[str] = None  # after() id

        # ── search result cache ───────────────────────────────────────────────
        self.out_results: Dict[str, List[FlightResult]] = {}
        self.ret_results: Dict[str, List[FlightResult]] = {}

        self._build_window()
        self._apply_api()
        # Fetch exchange rate in background immediately
        threading.Thread(target=self._fetch_rate_bg, daemon=True).start()
        self._poll()

    # ══ Window ════════════════════════════════════════════════════════════════

    def _build_window(self):
        self.root = tk.Tk()
        self.root.title(f"{APP_NAME} v{VERSION}")
        self.root.geometry("980x720")
        self.root.minsize(860, 620)

        style = ttk.Style()
        try:
            style.theme_use("clam")
        except Exception:
            pass
        style.configure("TNotebook.Tab",       padding=[14, 7])
        style.configure("H1.TLabel",           font=("Segoe UI", 15, "bold"))
        style.configure("Price.TLabel",        font=("Segoe UI", 11, "bold"), foreground="#1565c0")
        style.configure("Total.TLabel",        font=("Segoe UI", 13, "bold"), foreground="#b71c1c")
        style.configure("OK.TLabel",           foreground="#2e7d32")
        style.configure("Err.TLabel",          foreground="#c62828")
        style.configure("Accent.TButton",      padding=[8, 4])
        style.configure("Green.Horizontal.TProgressbar",
                        troughcolor="#e0e0e0", background="#43a047",
                        lightcolor="#66bb6a",  darkcolor="#2e7d32",
                        bordercolor="#c8e6c9", thickness=14)
        style.map("Accent.TButton",
                  background=[("active", "#1565c0"), ("!active", "#1a73e8")],
                  foreground=[("active", "white"),   ("!active", "white")])

        # Header
        hdr = ttk.Frame(self.root, padding=(10, 8))
        hdr.pack(fill=tk.X)
        ttk.Label(hdr, text="✈  Vietnam Airlines Price Tracker",
                  style="H1.TLabel").pack(side=tk.LEFT)
        self._status_var = tk.StringVar(value="Sẵn sàng")
        ttk.Label(hdr, textvariable=self._status_var,
                  foreground="gray").pack(side=tk.RIGHT, padx=10)

        ttk.Separator(self.root, orient=tk.HORIZONTAL).pack(fill=tk.X)

        nb = ttk.Notebook(self.root)
        nb.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        self.nb = nb

        self._build_search_tab(nb)
        self._build_results_tab(nb)
        self._build_combo_tab(nb)
        self._build_monitor_tab(nb)
        self._build_settings_tab(nb)

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

    # ══ Search Tab ════════════════════════════════════════════════════════════

    def _build_search_tab(self, nb):
        f = ttk.Frame(nb, padding=10)
        nb.add(f, text="  Tìm chuyến bay  ")

        # ── Trip type ────────────────────────────────────────────────────────
        row = ttk.LabelFrame(f, text="Loại chuyến bay", padding=10)
        row.pack(fill=tk.X, pady=(0, 8))
        self._trip = tk.StringVar(value="OW")
        ttk.Radiobutton(row, text="  Một chiều",
                        variable=self._trip, value="OW",
                        command=self._trip_changed).pack(side=tk.LEFT, padx=(0, 30))
        ttk.Radiobutton(row, text="  Khứ hồi",
                        variable=self._trip, value="RT",
                        command=self._trip_changed).pack(side=tk.LEFT)

        # ── Route ────────────────────────────────────────────────────────────
        route = ttk.LabelFrame(f, text="Tuyến bay", padding=10)
        route.pack(fill=tk.X, pady=(0, 8))

        ttk.Label(route, text="Nơi đi:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        self._origin = tk.StringVar(value=AIRPORT_LABELS[0])
        ttk.Combobox(route, textvariable=self._origin, values=AIRPORT_LABELS,
                     width=34, state="readonly").grid(row=0, column=1, sticky=tk.W)
        ttk.Button(route, text="⇄", width=4,
                   command=self._swap).grid(row=0, column=2, padx=8)
        ttk.Label(route, text="Nơi đến:").grid(row=0, column=3, sticky=tk.W, padx=(0, 5))
        self._dest = tk.StringVar(value=AIRPORT_LABELS[1])
        ttk.Combobox(route, textvariable=self._dest, values=AIRPORT_LABELS,
                     width=34, state="readonly").grid(row=0, column=4, sticky=tk.W)

        # ── Dates ────────────────────────────────────────────────────────────
        dates = ttk.LabelFrame(f, text="Khoảng thời gian", padding=10)
        dates.pack(fill=tk.X, pady=(0, 8))

        today   = datetime.now()
        def_df  = (today + timedelta(days=7)).strftime("%Y-%m-%d")
        def_dt  = (today + timedelta(days=37)).strftime("%Y-%m-%d")
        def_rf  = (today + timedelta(days=10)).strftime("%Y-%m-%d")
        def_rt  = (today + timedelta(days=45)).strftime("%Y-%m-%d")

        # Hidden StringVars keep dates as YYYY-MM-DD (backward compat)
        self._dep_from = tk.StringVar(value=def_df)
        self._dep_to   = tk.StringVar(value=def_dt)
        self._ret_from = tk.StringVar(value=def_rf)
        self._ret_to   = tk.StringVar(value=def_rt)

        def _fmt(sv_from, sv_to):
            s = sv_from.get()
            e = sv_to.get()
            try:
                nights = (datetime.strptime(e, "%Y-%m-%d") -
                          datetime.strptime(s, "%Y-%m-%d")).days
                return f"📅  {s}  →  {e}  ({nights} đêm)"
            except Exception:
                return f"📅  {s}  →  {e}"

        # Chuyến đi row
        self._dep_from_lbl = ttk.Label(dates, text="Chuyến đi:")
        self._dep_from_lbl.grid(row=0, column=0, sticky=tk.W, padx=(0, 8))
        self._dep_range_var = tk.StringVar(value=_fmt(self._dep_from, self._dep_to))
        self._dep_btn = tk.Button(
            dates, textvariable=self._dep_range_var,
            relief=tk.GROOVE, bg="#e8f0fe", fg="#1565c0",
            font=("Segoe UI", 10), padx=10, pady=4, cursor="hand2",
            command=lambda: self._open_picker("dep"))
        self._dep_btn.grid(row=0, column=1, sticky=tk.W)
        ttk.Label(dates, text="(click để chọn)", foreground="gray",
                  font=("Segoe UI", 8)).grid(row=0, column=2, padx=(8, 0))

        # Chuyến về row
        self._ret_from_lbl = ttk.Label(dates, text="Chuyến về:")
        self._ret_from_lbl.grid(row=1, column=0, sticky=tk.W, padx=(0, 8), pady=(10, 0))
        self._ret_range_var = tk.StringVar(value=_fmt(self._ret_from, self._ret_to))
        self._ret_btn = tk.Button(
            dates, textvariable=self._ret_range_var,
            relief=tk.GROOVE, bg="#fce4ec", fg="#880e4f",
            font=("Segoe UI", 10), padx=10, pady=4, cursor="hand2",
            command=lambda: self._open_picker("ret"))
        self._ret_btn.grid(row=1, column=1, sticky=tk.W, pady=(10, 0))
        self._ret_hint = ttk.Label(dates, text="(click để chọn)", foreground="gray",
                                    font=("Segoe UI", 8))
        self._ret_hint.grid(row=1, column=2, padx=(8, 0), pady=(10, 0))

        # Auto-refresh toggle
        ar_row = ttk.Frame(dates)
        ar_row.grid(row=2, column=0, columnspan=3, sticky=tk.W, pady=(10, 0))
        self._auto_refresh = tk.BooleanVar(value=False)
        ttk.Checkbutton(ar_row, text="Tự động làm mới giá mỗi",
                        variable=self._auto_refresh,
                        command=self._toggle_auto_refresh).pack(side=tk.LEFT)
        self._ar_interval = tk.IntVar(value=15)
        ttk.Spinbox(ar_row, from_=5, to=120, textvariable=self._ar_interval,
                    width=5).pack(side=tk.LEFT, padx=4)
        ttk.Label(ar_row, text="phút").pack(side=tk.LEFT)
        self._ar_status = tk.StringVar(value="")
        ttk.Label(ar_row, textvariable=self._ar_status,
                  foreground="gray").pack(side=tk.LEFT, padx=(12, 0))

        # ── Options ──────────────────────────────────────────────────────────
        opts = ttk.LabelFrame(f, text="Tùy chọn", padding=10)
        opts.pack(fill=tk.X, pady=(0, 8))

        self._direct = tk.BooleanVar(value=False)
        ttk.Checkbutton(opts, text="Bay thẳng (không quá cảnh/transit)",
                        variable=self._direct).pack(side=tk.LEFT, padx=(0, 30))

        ttk.Label(opts, text="Số hành khách:").pack(side=tk.LEFT)
        self._pax = tk.IntVar(value=1)
        ttk.Spinbox(opts, from_=1, to=9, textvariable=self._pax,
                    width=5).pack(side=tk.LEFT, padx=5)

        # ── Buttons ──────────────────────────────────────────────────────────
        btns = ttk.Frame(f)
        btns.pack(fill=tk.X, pady=(5, 0))

        self._search_btn = ttk.Button(
            btns, text="🔍  Tìm giá rẻ nhất",
            command=self._do_search, style="Accent.TButton")
        self._search_btn.pack(side=tk.LEFT, ipadx=12, ipady=5)

        ttk.Button(btns, text="💾  Lưu cấu hình",
                   command=self._save_config).pack(side=tk.LEFT, padx=10)

        self._prog_var = tk.DoubleVar(value=0)
        self._prog     = ttk.Progressbar(f, variable=self._prog_var,
                                          maximum=100, length=380,
                                          style="Green.Horizontal.TProgressbar")
        self._prog.pack(side=tk.LEFT, padx=10)

        self._trip_changed()

    def _trip_changed(self):
        is_rt = self._trip.get() == "RT"
        btn_state = tk.NORMAL if is_rt else tk.DISABLED
        self._ret_btn.configure(state=btn_state,
                                bg="#fce4ec" if is_rt else "#f5f5f5",
                                fg="#880e4f" if is_rt else "#bdbdbd")
        fg = "black" if is_rt else "gray"
        self._ret_from_lbl.configure(foreground=fg)
        self._ret_hint.configure(foreground="gray" if is_rt else "#e0e0e0")

    def _swap(self):
        o, d = self._origin.get(), self._dest.get()
        self._origin.set(d)
        self._dest.set(o)

    # ══ Results Tab ═══════════════════════════════════════════════════════════

    def _build_results_tab(self, nb):
        f = ttk.Frame(nb, padding=8)
        nb.add(f, text="  Kết quả giá  ")

        # Currency bar
        curr_bar = ttk.Frame(f)
        curr_bar.pack(fill=tk.X, pady=(0, 4))
        ttk.Label(curr_bar, text="Hiển thị giá:").pack(side=tk.LEFT)
        self._currency = tk.StringVar(value=self.settings.get("currency", "VND"))
        for cur in ("VND", "JPY", "Cả hai"):
            ttk.Radiobutton(curr_bar, text=cur, variable=self._currency,
                            value=cur,
                            command=self._on_currency_change).pack(
                side=tk.LEFT, padx=(8, 0))
        self._rate_lbl = tk.StringVar(value="Đang lấy tỷ giá...")
        ttk.Label(curr_bar, textvariable=self._rate_lbl,
                  foreground="#1565c0").pack(side=tk.LEFT, padx=(20, 0))
        ttk.Button(curr_bar, text="↻ Làm mới tỷ giá",
                   command=self._refresh_rate).pack(side=tk.RIGHT)

        # Progress bar (visible while searching, hidden when done)
        prog_frame = ttk.Frame(f)
        prog_frame.pack(fill=tk.X, pady=(0, 4))
        self._res_prog_var = tk.DoubleVar(value=0)
        self._res_prog = ttk.Progressbar(
            prog_frame, variable=self._res_prog_var,
            maximum=100, mode="determinate",
            style="Green.Horizontal.TProgressbar")
        self._res_prog.pack(fill=tk.X, ipady=3)
        self._res_prog_lbl = tk.StringVar(value="")
        ttk.Label(prog_frame, textvariable=self._res_prog_lbl,
                  foreground="#2e7d32", font=("Segoe UI", 9)).pack(anchor=tk.W)

        # No-data warning banner
        self._res_no_data_var = tk.StringVar(value="")
        self._res_no_data_lbl = ttk.Label(
            f, textvariable=self._res_no_data_var,
            foreground="#b71c1c", background="#ffebee",
            font=("Segoe UI", 9), padding=(10, 6), wraplength=860, justify=tk.LEFT)

        # Summary bar
        summ = ttk.LabelFrame(f, text="Giá tốt nhất tìm thấy", padding=10)
        summ.pack(fill=tk.X, pady=(0, 8))

        self._s_out = tk.StringVar(value="—")
        self._s_ret = tk.StringVar(value="—")
        self._s_tot = tk.StringVar(value="—")

        ttk.Label(summ, text="Chuyến đi:").grid(row=0, column=0, sticky=tk.W, padx=(0, 5))
        ttk.Label(summ, textvariable=self._s_out, style="Price.TLabel").grid(
            row=0, column=1, sticky=tk.W, padx=(0, 30))
        ttk.Label(summ, text="Chuyến về:").grid(row=0, column=2, sticky=tk.W, padx=(0, 5))
        ttk.Label(summ, textvariable=self._s_ret, style="Price.TLabel").grid(
            row=0, column=3, sticky=tk.W, padx=(0, 30))
        ttk.Label(summ, text="Tổng:").grid(row=0, column=4, sticky=tk.W, padx=(0, 5))
        ttk.Label(summ, textvariable=self._s_tot, style="Total.TLabel").grid(
            row=0, column=5, sticky=tk.W)

        # Paned view
        pw = ttk.PanedWindow(f, orient=tk.HORIZONTAL)
        pw.pack(fill=tk.BOTH, expand=True, pady=(0, 6))

        out_fr = ttk.LabelFrame(pw, text="Chuyến đi (giá theo ngày)", padding=5)
        pw.add(out_fr, weight=1)
        self._out_tree = self._make_price_tree(out_fr)
        self._out_tree.bind("<<TreeviewSelect>>", self._on_select_out)
        self._out_tree.bind("<Double-1>",          self._on_dbl_out)

        ret_fr = ttk.LabelFrame(pw, text="Chuyến về (giá theo ngày)", padding=5)
        pw.add(ret_fr, weight=1)
        self._ret_tree = self._make_price_tree(ret_fr)
        self._ret_tree.bind("<Double-1>", self._on_dbl_ret)

        # Detail bar
        det = ttk.LabelFrame(f, text="Chi tiết (double-click để xem đầy đủ)", padding=6)
        det.pack(fill=tk.X, pady=(0, 6))
        self._detail = tk.Text(det, height=3, state=tk.DISABLED,
                               font=("Consolas", 9), background="#f5f5f5",
                               relief=tk.FLAT, borderwidth=0)
        self._detail.pack(fill=tk.X)

        # Action row
        acts = ttk.Frame(f)
        acts.pack(fill=tk.X)
        ttk.Button(acts, text="📋 Sao chép kết quả",
                   command=self._copy_results).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(acts, text="🔔 Thêm vào theo dõi",
                   command=self._add_monitor).pack(side=tk.LEFT)

    def _make_price_tree(self, parent) -> ttk.Treeview:
        cols = ("date", "price", "stops", "flight", "dep", "dur")
        t = ttk.Treeview(parent, columns=cols, show="headings", height=14)
        t.heading("date",  text="Ngày bay")
        t.heading("price", text="Giá")
        t.heading("stops", text="Điểm dừng")
        t.heading("flight",text="Chuyến bay")
        t.heading("dep",   text="Giờ bay")
        t.heading("dur",   text="Thời gian")

        t.column("date",   width=95,  anchor=tk.CENTER)
        t.column("price",  width=130, anchor=tk.E)
        t.column("stops",  width=75,  anchor=tk.CENTER)
        t.column("flight", width=80,  anchor=tk.CENTER)
        t.column("dep",    width=80,  anchor=tk.CENTER)
        t.column("dur",    width=80,  anchor=tk.CENTER)

        t.tag_configure("best",    background="#c8e6c9", font=("Segoe UI", 9, "bold"))
        t.tag_configure("cheap",   background="#e8f5e9")
        t.tag_configure("mid",     background="#fff9c4")
        t.tag_configure("none",    foreground="gray")

        sb = ttk.Scrollbar(parent, orient=tk.VERTICAL, command=t.yview)
        t.configure(yscrollcommand=sb.set)
        t.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb.pack(side=tk.RIGHT, fill=tk.Y)
        return t

    # ══ Combo Tab ═════════════════════════════════════════════════════════════

    def _build_combo_tab(self, nb):
        f = ttk.Frame(nb, padding=8)
        nb.add(f, text="  Khứ hồi tối ưu  ")

        # Settings row – min/max layover
        sr = ttk.LabelFrame(f, text="Khoảng thời gian nghỉ giữa 2 chuyến", padding=(10, 6))
        sr.pack(fill=tk.X, pady=(0, 8))

        # Unit selector (shared by min & max)
        self._layover_unit = tk.StringVar(
            value="giờ" if self.settings.get("min_layover_unit", "hours") == "hours" else "ngày")
        unit_cb = ttk.Combobox(sr, textvariable=self._layover_unit,
                               values=["giờ", "ngày"], width=7, state="readonly")

        # Min
        ttk.Label(sr, text="Tối thiểu:").grid(row=0, column=0, sticky=tk.W, padx=(0, 4))
        self._layover = tk.IntVar(value=self.settings.get("min_layover_value", 1))
        ttk.Spinbox(sr, from_=1, to=9999, textvariable=self._layover,
                    width=7, command=self._recalc_combos).grid(row=0, column=1, padx=(0, 4))

        # Max
        ttk.Label(sr, text="Tối đa:").grid(row=0, column=2, sticky=tk.W, padx=(12, 4))
        self._layover_max = tk.IntVar(value=self.settings.get("max_layover_value", 30))
        ttk.Spinbox(sr, from_=1, to=9999, textvariable=self._layover_max,
                    width=7, command=self._recalc_combos).grid(row=0, column=3, padx=(0, 4))

        # Unit
        ttk.Label(sr, text="Đơn vị:").grid(row=0, column=4, sticky=tk.W, padx=(12, 4))
        unit_cb.grid(row=0, column=5, padx=(0, 12))
        unit_cb.bind("<<ComboboxSelected>>", lambda _: self._recalc_combos())

        ttk.Button(sr, text="⟳ Tính lại",
                   command=self._recalc_combos).grid(row=0, column=6, padx=(8, 0))

        # Helper label
        self._layover_hint = tk.StringVar(value="")
        ttk.Label(sr, textvariable=self._layover_hint,
                  foreground="#1565c0", font=("Segoe UI", 9)).grid(
            row=1, column=0, columnspan=7, sticky=tk.W, pady=(4, 0))

        # Best summary text
        self._combo_txt = tk.Text(f, height=5, state=tk.DISABLED,
                                   font=("Segoe UI", 10), background="#f0f4ff",
                                   relief=tk.FLAT, padx=12, pady=8)
        self._combo_txt.pack(fill=tk.X, pady=(0, 8))

        # Combo table
        cols2 = ("dep_date", "dep_price", "ret_date", "ret_price", "total", "nights")
        self._combo_tree = ttk.Treeview(f, columns=cols2, show="headings", height=16)
        self._combo_tree.heading("dep_date",  text="Ngày đi")
        self._combo_tree.heading("dep_price", text="Giá đi")
        self._combo_tree.heading("ret_date",  text="Ngày về")
        self._combo_tree.heading("ret_price", text="Giá về")
        self._combo_tree.heading("total",     text="Tổng cộng")
        self._combo_tree.heading("nights",    text="Số đêm")
        for col in cols2:
            self._combo_tree.column(col, width=130, anchor=tk.CENTER)
        self._combo_tree.tag_configure("best", background="#c8e6c9",
                                        font=("Segoe UI", 9, "bold"))
        self._combo_tree.tag_configure("good", background="#e8f5e9")

        sb2 = ttk.Scrollbar(f, orient=tk.VERTICAL, command=self._combo_tree.yview)
        self._combo_tree.configure(yscrollcommand=sb2.set)
        self._combo_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb2.pack(side=tk.RIGHT, fill=tk.Y)

    # ══ Monitor Tab ═══════════════════════════════════════════════════════════

    def _build_monitor_tab(self, nb):
        f = ttk.Frame(nb, padding=10)
        nb.add(f, text="  Theo dõi giá  ")

        # Control panel
        ctrl = ttk.LabelFrame(f, text="Cài đặt theo dõi tự động", padding=12)
        ctrl.pack(fill=tk.X, pady=(0, 10))

        r1 = ttk.Frame(ctrl)
        r1.pack(fill=tk.X, pady=4)
        ttk.Label(r1, text="Kiểm tra giá mỗi:").pack(side=tk.LEFT)
        self._mon_interval = tk.IntVar(value=self.settings.get("monitor_interval_minutes", 60))
        ttk.Spinbox(r1, from_=5, to=1440, textvariable=self._mon_interval,
                    width=7).pack(side=tk.LEFT, padx=5)
        ttk.Label(r1, text="phút      Popup thông báo mỗi:").pack(side=tk.LEFT)
        self._notif_interval = tk.IntVar(value=self.settings.get("notify_interval_minutes", 120))
        ttk.Spinbox(r1, from_=15, to=1440, textvariable=self._notif_interval,
                    width=7).pack(side=tk.LEFT, padx=5)
        ttk.Label(r1, text="phút").pack(side=tk.LEFT)

        r2 = ttk.Frame(ctrl)
        r2.pack(fill=tk.X, pady=4)
        self._notif_drop = tk.BooleanVar(value=self.settings.get("notify_on_price_drop", True))
        ttk.Checkbutton(r2, text="Thông báo khi giá giảm",
                        variable=self._notif_drop).pack(side=tk.LEFT, padx=(0, 25))
        self._notif_periodic = tk.BooleanVar(value=self.settings.get("notify_periodically", True))
        ttk.Checkbutton(r2, text="Thông báo định kỳ (popup hiển thị giá hiện tại)",
                        variable=self._notif_periodic).pack(side=tk.LEFT)

        r3 = ttk.Frame(ctrl)
        r3.pack(fill=tk.X, pady=(10, 0))
        self._mon_btn_txt = tk.StringVar(value="▶  Bắt đầu theo dõi")
        self._mon_btn = ttk.Button(r3, textvariable=self._mon_btn_txt,
                                    command=self._toggle_monitor)
        self._mon_btn.pack(side=tk.LEFT, ipadx=8, ipady=4)
        self._mon_status = tk.StringVar(value="Chưa bật theo dõi")
        ttk.Label(r3, textvariable=self._mon_status, foreground="gray").pack(
            side=tk.LEFT, padx=15)

        # Saved searches
        sl = ttk.LabelFrame(f, text="Cấu hình đã lưu (chọn để theo dõi)", padding=8)
        sl.pack(fill=tk.BOTH, expand=True)

        cols = ("name", "route", "dates", "type", "direct")
        self._saved_tree = ttk.Treeview(sl, columns=cols, show="headings", height=10)
        self._saved_tree.heading("name",   text="Tên")
        self._saved_tree.heading("route",  text="Tuyến")
        self._saved_tree.heading("dates",  text="Khoảng ngày đi")
        self._saved_tree.heading("type",   text="Loại")
        self._saved_tree.heading("direct", text="Bay thẳng")
        self._saved_tree.column("name",   width=160)
        self._saved_tree.column("route",  width=110, anchor=tk.CENTER)
        self._saved_tree.column("dates",  width=220)
        self._saved_tree.column("type",   width=90,  anchor=tk.CENTER)
        self._saved_tree.column("direct", width=80,  anchor=tk.CENTER)

        sb3 = ttk.Scrollbar(sl, orient=tk.VERTICAL, command=self._saved_tree.yview)
        self._saved_tree.configure(yscrollcommand=sb3.set)
        self._saved_tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        sb3.pack(side=tk.RIGHT, fill=tk.Y)

        acts = ttk.Frame(f)
        acts.pack(fill=tk.X, pady=(6, 0))
        ttk.Button(acts, text="Tải cấu hình",  command=self._load_config).pack(side=tk.LEFT, padx=(0, 8))
        ttk.Button(acts, text="Xóa cấu hình",  command=self._del_config).pack(side=tk.LEFT)

        self._refresh_saved()

    # ══ Settings Tab ══════════════════════════════════════════════════════════

    def _build_settings_tab(self, nb):
        f = ttk.Frame(nb, padding=12)
        nb.add(f, text="  Cài đặt API  ")

        api_f = ttk.LabelFrame(f, text="Nguồn dữ liệu giá vé", padding=15)
        api_f.pack(fill=tk.X)

        self._api_type = tk.StringVar(value=self.settings["api_type"])

        # ── VNA Direct (row 0-3) ──────────────────────────────────────────────
        ttk.Radiobutton(api_f,
                        text="Vietnam Airlines trực tiếp  (cần x-d-token từ browser – xem hướng dẫn bên dưới)",
                        variable=self._api_type, value="vna_direct").grid(
            row=0, column=0, columnspan=2, sticky=tk.W, pady=4)

        ttk.Label(api_f, text="x-d-token:").grid(
            row=1, column=0, sticky=tk.W, pady=4, padx=(20, 8))
        self._xd_token = tk.StringVar(value=self.settings.get("vna_xd_token", ""))
        xd_frame = ttk.Frame(api_f)
        xd_frame.grid(row=1, column=1, sticky=tk.EW)
        ttk.Entry(xd_frame, textvariable=self._xd_token, width=45).pack(side=tk.LEFT)
        self._auto_token_btn = ttk.Button(
            xd_frame, text="🔄 Tự động lấy",
            command=self._auto_fetch_xd_token)
        self._auto_token_btn.pack(side=tk.LEFT, padx=(6, 0))
        self._auto_token_status = tk.StringVar(value="")
        ttk.Label(xd_frame, textvariable=self._auto_token_status,
                  foreground="#1565c0").pack(side=tk.LEFT, padx=(6, 0))
        ttk.Label(api_f,
                  text=("→  Nhấn '🔄 Tự động lấy' để app tự lấy token qua trình duyệt ẩn\n"
                        "   hoặc lấy thủ công: F12 → Network → filter 'air-bounds' → Request Headers → x-d-token\n"
                        "   Token hợp lệ ~30 phút"),
                  foreground="#555", justify=tk.LEFT).grid(
            row=2, column=0, columnspan=2, sticky=tk.W, padx=(20, 0), pady=(0, 6))

        ttk.Separator(api_f, orient=tk.HORIZONTAL).grid(
            row=3, column=0, columnspan=2, sticky=tk.EW, pady=6)

        # ── Amadeus (row 4-8) ─────────────────────────────────────────────────
        ttk.Radiobutton(api_f,
                        text="Amadeus API  (đăng ký miễn phí, 2000 call/tháng)",
                        variable=self._api_type, value="amadeus").grid(
            row=4, column=0, columnspan=2, sticky=tk.W, pady=4)

        ttk.Label(api_f, text="Amadeus Client ID:").grid(
            row=5, column=0, sticky=tk.W, pady=6, padx=(20, 8))
        self._am_id = tk.StringVar(value=self.settings["amadeus_client_id"])
        ttk.Entry(api_f, textvariable=self._am_id, width=45).grid(row=5, column=1, sticky=tk.W)

        ttk.Label(api_f, text="Amadeus Client Secret:").grid(
            row=6, column=0, sticky=tk.W, pady=6, padx=(20, 8))
        self._am_sec = tk.StringVar(value=self.settings["amadeus_client_secret"])
        ttk.Entry(api_f, textvariable=self._am_sec, width=45, show="•").grid(
            row=6, column=1, sticky=tk.W)

        ttk.Label(api_f,
                  text="→  Đăng ký tại: https://developers.amadeus.com  (vào Self-Service → My Apps)",
                  foreground="#1565c0").grid(
            row=7, column=0, columnspan=2, sticky=tk.W, padx=(20, 0), pady=(2, 8))

        ttk.Separator(api_f, orient=tk.HORIZONTAL).grid(
            row=8, column=0, columnspan=2, sticky=tk.EW, pady=6)

        # ── Kiwi (row 9-11) ───────────────────────────────────────────────────
        ttk.Radiobutton(api_f,
                        text="Kiwi Tequila API  (miễn phí, không giới hạn – khuyến nghị dùng thay Amadeus)",
                        variable=self._api_type, value="kiwi").grid(
            row=9, column=0, columnspan=2, sticky=tk.W, pady=4)

        ttk.Label(api_f, text="Kiwi API Key:").grid(
            row=10, column=0, sticky=tk.W, pady=6, padx=(20, 8))
        self._kiwi_key = tk.StringVar(value=self.settings.get("kiwi_api_key", ""))
        ttk.Entry(api_f, textvariable=self._kiwi_key, width=45, show="•").grid(
            row=10, column=1, sticky=tk.W)

        ttk.Label(api_f,
                  text="→  Đăng ký tại: https://tequila.kiwi.com  (Partners → Get API Key)",
                  foreground="#2e7d32").grid(
            row=11, column=0, columnspan=2, sticky=tk.W, padx=(20, 0), pady=(2, 10))

        br = ttk.Frame(api_f)
        br.grid(row=12, column=0, columnspan=2, sticky=tk.W, padx=(20, 0))
        ttk.Button(br, text="💾  Lưu & Áp dụng",
                   command=self._save_api).pack(side=tk.LEFT, ipadx=6)
        ttk.Button(br, text="🔌  Kiểm tra kết nối",
                   command=self._test_conn).pack(side=tk.LEFT, padx=10)
        self._conn_lbl_var = tk.StringVar(value="")
        ttk.Label(br, textvariable=self._conn_lbl_var).pack(side=tk.LEFT)

        # Info box
        info = ttk.LabelFrame(f, text="Ghi chú", padding=12)
        info.pack(fill=tk.X, pady=(15, 0))
        notes = (
            "• Giá hiển thị là mức giá thấp nhất trong ngày, CHƯA bao gồm thuế/phí phụ.\n"
            "• Kiwi Tequila API: dễ đăng ký nhất, không giới hạn call – nên chọn option này.\n"
            "• Amadeus API test environment có thể không phản ánh đúng 100% giá thực tế.\n"
            "• VNA Direct API thử kết nối trực tiếp website – có thể bị chặn hoặc thay đổi bất kỳ lúc nào.\n"
            "• Nên dùng thông tin này làm tham khảo, xác nhận giá cuối trên website chính thức VNA."
        )
        ttk.Label(info, text=notes, justify=tk.LEFT, foreground="#555").pack(anchor=tk.W)

    # ══ Logic ═════════════════════════════════════════════════════════════════

    def _apply_api(self):
        VNADirectAPI.x_d_token = self.settings.get("vna_xd_token", "")
        t = self.settings["api_type"]
        if t == "amadeus":
            cid  = self.settings["amadeus_client_id"]
            csec = self.settings["amadeus_client_secret"]
            if cid and csec:
                self.api = AmadeusAPI(cid, csec)
            else:
                self.api = VNADirectAPI()
        elif t == "kiwi":
            key = self.settings["kiwi_api_key"]
            if key:
                self.api = KiwiAPI(key)
            else:
                self.api = VNADirectAPI()
        else:
            self.api = VNADirectAPI()
        self.monitor.set_api(self.api)

    def _code(self, val: str) -> str:
        return val.split(" - ")[0].strip()

    # ── Search ────────────────────────────────────────────────────────────────

    def _do_search(self):
        origin = self._code(self._origin.get())
        dest   = self._code(self._dest.get())
        d_from = self._dep_from.get().strip()
        d_to   = self._dep_to.get().strip()
        r_from = self._ret_from.get().strip()
        r_to   = self._ret_to.get().strip()
        trip   = self._trip.get()
        direct = self._direct.get()

        try:
            datetime.strptime(d_from, "%Y-%m-%d")
            datetime.strptime(d_to,   "%Y-%m-%d")
            if trip == "RT":
                datetime.strptime(r_from, "%Y-%m-%d")
                datetime.strptime(r_to,   "%Y-%m-%d")
        except ValueError:
            messagebox.showwarning("Ngày không hợp lệ",
                                   "Vui lòng nhập ngày theo định dạng YYYY-MM-DD")
            return

        if not self.api:
            messagebox.showerror("Chưa cấu hình API",
                                 "Vui lòng kiểm tra cài đặt API trong tab 'Cài đặt API'.")
            return

        self._search_btn.configure(state=tk.DISABLED, text="⏳  Đang tìm kiếm...")
        self._prog_var.set(0)
        self._res_prog_var.set(0)
        self._res_no_data_var.set("")
        self._status("Đang tìm kiếm...")
        self.nb.select(1)   # switch to results tab to show its progress bar

        def worker():
            try:
                out_days = (datetime.strptime(d_to, "%Y-%m-%d") -
                            datetime.strptime(d_from, "%Y-%m-%d")).days + 1
                ret_days = ((datetime.strptime(r_to, "%Y-%m-%d") -
                             datetime.strptime(r_from, "%Y-%m-%d")).days + 1
                            if trip == "RT" else 0)
                total_days = out_days + ret_days
                done_box   = [0]

                def prog(done, _total):
                    done_box[0] += 1
                    pct = done_box[0] / max(total_days, 1) * 100
                    self.q.put({"type": "progress", "pct": pct})

                out_res = self.api.search_range(origin, dest, d_from, d_to, direct, prog)
                ret_res = {}
                if trip == "RT":
                    ret_res = self.api.search_range(dest, origin, r_from, r_to, direct, prog)

                self.q.put({
                    "type":       "search_done",
                    "out_results": out_res,
                    "ret_results": ret_res,
                    "trip":       trip,
                    "origin":     origin,
                    "dest":       dest,
                })
            except Exception as ex:
                self.q.put({"type": "search_err", "msg": str(ex)})

        threading.Thread(target=worker, daemon=True).start()

    def _fill_results(self, out_res: Dict, ret_res: Dict):
        self.out_results = out_res
        self.ret_results = ret_res

        self._fill_tree(self._out_tree, out_res)
        self._fill_tree(self._ret_tree, ret_res)

        # Summary
        def best(res):
            all_f = [f for fs in res.values() for f in (fs or [])]
            if not all_f:
                return None, None
            bf = min(all_f, key=lambda f: f.price)
            return bf.date, bf.price

        od, op = best(out_res)
        rd, rp = best(ret_res)

        self._s_out.set(f"{od}: {self._fmt_price(op)}" if op else "—")
        self._s_ret.set(f"{rd}: {self._fmt_price(rp)}" if rp else "—")
        if op and rp:
            self._s_tot.set(self._fmt_price(op + rp))
        elif op:
            self._s_tot.set(self._fmt_price(op))
        else:
            self._s_tot.set("—")

        # Combos
        self._calc_combos(out_res, ret_res)

    def _fill_tree(self, tree: ttk.Treeview, res: Dict):
        tree.delete(*tree.get_children())
        if not res:
            return

        all_prices = [f.price for fs in res.values() for f in (fs or [])]
        # Colour range — safe even when no flights found at all
        min_p = min(all_prices) if all_prices else 0
        max_p = max(all_prices) if all_prices else 0
        rng   = max_p - min_p if max_p != min_p else 1

        for date in sorted(res.keys()):
            flights = res.get(date) or []
            if not flights:
                tree.insert("", tk.END,
                            values=(date, "—", "—", "—", "—", "—"),
                            tags=("none",))
                continue
            f   = min(flights, key=lambda x: x.price)
            rat = (f.price - min_p) / rng
            tag = "best" if f.price == min_p else ("cheap" if rat < 0.35 else "mid")

            dep_time = ""
            if f.departure_time:
                try:
                    dep_time = datetime.fromisoformat(f.departure_time).strftime("%H:%M")
                except Exception:
                    dep_time = f.departure_time[:5]

            dur = f.duration
            if isinstance(dur, int):
                dur = f"{dur // 60}h{dur % 60:02d}m" if dur else ""
            elif isinstance(dur, str) and dur.startswith("PT"):
                dur = dur[2:].replace("H", "h").replace("M", "m").lower()

            stops_label = "Thẳng" if f.stops == 0 else f"{f.stops} điểm dừng"

            tree.insert("", tk.END, values=(
                date,
                self._fmt_price(f.price),
                stops_label,
                f.flight_number or "VN",
                dep_time,
                dur,
            ), tags=(tag,))

    def _calc_combos(self, out_res: Dict, ret_res: Dict):
        self._combo_tree.delete(*self._combo_tree.get_children())
        if not ret_res:
            self._set_combo_txt("Không có dữ liệu chuyến về (tìm kiếm một chiều).")
            return

        unit    = self._layover_unit.get()   # "giờ" | "ngày"
        v_min   = max(1, self._layover.get())
        v_max   = max(v_min, self._layover_max.get())

        def to_days(val: int) -> int:
            return val if unit == "ngày" else max(1, (val + 23) // 24)

        min_days = to_days(v_min)
        max_days = to_days(v_max)
        unit_label = f"{v_min}–{v_max} {unit}"

        # Update hint label
        self._layover_hint.set(
            f"Lọc các tổ hợp có số đêm nghỉ từ {min_days} đến {max_days} ngày"
            + (f"  ({v_min}–{v_max} giờ)" if unit == "giờ" else ""))

        combos: List[Tuple] = []
        for od, oflights in out_res.items():
            if not oflights:
                continue
            of    = min(oflights, key=lambda f: f.price)
            od_dt = datetime.strptime(od, "%Y-%m-%d")
            for rd, rflights in ret_res.items():
                if not rflights:
                    continue
                rf     = min(rflights, key=lambda f: f.price)
                rd_dt  = datetime.strptime(rd, "%Y-%m-%d")
                nights = (rd_dt - od_dt).days
                if not (min_days <= nights <= max_days):
                    continue
                combos.append((od, of.price, rd, rf.price, of.price + rf.price, nights))

        if not combos:
            self._set_combo_txt(
                f"Không tìm thấy tổ hợp trong khoảng {unit_label}.\n"
                f"Thử mở rộng khoảng tối thiểu/tối đa hoặc điều chỉnh lại ngày bay.")
            self._layover_hint.set(
                f"⚠ 0 kết quả – khoảng ngày đi/về không có tổ hợp nào trong {min_days}–{max_days} đêm")
            return

        combos.sort(key=lambda x: x[4])
        best = combos[0]
        self._set_combo_txt(
            f"TỔ HỢP GIÁ TỐT NHẤT  (nghỉ {unit_label}, lọc {len(combos)} tổ hợp)\n\n"
            f"  ✈  Chuyến đi  : {best[0]}  →  {self._fmt_price(best[1])}\n"
            f"  ✈  Chuyến về  : {best[2]}  →  {self._fmt_price(best[3])}\n"
            f"  💰  Tổng cộng  : {self._fmt_price(best[4])}\n"
            f"  🌙  Số đêm nghỉ: {best[5]} đêm"
        )

        for i, c in enumerate(combos[:60]):
            tag = "best" if i == 0 else ("good" if i < 6 else "")
            self._combo_tree.insert("", tk.END, values=(
                c[0],
                self._fmt_price(c[1]),
                c[2],
                self._fmt_price(c[3]),
                self._fmt_price(c[4]),
                f"{c[5]} đêm",
            ), tags=(tag,))

        self.nb.select(2)

    def _set_combo_txt(self, txt: str):
        self._combo_txt.configure(state=tk.NORMAL)
        self._combo_txt.delete("1.0", tk.END)
        self._combo_txt.insert("1.0", txt)
        self._combo_txt.configure(state=tk.DISABLED)

    def _recalc_combos(self):
        if self.out_results or self.ret_results:
            self._calc_combos(self.out_results, self.ret_results)

    # ── Detail pane ───────────────────────────────────────────────────────────

    def _set_detail(self, text: str):
        self._detail.configure(state=tk.NORMAL)
        self._detail.delete("1.0", tk.END)
        self._detail.insert("1.0", text)
        self._detail.configure(state=tk.DISABLED)

    def _on_select_out(self, _event=None):
        sel = self._out_tree.selection()
        if sel:
            v = self._out_tree.item(sel[0])["values"]
            if v:
                self._set_detail(
                    f"Ngày: {v[0]}   Giá thấp nhất: {v[1]}   "
                    f"Điểm dừng: {v[2]}   Chuyến: {v[3]}   "
                    f"Giờ cất cánh: {v[4]}   Thời gian bay: {v[5]}\n"
                    "★ Giá chưa bao gồm thuế/phí. Double-click để xem danh sách tất cả chuyến trong ngày."
                )

    def _on_dbl_out(self, _event=None):
        sel = self._out_tree.selection()
        if not sel:
            return
        date = self._out_tree.item(sel[0])["values"][0]
        flights = self.out_results.get(str(date), [])
        self._show_day_popup(str(date), flights, "đi")

    def _on_dbl_ret(self, _event=None):
        sel = self._ret_tree.selection()
        if not sel:
            return
        date = self._ret_tree.item(sel[0])["values"][0]
        flights = self.ret_results.get(str(date), [])
        self._show_day_popup(str(date), flights, "về")

    def _show_day_popup(self, date: str, flights: List[FlightResult], direction: str):
        if not flights:
            DetailPopup(self.root, f"Ngày {date}",
                        f"Không có chuyến {direction} nào trong ngày {date}.")
            return
        lines = [f"Các chuyến bay {direction} ngày {date}\n{'─'*45}"]
        for i, f in enumerate(sorted(flights, key=lambda x: x.price), 1):
            dep = ""
            if f.departure_time:
                try:
                    dep = datetime.fromisoformat(f.departure_time).strftime("%H:%M")
                except Exception:
                    dep = f.departure_time[:5]
            dur = f.duration
            if isinstance(dur, int):
                dur = f"{dur // 60}h{dur % 60:02d}m" if dur else ""
            elif isinstance(dur, str) and dur.startswith("PT"):
                dur = dur[2:].replace("H", "h").replace("M", "m").lower()
            stops = "Bay thẳng" if f.stops == 0 else f"Quá cảnh {f.stops} điểm"
            lines.append(
                f"{i:2d}. {f.flight_number or 'VN':>6}  "
                f"Giờ cất cánh: {dep or '?':>5}  "
                f"Thời gian: {dur or '?':>6}  "
                f"{stops:<20}  "
                f"Giá: {f.price:>14,.0f} ₫"
            )
        lines.append("\n★ Giá chưa gồm thuế/phí phụ. Xác nhận trên website chính thức VNA.")
        DetailPopup(self.root, f"Chuyến {direction} – {date}", "\n".join(lines))

    # ── Copy / Monitor actions ────────────────────────────────────────────────

    def _copy_results(self):
        lines = [f"{APP_NAME} – Kết quả tìm kiếm ({datetime.now().strftime('%d/%m/%Y %H:%M')})\n"]
        if self.out_results:
            lines.append("=== CHUYẾN ĐI ===")
            for d, fs in sorted(self.out_results.items()):
                if fs:
                    lines.append(f"  {d}: {min(f.price for f in fs):,.0f} ₫")
        if self.ret_results:
            lines.append("\n=== CHUYẾN VỀ ===")
            for d, fs in sorted(self.ret_results.items()):
                if fs:
                    lines.append(f"  {d}: {min(f.price for f in fs):,.0f} ₫")
        self.root.clipboard_clear()
        self.root.clipboard_append("\n".join(lines))
        messagebox.showinfo("Đã sao chép", "Kết quả giá vé đã sao chép vào clipboard.")

    def _add_monitor(self):
        self.nb.select(3)
        messagebox.showinfo("Gợi ý",
                            "Lưu cấu hình tìm kiếm, sau đó bật 'Bắt đầu theo dõi'.\n"
                            "App sẽ tự động kiểm tra giá và popup thông báo.")

    # ── Saved configs ─────────────────────────────────────────────────────────

    def _save_config(self):
        origin = self._code(self._origin.get())
        dest   = self._code(self._dest.get())
        default_name = (f"{origin}-{dest} "
                        f"[{self._dep_from.get()} ~ {self._dep_to.get()}]")
        dlg = NameDialog(self.root, default_name)
        self.root.wait_window(dlg)
        name = dlg.result
        if not name:
            return
        cfg = {
            "name":        name,
            "origin":      origin,
            "destination": dest,
            "start_date":  self._dep_from.get(),
            "end_date":    self._dep_to.get(),
            "ret_start":   self._ret_from.get(),
            "ret_end":     self._ret_to.get(),
            "trip_type":   self._trip.get(),
            "direct_only": self._direct.get(),
            "monitor_interval": self._mon_interval.get(),
            "saved_at":    datetime.now().isoformat(),
        }
        saves = self.settings.get("searches", [])
        saves.append(cfg)
        self.settings["searches"] = saves
        self.settings.save()
        self._refresh_saved()
        messagebox.showinfo("Đã lưu", f"Đã lưu cấu hình: {name}")

    def _refresh_saved(self):
        self._saved_tree.delete(*self._saved_tree.get_children())
        for cfg in self.settings.get("searches", []):
            self._saved_tree.insert("", tk.END, values=(
                cfg.get("name", ""),
                f"{cfg.get('origin','')}-{cfg.get('destination','')}",
                f"{cfg.get('start_date','')} ~ {cfg.get('end_date','')}",
                "Khứ hồi" if cfg.get("trip_type") == "RT" else "Một chiều",
                "Có" if cfg.get("direct_only") else "Không",
            ))

    def _load_config(self):
        sel = self._saved_tree.selection()
        if not sel:
            return
        idx  = self._saved_tree.index(sel[0])
        cfgs = self.settings.get("searches", [])
        if idx >= len(cfgs):
            return
        cfg = cfgs[idx]
        # Populate form
        for label in AIRPORT_LABELS:
            if label.startswith(cfg.get("origin", "") + " "):
                self._origin.set(label)
            if label.startswith(cfg.get("destination", "") + " "):
                self._dest.set(label)
        self._dep_from.set(cfg.get("start_date", ""))
        self._dep_to.set(cfg.get("end_date", ""))
        self._ret_from.set(cfg.get("ret_start", ""))
        self._ret_to.set(cfg.get("ret_end", ""))
        self._trip.set(cfg.get("trip_type", "OW"))
        self._direct.set(cfg.get("direct_only", False))
        self._trip_changed()
        self.nb.select(0)

    def _del_config(self):
        sel = self._saved_tree.selection()
        if not sel:
            return
        idx  = self._saved_tree.index(sel[0])
        cfgs = self.settings.get("searches", [])
        if idx < len(cfgs):
            name = cfgs[idx].get("name", "?")
            if messagebox.askyesno("Xóa?", f"Xóa cấu hình '{name}'?"):
                cfgs.pop(idx)
                self.settings["searches"] = cfgs
                self.settings.save()
                self._refresh_saved()

    # ── Monitor ───────────────────────────────────────────────────────────────

    def _toggle_monitor(self):
        if not self._monitor_on:
            cfgs = self.settings.get("searches", [])
            if not cfgs:
                messagebox.showwarning("Chưa có cấu hình",
                                       "Hãy lưu ít nhất một cấu hình tìm kiếm trước.")
                return
            # Save current interval settings
            self.settings["monitor_interval_minutes"] = self._mon_interval.get()
            self.settings["notify_interval_minutes"]  = self._notif_interval.get()
            self.settings["notify_on_price_drop"]     = self._notif_drop.get()
            self.settings["notify_periodically"]      = self._notif_periodic.get()
            self.settings.save()

            for cfg in cfgs:
                cfg["monitor_interval"] = self._mon_interval.get()

            self.monitor.set_searches(cfgs)
            self.monitor.start()
            self._monitor_on = True
            self._mon_btn_txt.set("⏹  Dừng theo dõi")
            self._mon_status.set(f"Đang theo dõi {len(cfgs)} cấu hình...")
        else:
            self.monitor.stop()
            self._monitor_on = False
            self._mon_btn_txt.set("▶  Bắt đầu theo dõi")
            self._mon_status.set("Đã dừng")

    # ── API settings ──────────────────────────────────────────────────────────

    def _auto_fetch_xd_token(self):
        if not PLAYWRIGHT_OK:
            messagebox.showerror("Lỗi", "Playwright chưa cài.\nChạy: pip install playwright && playwright install chromium")
            return

        self._auto_token_btn.config(state=tk.DISABLED)
        self._auto_token_status.set("⏳ Đang lấy token...")

        def worker():
            token = None
            try:
                with sync_playwright() as p:
                    browser = p.chromium.launch(headless=True)
                    context = browser.new_context(
                        user_agent=(
                            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                            "AppleWebKit/537.36 (KHTML, like Gecko) "
                            "Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0"
                        )
                    )
                    page = context.new_page()

                    captured = []

                    def on_request(request):
                        if "air-bounds" in request.url:
                            xdt = request.headers.get("x-d-token", "")
                            if xdt:
                                captured.append(xdt)

                    page.on("request", on_request)
                    page.goto("https://booking.vietnamairlines.com/", timeout=30000)
                    page.wait_for_timeout(3000)

                    # Thử trigger search với route HAN→SGN để có request air-bounds
                    try:
                        page.evaluate("""
                            fetch('https://api-des.vietnamairlines.com/v2/search/air-bounds', {
                                method: 'POST',
                                headers: {'Content-Type': 'application/json'}
                            }).catch(()=>{});
                        """)
                        page.wait_for_timeout(2000)
                    except Exception:
                        pass

                    if captured:
                        token = captured[-1]
                    browser.close()
            except Exception as e:
                self.after(0, lambda: self._auto_token_status.set(f"❌ Lỗi: {e}"))
                self.after(0, lambda: self._auto_token_btn.config(state=tk.NORMAL))
                return

            if token:
                self._xd_token.set(token)
                VNADirectAPI.x_d_token = token
                self.after(0, lambda: self._auto_token_status.set("✅ Lấy token thành công!"))
            else:
                # Fallback: lấy token từ TOKEN_URL trực tiếp (không cần x-d-token)
                self.after(0, lambda: self._auto_token_status.set("⚠ Không lấy được x-d-token (dùng không có token cũng được)"))

            self.after(0, lambda: self._auto_token_btn.config(state=tk.NORMAL))

        threading.Thread(target=worker, daemon=True).start()

    def _save_api(self):
        self.settings["api_type"]              = self._api_type.get()
        self.settings["vna_xd_token"]          = self._xd_token.get().strip()
        self.settings["amadeus_client_id"]     = self._am_id.get().strip()
        self.settings["amadeus_client_secret"] = self._am_sec.get().strip()
        self.settings["kiwi_api_key"]          = self._kiwi_key.get().strip()
        self.settings.save()
        self._apply_api()
        self._conn_lbl_var.set("✔ Đã lưu")

    def _test_conn(self):
        self._conn_lbl_var.set("Đang kiểm tra...")
        test_date = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
        def worker():
            try:
                # For VNADirectAPI, test token first then search
                api = self.api
                if isinstance(api, VNADirectAPI):
                    token = VNADirectAPI._get_token()
                    if not token:
                        # Try to give a more specific error by testing the token URL directly
                        try:
                            r = requests.post(
                                VNADirectAPI.TOKEN_URL,
                                data={"grant_type": "client_credentials",
                                      "client_id": VNADirectAPI.CLIENT_ID,
                                      "client_secret": VNADirectAPI.CLIENT_SECRET},
                                headers={"Content-Type": "application/x-www-form-urlencoded",
                                         "Origin": "https://booking.vietnamairlines.com"},
                                timeout=12)
                            self.q.put({"type": "conn_err",
                                        "msg": f"Token thất bại: HTTP {r.status_code} — {r.text[:120]}"})
                        except Exception as te:
                            self.q.put({"type": "conn_err", "msg": f"Không kết nối được token endpoint: {te}"})
                        return
                res = api.search("HAN", "SGN", test_date)
                if res:
                    self.q.put({"type": "conn_ok", "count": len(res)})
                else:
                    # Try raw request to get error detail
                    token = VNADirectAPI._token if isinstance(api, VNADirectAPI) else None
                    if token:
                        try:
                            r = requests.post(
                                VNADirectAPI.SEARCH_URL,
                                json={"commercialFareFamilies": ["WEB"],
                                      "itineraries": [{"departureDateTime": f"{test_date}T00:00:00.000",
                                                        "originLocationCode": "HAN",
                                                        "destinationLocationCode": "SGN"}],
                                      "searchPreferences": {"showMilesPrice": False},
                                      "travelers": [{"passengerTypeCode": "ADT"}]},
                                headers={**VNADirectAPI.HEADERS, "Authorization": f"Bearer {token}"},
                                timeout=20)
                            self.q.put({"type": "conn_err",
                                        "msg": f"Search HTTP {r.status_code} — {r.text[:150]}"})
                        except Exception as se:
                            self.q.put({"type": "conn_err", "msg": f"Search lỗi: {se}"})
                    else:
                        self.q.put({"type": "conn_err", "msg": "Không tìm thấy chuyến bay (0 kết quả)"})
            except Exception as ex:
                self.q.put({"type": "conn_err", "msg": str(ex)})
        threading.Thread(target=worker, daemon=True).start()

    # ── Queue / main loop ─────────────────────────────────────────────────────

    def _poll(self):
        try:
            while True:
                msg = self.q.get_nowait()
                self._handle(msg)
        except queue.Empty:
            pass
        self.root.after(250, self._poll)

    def _handle(self, msg: Dict):
        t = msg["type"]

        if t == "progress":
            pct = min(100.0, msg["pct"])
            self._prog_var.set(pct)
            self._res_prog_var.set(pct)
            self._res_prog_lbl.set(f"Đang tìm kiếm… {pct:.0f}%")

        elif t == "search_done":
            self._search_btn.configure(state=tk.NORMAL, text="🔍  Tìm giá rẻ nhất")
            self._prog_var.set(100)
            self._res_prog_var.set(100)
            ts = datetime.now().strftime("%H:%M:%S")
            out, ret = msg["out_results"], msg["ret_results"]
            n_out = sum(1 for fs in out.values() if fs)
            n_ret = sum(1 for fs in ret.values() if fs)
            self._res_prog_lbl.set(
                f"Hoàn tất lúc {ts} — Tìm thấy: {n_out} ngày có chuyến đi"
                + (f", {n_ret} ngày có chuyến về" if ret else ""))
            self._fill_results(out, ret)
            # Show no-data warning if API returned nothing
            if n_out == 0:
                self._res_no_data_var.set(
                    "⚠  Không tìm thấy chuyến bay nào. Có thể API VNA Direct chưa kết nối được.\n"
                    "→ Vào tab 'Cài đặt API', chọn Amadeus API và nhập key miễn phí từ "
                    "developers.amadeus.com để có dữ liệu chính xác hơn.")
                self._res_no_data_lbl.pack(fill=tk.X, pady=(0, 6))
            else:
                self._res_no_data_var.set("")
                self._res_no_data_lbl.pack_forget()
            self._status(f"Tìm kiếm hoàn tất — {ts}")

        elif t == "search_err":
            self._search_btn.configure(state=tk.NORMAL, text="🔍  Tìm giá rẻ nhất")
            self._prog_var.set(0)
            self._res_prog_var.set(0)
            self._res_prog_lbl.set("")
            self._status(f"Lỗi: {msg['msg']}")
            self._res_no_data_var.set(f"⚠  Lỗi: {msg['msg']}")
            self._res_no_data_lbl.pack(fill=tk.X, pady=(0, 6))
            messagebox.showerror("Lỗi tìm kiếm",
                f"{msg['msg']}\n\nGợi ý: Thử dùng Amadeus API hoặc kiểm tra kết nối mạng.")

        elif t == "monitor_update":
            cfg  = msg["cfg"]
            best = msg["cheapest"]
            route = f"{cfg['origin']}→{cfg['destination']}"
            self._mon_status.set(f"Cập nhật lúc {datetime.now().strftime('%H:%M:%S')}")

            if best:
                now = time.time()
                notif_gap = self._notif_interval.get() * 60

                if msg["price_dropped"] and self._notif_drop.get():
                    Notifier.toast(
                        f"✈ Giá vé GIẢM! {route}",
                        f"Ngày {best.date}: {best.price:,.0f} ₫\n"
                        f"(Trước: {msg['prev_price']:,.0f} ₫)",
                        min_gap_sec=0,
                    )
                elif self._notif_periodic.get() and (now - self._last_notify) >= notif_gap:
                    self._last_notify = now
                    Notifier.toast(
                        f"✈ Cập nhật giá {route}",
                        f"Giá thấp nhất: ngày {best.date} — {best.price:,.0f} ₫",
                        min_gap_sec=0,
                    )

        elif t == "conn_ok":
            self._conn_lbl_var.set(f"✔ OK – tìm thấy {msg['count']} chuyến mẫu")
        elif t == "conn_err":
            self._conn_lbl_var.set(f"✘ Lỗi: {msg['msg'][:60]}")
        elif t == "rate_updated":
            self._rate_lbl.set(ExchangeRate.rate_label())

    def _status(self, text: str):
        self._status_var.set(text)

    # ── Currency helpers ──────────────────────────────────────────────────────

    def _fmt_price(self, vnd: float) -> str:
        """Format giá theo đơn vị hiện tại."""
        cur = self._currency.get() if hasattr(self, "_currency") else "VND"
        if cur == "JPY":
            jpy = ExchangeRate.vnd_to_jpy(vnd)
            return f"¥{jpy:,.0f}"
        elif cur == "Cả hai":
            jpy = ExchangeRate.vnd_to_jpy(vnd)
            return f"{vnd:,.0f} ₫  (¥{jpy:,.0f})"
        else:
            return f"{vnd:,.0f} ₫"

    def _on_currency_change(self):
        self.settings["currency"] = self._currency.get()
        # Re-render tables with new currency
        if self.out_results or self.ret_results:
            self._fill_results(self.out_results, self.ret_results)

    def _refresh_rate(self):
        self._rate_lbl.set("Đang cập nhật...")
        def worker():
            ok = ExchangeRate.fetch_now()
            self.q.put({"type": "rate_updated", "ok": ok})
        threading.Thread(target=worker, daemon=True).start()

    def _fetch_rate_bg(self):
        ExchangeRate.fetch_now()
        self.q.put({"type": "rate_updated", "ok": True})

    # ── Calendar picker ───────────────────────────────────────────────────────

    def _open_picker(self, which: str):
        if which == "dep":
            picker = DateRangePicker(
                self.root, title="Chọn khoảng ngày đi",
                start_str=self._dep_from.get(),
                end_str=self._dep_to.get())
            self.root.wait_window(picker)
            if picker.result_start:
                self._dep_from.set(picker.result_start)
            if picker.result_end:
                self._dep_to.set(picker.result_end)
            self._dep_range_var.set(self._fmt_date_range(self._dep_from, self._dep_to))
        else:
            picker = DateRangePicker(
                self.root, title="Chọn khoảng ngày về",
                start_str=self._ret_from.get(),
                end_str=self._ret_to.get())
            self.root.wait_window(picker)
            if picker.result_start:
                self._ret_from.set(picker.result_start)
            if picker.result_end:
                self._ret_to.set(picker.result_end)
            self._ret_range_var.set(self._fmt_date_range(self._ret_from, self._ret_to))

    @staticmethod
    def _fmt_date_range(sv_from: tk.StringVar, sv_to: tk.StringVar) -> str:
        s, e = sv_from.get(), sv_to.get()
        try:
            nights = (datetime.strptime(e, "%Y-%m-%d") -
                      datetime.strptime(s, "%Y-%m-%d")).days
            return f"📅  {s}  →  {e}  ({nights} đêm)"
        except Exception:
            return f"📅  {s}  →  {e}"

    # ── Auto refresh ──────────────────────────────────────────────────────────

    def _toggle_auto_refresh(self):
        if self._auto_refresh.get():
            self._schedule_auto_refresh()
        else:
            if self._auto_refresh_job:
                self.root.after_cancel(self._auto_refresh_job)
                self._auto_refresh_job = None
            self._ar_status.set("")

    def _schedule_auto_refresh(self):
        interval_ms = self._ar_interval.get() * 60 * 1000
        self._auto_refresh_job = self.root.after(interval_ms, self._auto_refresh_tick)
        mins = self._ar_interval.get()
        self._ar_status.set(f"Sẽ làm mới sau {mins} phút")

    def _auto_refresh_tick(self):
        if not self._auto_refresh.get():
            return
        self._ar_status.set("Đang làm mới...")
        self._do_search()
        # Reschedule after search finishes (approx)
        self._auto_refresh_job = self.root.after(
            self._ar_interval.get() * 60 * 1000,
            self._auto_refresh_tick)

    def _on_close(self):
        self.monitor.stop()
        if self._auto_refresh_job:
            self.root.after_cancel(self._auto_refresh_job)
        self.settings["min_layover_value"]        = self._layover.get()
        self.settings["max_layover_value"]        = self._layover_max.get()
        self.settings["min_layover_unit"]         = "days" if self._layover_unit.get() == "ngày" else "hours"
        self.settings["monitor_interval_minutes"] = self._mon_interval.get()
        self.settings["notify_interval_minutes"]  = self._notif_interval.get()
        self.settings["currency"]                 = self._currency.get()
        self.settings.save()
        self.root.destroy()

    def run(self):
        self.root.mainloop()


# ─── Entry Point ──────────────────────────────────────────────────────────────

if __name__ == "__main__":
    App().run()
