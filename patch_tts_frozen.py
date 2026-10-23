from pathlib import Path

p = Path("src/engine/tts.py")
src = p.read_text(encoding="utf-8")

# Find the current _piper_exe resolution and add frozen check
old = '''        # Resolve the piper executable path
        # Windows: absolute path to %LOCALAPPDATA%\\\\Programs\\\\piper\\\\piper.exe
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
            self._piper_exe = _shutil.which("piper") or "piper"'''

new = '''        # Resolve the piper executable path
        # Bundled .exe: inside PyInstaller temp dir
        # Source (Windows): %LOCALAPPDATA%\\\\Programs\\\\piper\\\\piper.exe
        # Source (Linux/macOS): "piper" in PATH
        import sys as _sys
        if getattr(_sys, "frozen", False) and hasattr(_sys, "_MEIPASS"):
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
    print("✅ Patched _piper_exe for bundled .exe")
    import ast
    ast.parse(src)
    print("✅ Syntax OK")
else:
    print("⚠ Pattern not found — current _piper_exe block:")
    idx = src.find("_piper_exe")
    if idx >= 0:
        print(src[max(0, idx-300):idx+400])
