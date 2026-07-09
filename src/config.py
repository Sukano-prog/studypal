"""
Small persisted-settings helper (currently just recent files).
"""

import json
from pathlib import Path

CONFIG_FILE = Path.home() / ".studypal_recent.json"
MAX_RECENT = 10


def load_recent_files():
    if not CONFIG_FILE.exists():
        return []
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data.get("recent", [])
    except (OSError, json.JSONDecodeError):
        return []


def save_recent_files(recent_files):
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            json.dump({"recent": recent_files[:MAX_RECENT]}, f)
    except OSError:
        pass
