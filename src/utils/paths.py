"""Cross-platform data directories for StudyPal.

All app data lives under one root, resolved in this order:
  1. $STUDYPAL_DATA_DIR if set (portable USB-stick mode)
  2. OS-appropriate default:
       - Linux/macOS: ~/.local/share/studypal
       - Windows:     %LOCALAPPDATA%\\studypal

Cache lives separately:
  1. $STUDYPAL_CACHE_DIR if set
  2. Linux/macOS: ~/.cache/studypal
  3. Windows:     %LOCALAPPDATA%\\studypal\\Cache

Piper voices:
  1. $STUDYPAL_PIPER_DIR if set
  2. Linux/macOS: ~/.local/share/piper
  3. Windows:     %LOCALAPPDATA%\\piper
"""
import os
import platform
from pathlib import Path
import sys


def _is_windows() -> bool:
    return platform.system() == "Windows"


def _linux_data_home() -> Path:
    """XDG_DATA_HOME or ~/.local/share."""
    return Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))


def _linux_cache_home() -> Path:
    """XDG_CACHE_HOME or ~/.cache."""
    return Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))


def _windows_local_appdata() -> Path:
    """%LOCALAPPDATA%, falling back to the standard location."""
    return Path(os.environ.get(
        "LOCALAPPDATA",
        Path.home() / "AppData" / "Local",
    ))


# ─────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────

def get_data_dir() -> Path:
    """Root directory for persistent StudyPal data (DB, models)."""
    override = os.environ.get("STUDYPAL_DATA_DIR")
    if override:
        return Path(override).expanduser()
    if _is_windows():
        return _windows_local_appdata() / "studypal"
    return _linux_data_home() / "studypal"


def get_cache_dir() -> Path:
    """Root directory for regenerable caches (TTS audio, STT results)."""
    override = os.environ.get("STUDYPAL_CACHE_DIR")
    if override:
        return Path(override).expanduser()
    if _is_windows():
        return _windows_local_appdata() / "studypal" / "Cache"
    return _linux_cache_home() / "studypal"


def _is_frozen() -> bool:
    """True when running as a PyInstaller-bundled .exe."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def _meipass() -> Path:
    """PyInstaller temp dir where bundled files live."""
    return Path(sys._MEIPASS)


def get_piper_voices_dir() -> Path:
    """Directory containing Piper voice .onnx files."""
    # If bundled .exe, voices are inside PyInstaller's temp dir
    if _is_frozen():
        return _meipass() / "piper_voices"
    override = os.environ.get("STUDYPAL_PIPER_DIR")
    if override:
        return Path(override).expanduser()
    if _is_windows():
        return _windows_local_appdata() / "piper"
    return _linux_data_home() / "piper"


def get_db_path() -> Path:
    """SQLite annotations database."""
    return get_data_dir() / "annotations.db"


def get_models_dir() -> Path:
    """Local Whisper model directories (e.g. medium)."""
    return get_data_dir() / "models"


def ensure_dirs() -> None:
    """Create all required directories. Safe to call repeatedly."""
    for d in (get_data_dir(), get_cache_dir(), get_piper_voices_dir()):
        d.mkdir(parents=True, exist_ok=True)


# ─────────────────────────────────────────────────────────────
# Diagnostic helper
# ─────────────────────────────────────────────────────────────

def describe() -> str:
    """Human-readable summary of resolved paths."""
    return (
        f"StudyPal directories:\n"
        f"  data:   {get_data_dir()}\n"
        f"  cache:  {get_cache_dir()}\n"
        f"  piper:  {get_piper_voices_dir()}\n"
        f"  db:     {get_db_path()}\n"
        f"  models: {get_models_dir()}\n"
        f"  OS:     {platform.system()} {platform.release()}\n"
    )


if __name__ == "__main__":
    print(describe())
    ensure_dirs()
    print("✅ All directories created.")
