from pathlib import Path

p = Path("src/engine/tts.py")
src = p.read_text(encoding="utf-8")

# Match the exact current block (no comment lines)
old = '''        if _sys.platform == "win32":
            import os as _os
            self._piper_exe = str(
                Path(_os.environ.get("LOCALAPPDATA", ""))
                / "Programs" / "piper" / "piper.exe"
            )
        else:
            import shutil as _shutil
            self._piper_exe = _shutil.which("piper") or "piper"'''

new = '''        if getattr(_sys, "frozen", False) and hasattr(_sys, "_MEIPASS"):
            # Bundled .exe: piper.exe is inside PyInstaller's temp dir
            _suffix = "piper.exe" if _sys.platform == "win32" else "piper"
            self._piper_exe = str(Path(_sys._MEIPASS) / "piper" / _suffix)
        elif _sys.platform == "win32":
            import os as _os
            self._piper_exe = str(
                Path(_os.environ.get("LOCALAPPDATA", ""))
                / "Programs" / "piper" / "piper.exe"
            )
        else:
            import shutil as _shutil
            self._piper_exe = _shutil.which("piper") or "piper"'''

if old in src:
    src = src.replace(old, new, 1)
    p.write_text(src, encoding="utf-8")
    print("✅ Patched _piper_exe with frozen check")
else:
    print("⚠ Still not matching — showing current block:")
    idx = src.find("if _sys.platform")
    if idx >= 0:
        print(repr(src[idx:idx+400]))
