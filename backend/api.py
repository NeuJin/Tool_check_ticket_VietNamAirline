"""
backend/api.py — VNA flight search API (extracted from reference/main.py).

Pure backend, no tkinter dependency. Suitable for use behind a pywebview/HTTP
bridge serving the React UI in design/.
"""
from __future__ import annotations

import json
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timedelta
from typing import Dict, List, Optional

import requests


# ─── ExchangeRate ─────────────────────────────────────────────────────────────

class ExchangeRate:
    """JPY ↔ VND rate from open.er-api.com (no key, 1h cache)."""
    _API = "https://open.er-api.com/v6/latest/JPY"
    _rate_vnd_per_jpy: float = 165.0
    _fetched_at: float = 0.0
    _TTL = 3600

    @classmethod
    def jpy_to_vnd(cls, jpy: float) -> float:
        cls._maybe_refresh()
        return jpy * cls._rate_vnd_per_jpy

    @classmethod
    def vnd_to_jpy(cls, vnd: float) -> float:
        cls._maybe_refresh()
        return vnd / cls._rate_vnd_per_jpy

    @classmethod
    def rate(cls) -> float:
        cls._maybe_refresh()
        return cls._rate_vnd_per_jpy

    @classmethod
    def fetch_now(cls) -> bool:
        try:
            r = requests.get(cls._API, timeout=8)
            r.raise_for_status()
            data = r.json()
            v = data.get("rates", {}).get("VND")
            if v and float(v) > 0:
                cls._rate_vnd_per_jpy = float(v)
                cls._fetched_at = time.time()
                return True
        except Exception:
            pass
        return False

    @classmethod
    def _maybe_refresh(cls):
        if time.time() - cls._fetched_at > cls._TTL:
            threading.Thread(target=cls.fetch_now, daemon=True).start()


# ─── FlightResult / FlightAPI ─────────────────────────────────────────────────

class FlightResult:
    __slots__ = ("date", "price_vnd", "price_jpy", "departure_time",
                 "arrival_time", "stops", "duration_min", "flight_number")

    def __init__(self, date, price_vnd, price_jpy=0, departure_time="",
                 arrival_time="", stops=0, duration_min=0, flight_number=""):
        self.date           = date
        self.price_vnd      = price_vnd
        self.price_jpy      = price_jpy
        self.departure_time = departure_time
        self.arrival_time   = arrival_time
        self.stops          = stops
        self.duration_min   = duration_min
        self.flight_number  = flight_number

    def to_dict(self) -> dict:
        # Keys mirror the mock object shape in design/shared.jsx so the React
        # UI does not need to branch on data source.
        return {
            "date":        self.date,
            "price":       self.price_vnd,
            "priceJpy":    self.price_jpy,
            "depTime":     self.departure_time,
            "arrTime":     self.arrival_time,
            "stops":       self.stops,
            "durationMin": self.duration_min,
            "flightNum":   self.flight_number,
        }


class FlightAPI:
    name = "Base"

    def search(self, origin: str, destination: str, date: str,
               direct_only: bool = False) -> List[FlightResult]:
        raise NotImplementedError

    def search_range(self, origin: str, destination: str,
                     start_date: str, end_date: str,
                     direct_only: bool = False,
                     progress_cb=None,
                     max_workers: int = 6) -> Dict[str, List[FlightResult]]:
        current = datetime.strptime(start_date, "%Y-%m-%d")
        end     = datetime.strptime(end_date,   "%Y-%m-%d")
        dates: List[str] = []
        while current <= end:
            dates.append(current.strftime("%Y-%m-%d"))
            current += timedelta(days=1)

        results: Dict[str, List[FlightResult]] = {}
        done = [0]
        lock = threading.Lock()

        def fetch(ds: str):
            try:
                return ds, self.search(origin, destination, ds, direct_only) or []
            except Exception:
                return ds, []

        with ThreadPoolExecutor(max_workers=max_workers) as ex:
            futures = {ex.submit(fetch, ds): ds for ds in dates}
            for fut in as_completed(futures):
                ds, flights = fut.result()
                results[ds] = flights
                with lock:
                    done[0] += 1
                    if progress_cb:
                        try:
                            progress_cb(done[0], len(dates))
                        except Exception:
                            pass
        return results


# ─── VNADirectAPI ─────────────────────────────────────────────────────────────

