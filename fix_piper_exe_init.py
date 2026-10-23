from pathlib import Path
p = Path("src/engine/tts.py")
src = p.read_text(encoding="utf-8")

# Match the exact line + the next line to insert between
old = '''    def __init__(self):
        self.voice_dir = get_piper_voices_dir()
        self.cache_dir = get_cache_dir() / "tts"'''

new = '''    def __init__(self):
        self.voice_dir = get_piper_voices_dir()

        # Resolve the piper executable path
        # Windows: absolute path to %LOCALAPPDATA%\\Programs\\piper\\piper.exe
        # Linux/macOS: find "piper" in PATH via shutil.which
        import sys as _sys
        if _sys.platform == "win32":
            import os as _os
            self._piper_exe = str(
                Path(_os.environ.get("LOCALAPPDATA", ""))
                / "Programs" / "piper" / "piper.exe"
            )
        else:
            import shutil as _shutil
            self._piper_exe = _shutil.which("piper") or "piper"

        self.cache_dir = get_cache_dir() / "tts"'''

if old in src:
    src = src.replace(old, new, 1)
    p.write_text(src, encoding="utf-8")
    print("✅ Added _piper_exe to TTSGenerator.__init__")
else:
    print("⚠ Pattern not found — checking current __init__:")
    idx = src.find("    def __init__(self):")
    if idx >= 0:
        print(src[idx:idx+400])
