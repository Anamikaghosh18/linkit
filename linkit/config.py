from __future__ import annotations
import json
import os
from pathlib import Path

APP_NAME = "LinkWireless"
APP_DIR = Path(os.environ.get("APPDATA", str(Path.home()))) / APP_NAME
CONFIG_PATH = APP_DIR / "config.json"
PORTAL_URL = "https://internet.lpu.in/24online/webpages/client.jsp"

DEFAULTS = {
    "ssid": "",
    "portal_url": PORTAL_URL,
    "poll_seconds": 20,
    "auto_connect": True,
    "open_portal_on_detect": True,
}

def load_config() -> dict:
    if not CONFIG_PATH.exists():
        return DEFAULTS.copy()
    try:
        data = json.loads(CONFIG_PATH.read_text(encoding="utf-8"))
        return {**DEFAULTS, **data}
    except (OSError, json.JSONDecodeError):
        return DEFAULTS.copy()

def save_config(config: dict) -> None:
    APP_DIR.mkdir(parents=True, exist_ok=True)
    # Never store passwords or other secrets in this file.
    safe = {k: v for k, v in config.items() if k not in {"password", "username"}}
    CONFIG_PATH.write_text(json.dumps(safe, indent=2), encoding="utf-8")
