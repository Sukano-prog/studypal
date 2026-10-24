# -*- mode: python ; coding: utf-8 -*-
import os
import glob
import argostranslate.package

block_cipher = None

# Ask Argos where it actually saved the packages
argos_paths = []
try:
    argos_dir = argostranslate.package.get_package_directory()
    # PyInstaller needs a glob pattern to find files inside the directory
    argos_paths = [(os.path.join(argos_dir, '*.argosmodel'), 'argos_models')]
except Exception as e:
    print(f"Could not find argos packages: {e}")

# Build the final datas list
dynamic_datas = [
    (os.path.join(os.environ.get('LOCALAPPDATA', ''), 'piper', '*.onnx'), 'piper_voices'),
    (os.path.join(os.environ.get('LOCALAPPDATA', ''), 'piper', '*.onnx.json'), 'piper_voices'),
    (os.path.join(os.environ.get('LOCALAPPDATA', ''), 'studypal', 'models', 'medium', '*'), 'whisper_models/medium'),
] + argos_paths

a = Analysis(
    ['run.py'],
    pathex=['src'],
    binaries=[
        (os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'piper', '*'), 'piper'),
    ],
    datas=dynamic_datas,
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='StudyPal',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='StudyPal',
)