class VNADirectAPI(FlightAPI):
    """Direct call to api-des.vietnamairlines.com, reverse-engineered from web."""
    name = "VNA Direct"
    GATEWAY    = "https://api-des.vietnamairlines.com"
    TOKEN_URL  = f"{GATEWAY}/v1/security/oauth2/token/initialization"
    SEARCH_URL = f"{GATEWAY}/v2/search/air-bounds"
    CLIENT_ID     = "7yA9XUB34tvB8vahz5O3CFVdGmdKT9au"
    CLIENT_SECRET = "vlaA0atz4fjdyEQZ"

    _token: Optional[str] = None
    _token_expiry: float  = 0.0
    _token_lock = threading.Lock()
    x_d_token: str = ""
    x_d_token_set_at: float = 0.0
    _xd_token_ttl: float = 30 * 60  # 30 min

    HEADERS = {
        "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                       "AppleWebKit/537.36 (KHTML, like Gecko) "
                       "Chrome/148.0.0.0 Safari/537.36 Edg/148.0.0.0"),
        "Accept":          "application/json",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type":    "application/json",
        "Origin":          "https://booking.vietnamairlines.com",
        "Referer":         "https://booking.vietnamairlines.com/",
    }

    @classmethod
    def set_xd_token(cls, token: str):
        cls.x_d_token = (token or "").strip()
        cls.x_d_token_set_at = time.time() if cls.x_d_token else 0.0
        cls.reset_oauth_token()

    @classmethod
    def reset_oauth_token(cls):
        with cls._token_lock:
            cls._token = None
            cls._token_expiry = 0.0

    @classmethod
    def token_status(cls) -> dict:
        if not cls.x_d_token:
            return {"hasToken": False, "ageSec": 0, "ttlSec": int(cls._xd_token_ttl), "expired": False}
        age = time.time() - cls.x_d_token_set_at
        return {
            "hasToken": True,
            "ageSec":   int(age),
            "ttlSec":   int(cls._xd_token_ttl),
            "expired":  age >= cls._xd_token_ttl,
        }

    @classmethod
    def _get_oauth_token(cls) -> Optional[str]:
        with cls._token_lock:
            if cls._token and time.time() < cls._token_expiry - 60:
                return cls._token
            try:
                hdrs = {
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Origin":       "https://booking.vietnamairlines.com",
                    "Referer":      "https://booking.vietnamairlines.com/",
                    "User-Agent":   cls.HEADERS["User-Agent"],
                }
                if cls.x_d_token:
                    hdrs["x-d-token"] = cls.x_d_token
                fact = json.dumps({
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
                    cls._token        = d.get("access_token")
                    cls._token_expiry = time.time() + d.get("expires_in", 1799)
                    return cls._token
            except Exception:
                pass
            return None

    # If True, the next successful search will dump the raw JSON response to
    # ~/.vna_tracker/last_response_<date>.json for debugging mismatched prices.
    DEBUG_DUMP_NEXT = False

    def search(self, origin: str, destination: str, date: str,
               direct_only: bool = False) -> List[FlightResult]:
        token = self._get_oauth_token()
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
            data = r.json()
            if VNADirectAPI.DEBUG_DUMP_NEXT:
                VNADirectAPI.DEBUG_DUMP_NEXT = False
                from pathlib import Path as _P
                dump = _P.home() / ".vna_tracker" / f"last_response_{origin}-{destination}-{date}.json"
                dump.parent.mkdir(parents=True, exist_ok=True)
                dump.write_text(json.dumps(data, indent=2, ensure_ascii=False), "utf-8")
            return self._parse(data, date, direct_only)
        except Exception:
            return []

    def _parse(self, resp: dict, date: str, direct_only: bool) -> List[FlightResult]:
        data    = resp.get("data", {})
        flights = resp.get("dictionaries", {}).get("flight", {})
        results: List[FlightResult] = []

        rate = ExchangeRate.rate() or 165.0

        for group in data.get("airBoundGroups", []):
            bd       = group.get("boundDetails", {})
            segments = bd.get("segments", [])
            stops    = max(0, len(segments) - 1)
            if direct_only and stops > 0:
                continue

            cheapest = None
            for ab in group.get("airBounds", []):
                prices = ab.get("prices", {}).get("totalPrices", [])
                # Some responses ship multiple price points (per pax-type, per
                # currency, …). Take the minimum positive total to be safe.
                totals = [p.get("total", 0) for p in prices
                          if isinstance(p.get("total", 0), (int, float))
                             and p.get("total", 0) > 0]
                if not totals:
                    continue
                total_jpy = min(totals)
                if cheapest is None or total_jpy < cheapest[0]:
                    cheapest = (total_jpy, ab, segments)

            if cheapest is None:
                continue

            total_jpy, _ab, segs = cheapest
            price_vnd = int(total_jpy * rate)

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
                price_vnd      = price_vnd,
                price_jpy      = int(total_jpy),
                departure_time = dep_time,
                arrival_time   = arr_time,
                stops          = stops,
                duration_min   = (bd.get("duration", 0) or 0) // 60,
                flight_number  = flight_num,
            ))

        return results
