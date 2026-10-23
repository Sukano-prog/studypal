from pathlib import Path

p = Path("src/utils/paths.py")
src = p.read_text(encoding="utf-8")

# 1. Add sys import if missing
if "import sys" not in src.split("\n")[0:20]:
    # Insert after the existing imports
    lines = src.split("\n")
    for i, line in enumerate(lines):
        if line.startswith("import ") or line.startswith("from "):
            # Find last import
            last_import = i
    lines.insert(last_import + 1, "import sys")
    src = "\n".join(lines)
    print("✅ Added 'import sys'")

# 2. Add a helper for bundle detection
if "def _is_frozen()" not in src:
    # Insert helper before get_piper_voices_dir
    marker = "def get_piper_voices_dir() -> Path:"
    helper = '''def _is_frozen() -> bool:
    """True when running as a PyInstaller-bundled .exe."""
    return getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS")


def _meipass() -> Path:
    """PyInstaller temp dir where bundled files live."""
    return Path(sys._MEIPASS)


'''
    src = src.replace(marker, helper + marker, 1)
    print("✅ Added _is_frozen() and _meipass() helpers")

# 3. Patch get_piper_voices_dir to check _MEIPASS first
old_piper = '''def get_piper_voices_dir() -> Path:
    """Directory containing Piper voice .onnx files."""
    override = os.environ.get("STUDYPAL_PIPER_DIR")
    if override:
        return Path(override).expanduser()
    if _is_windows():
        return _windows_local_appdata() / "piper"
    return _linux_data_home() / "piper"'''

new_piper = '''def get_piper_voices_dir() -> Path:
    """Directory containing Piper voice .onnx files."""
    # If bundled .exe, voices are inside PyInstaller's temp dir
    if _is_frozen():
        return _meipass() / "piper_voices"
    override = os.environ.get("STUDYPAL_PIPER_DIR")
    if override:
        return Path(override).expanduser()
    if _is_windows():
        return _windows_local_appdata() / "piper"
    return _linux_data_home() / "piper"'''

if old_piper in src:
    src = src.replace(old_piper, new_piper, 1)
    print("✅ Patched get_piper_voices_dir for bundled .exe")
else:
    print("⚠ get_piper_voices_dir pattern not found")

# 4. Patch get_argos_models_dir (if it exists)
if "def get_argos_models_dir" in src:
    import re
    match = re.search(r"def get_argos_models_dir\(\) -> Path:.*?(?=\ndef |\Z)", src, re.S)
    if match:
        old_argos = match.group(0)
        new_argos = '''def get_argos_models_dir() -> Path:
    """Directory containing Argos translation model packages."""
    if _is_frozen():
        return _meipass() / "argos_models"
    return _windows_local_appdata() / "argos-translate" / "packages"
'''
        src = src.replace(old_argos, new_argos, 1)
        print("✅ Patched get_argos_models_dir")
else:
    print("ℹ️ No get_argos_models_dir() — checking for other argos paths")
    # Look for any argos path references
    for line in src.split("\n"):
        if "argos" in line.lower():
            print(f"  {line}")

p.write_text(src, encoding="utf-8")
print()
print("=== Syntax check ===")
import ast
try:
    ast.parse(src)
    print("✅ Syntax OK")
except Exception as e:
    print(f"❌ {e}")
