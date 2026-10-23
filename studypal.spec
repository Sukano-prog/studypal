# -*- mode: python ; coding: utf-8 -*-

import os
import glob

block_cipher = None

a = Analysis(
    ['run.py'],
    pathex=['src'],
    binaries=[
        (os.path.join(os.environ.get('LOCALAPPDATA', ''), 'Programs', 'piper', '*'), 'piper'),
    ],
    datas=[
        (os.path.join(os.environ.get('LOCALAPPDATA', ''), 'piper', '*.onnx'), 'piper_voices'),
        (os.path.join(os.environ.get('LOCALAPPDATA', ''), 'piper', '*.onnx.json'), 'piper_voices'),
        # Dynamically find Argos models (they can be in different locations)
        (glob.glob(os.path.join(os.environ.get('LOCALAPPDATA', ''), 'argos-translate', 'packages', '*.argosmodel')), 'argos_models'),
        (glob.glob(os.path.join(os.path.expanduser('~'), '.local', 'share', 'argos-translate', 'packages', '*.argosmodel')), 'argos_models'),
    ],
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