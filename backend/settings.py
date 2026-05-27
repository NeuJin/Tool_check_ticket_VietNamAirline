"""backend/settings.py — JSON file-backed settings store."""
from __future__ import annotations

import json
from pathlib import Path

SETTINGS_FILE = Path.home() / ".vna_tracker" / "settings.json"

DEFAULT_SETTINGS = {
    "api_type":              "vna_direct",
    "vna_xd_token":          "",
    "amadeus_client_id":     "",
    "amadeus_client_secret": "",
    "kiwi_api_key":          "",
    "currency":              "VND",
    "fallback_rate":         165.0,
}


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
        SETTINGS_FILE.write_text(
            json.dumps(self.data, indent=2, ensure_ascii=False), "utf-8")

    def get(self, k, default=None):
        return self.data.get(k, default)

    def update(self, partial: dict):
        if not isinstance(partial, dict):
            return
        for k, v in partial.items():
            if k in DEFAULT_SETTINGS:
                self.data[k] = v

    def to_dict(self) -> dict:
        return dict(self.data)
