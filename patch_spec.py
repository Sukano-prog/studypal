from pathlib import Path

p = Path("studypal.spec")
src = p.read_text(encoding="utf-8")

# Add `import os` at the top if missing
if "import os" not in src.split("Analysis")[0]:
    src = src.replace(
        "block_cipher = None",
        "import os\n\nblock_cipher = None",
        1,
    )
    print("✅ Added import os")

# Replace hardcoded paths with env-var lookups
old_binaries = """    binaries=[
        ('C:\\\\Users\\\\vboxuser\\\\AppData\\\\Local\\\\Programs\\\\piper\\\\*', 'piper'),
    ],"""
new_binaries = """    binaries=[
        (os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'piper', '*'), 'piper'),
    ],"""

if old_binaries in src:
    src = src.replace(old_binaries, new_binaries, 1)
    print("✅ Patched binaries")

old_datas = """    datas=[
        ('C:\\\\Users\\\\vboxuser\\\\AppData\\\\Local\\\\piper\\\\*.onnx', 'piper_voices'),
        ('C:\\\\Users\\\\vboxuser\\\\AppData\\\\Local\\\\piper\\\\*.onnx.json', 'piper_voices'),
        ('C:\\\\Users\\\\vboxuser\\\\AppData\\\\Local\\\\argos-translate\\\\packages\\\\*.argosmodel', 'argos_models'),
    ],"""
new_datas = """    datas=[
        (os.path.join(os.environ.get('LOCALAPPDATA', ''), 'piper', '*.onnx'), 'piper_voices'),
        (os.path.join(os.environ.get('LOCALAPPDATA', ''), 'piper', '*.onnx.json'), 'piper_voices'),
        (os.path.join(os.environ.get('LOCALAPPDATA', ''), 'argos-translate', 'packages', '*.argosmodel'), 'argos_models'),
    ],"""

if old_datas in src:
    src = src.replace(old_datas, new_datas, 1)
    print("✅ Patched datas")
else:
    print("⚠ datas pattern not found — showing current:")
    idx = src.find("datas=")
    print(src[idx:idx + 400])

p.write_text(src, encoding="utf-8")
print("✅ studypal.spec patched")
