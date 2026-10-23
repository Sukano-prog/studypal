from pathlib import Path
p = Path("src/engine/tts.py")
src = p.read_text(encoding="utf-8")

# 1. Replace bare "piper" with self._piper_exe
old_cmd = '''            cmd = [
                "piper",
                "--model", str(self.voice_dir / voice_info["file"]),'''
new_cmd = '''            cmd = [
                self._piper_exe,
                "--model", str(self.voice_dir / voice_info["file"]),'''

if old_cmd in src:
    src = src.replace(old_cmd, new_cmd, 1)
    print("✅ Replaced 'piper' with self._piper_exe in subprocess command")
else:
    print("⚠ Command block not found")

# 2. Add _piper_exe resolution in TTSGenerator.__init__
# Find the line where voice_dir is set
old_init = "        self.voice_dir = get_piper_voices_dir()"
new_init = '''        self.voice_dir = get_piper_voices_dir()

        # Resolve piper binary path (Windows needs absolute path, Linux uses PATH)
        import sys as _sys
        if _sys.platform == "win32":
            import os as _os
            self._piper_exe = str(Path(_os.environ.get("LOCALAPPDATA", "")) / "Programs" / "piper" / "piper.exe")
        else:
            import shutil as _shutil
            self._piper_exe = _shutil.which("piper") or "piper"'''

if old_init in src and "_piper_exe" not in src:
    src = src.replace(old_init, new_init, 1)
    print("✅ Added _piper_exe path resolution in __init__")
elif "_piper_exe" in src:
    print("✓ _piper_exe already present")
else:
    print("⚠ __init__ pattern not found")

p.write_text(src, encoding="utf-8")
