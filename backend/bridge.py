"""
backend/bridge.py — pywebview JS bridge.

Methods on `Bridge` are callable from JS via `window.pywebview.api.<method>`.
All methods must return JSON-serialisable values.
"""
from __future__ import annotations

import threading
import time
from typing import Dict, List, Optional

from .api import ExchangeRate, FlightAPI, VNADirectAPI
from .settings import Settings


class Bridge:
    def __init__(self):
        self.settings = Settings()
        self.vna      = VNADirectAPI()
        # Restore token from settings on startup
        if self.settings.get("vna_xd_token"):
            VNADirectAPI.set_xd_token(self.settings.get("vna_xd_token", ""))
        # progress state for search
        self._progress_lock = threading.Lock()
        self._progress = {"done": 0, "total": 0, "running": False}
        # Auto-arm response dump on startup — first successful search will
        # write the raw VNA JSON to ~/.vna_tracker/last_response_*.json for
        # debugging price mismatches. Re-armed after each app start.
        VNADirectAPI.DEBUG_DUMP_NEXT = True

    # ── Settings ──────────────────────────────────────────────────────────────

    def get_settings(self) -> dict:
        return self.settings.to_dict()

    def save_settings(self, partial: dict) -> dict:
        self.settings.update(partial or {})
        self.settings.save()
        # Re-apply token if it changed
        if partial and "vna_xd_token" in partial:
            VNADirectAPI.set_xd_token(partial["vna_xd_token"] or "")
        return self.settings.to_dict()

    # ── Token management ──────────────────────────────────────────────────────

    def set_xd_token(self, token: str) -> dict:
        VNADirectAPI.set_xd_token(token or "")
        self.settings.update({"vna_xd_token": VNADirectAPI.x_d_token})
        self.settings.save()
        return self.token_status()

    def token_status(self) -> dict:
        return VNADirectAPI.token_status()

    def refresh_xd_token(self) -> dict:
        """Reset the OAuth side; x-d-token must be re-pasted manually unless
        the playwright auto-fetch path is wired up (heavy dependency)."""
        VNADirectAPI.reset_oauth_token()
        return self.token_status()

    def test_connection(self) -> dict:
        """Try a token-fetch + lightweight HAN→SGN search to verify the API."""
        from datetime import datetime, timedelta
        future = (datetime.now() + timedelta(days=14)).strftime("%Y-%m-%d")
        try:
            results = self.vna.search("HAN", "SGN", future, direct_only=False)
            ok = len(results) > 0
            return {
                "ok":      ok,
                "count":   len(results),
                "message": "Kết nối OK — nhận được dữ liệu giá vé" if ok
                           else "Không có chuyến — kiểm tra x-d-token (có thể đã hết hạn)",
            }
        except Exception as e:
            return {"ok": False, "count": 0, "message": f"Lỗi: {e}"}

    # ── Exchange rate ─────────────────────────────────────────────────────────

    def exchange_rate(self) -> dict:
        # Trigger background refresh if stale
        ExchangeRate._maybe_refresh()
        return {"vndPerJpy": ExchangeRate.rate(), "fetchedAt": ExchangeRate._fetched_at}

    def refresh_exchange_rate(self) -> dict:
        ExchangeRate.fetch_now()
        return self.exchange_rate()

    # ── Search ────────────────────────────────────────────────────────────────

    def search_range(self, origin: str, destination: str,
                     start_date: str, end_date: str,
                     direct_only: bool = False) -> dict:
        """Returns {dateStr: [flight_dict, ...]} for cheapest each day."""
        with self._progress_lock:
            self._progress = {"done": 0, "total": 0, "running": True}

        def cb(done, total):
            with self._progress_lock:
                self._progress["done"]  = done
                self._progress["total"] = total

        try:
            raw = self.vna.search_range(origin, destination, start_date, end_date,
                                         direct_only=direct_only, progress_cb=cb)
        except Exception as e:
            with self._progress_lock:
                self._progress["running"] = False
            return {"error": str(e), "results": {}}
        finally:
            with self._progress_lock:
                self._progress["running"] = False

        return {
            "error":   None,
            "results": {ds: [f.to_dict() for f in flights] for ds, flights in raw.items()},
        }

    def get_progress(self) -> dict:
        with self._progress_lock:
            return dict(self._progress)

    # ── Misc ──────────────────────────────────────────────────────────────────

    def ping(self) -> str:
        return "pong"

    def dump_next_response(self) -> dict:
        """Arm a one-shot dump of the next raw API response to
        ~/.vna_tracker/last_response_<route>-<date>.json — for debugging
        price mismatches against the web."""
        VNADirectAPI.DEBUG_DUMP_NEXT = True
        return {"armed": True, "path": "~/.vna_tracker/last_response_*.json"}
