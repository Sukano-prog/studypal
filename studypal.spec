# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# 1. Collect PySide6 (GUI)
pyside6_datas, pyside6_binaries, pyside6_hiddenimports = collect_all('PySide6')

# 2. Collect faster-whisper CODE ONLY (no huge models)
fw_hiddenimports = collect_submodules('faster_whisper')
ct2_hiddenimports = collect_submodules('ctranslate2')

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=pyside6_binaries,
    datas=[
        ('src', 'src'),
    ] + pyside6_datas,
    hiddenimports=[
        'sounddevice',
        'soundfile',
        'numpy',
        'pypdf',
        'docx',
        'faster_whisper',
        'ctranslate2',
        'argostranslate',
        'pyttsx3',
    ] + pyside6_hiddenimports + fw_hiddenimports + ct2_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        # Exclude massive unused Qt modules to save space
        'PySide6.QtWebEngine',
        'PySide6.QtWebEngineCore',
        'PySide6.QtWebEngineWidgets',
        'PySide6.QtMultimedia',
        'PySide6.QtBluetooth',
        'PySide6.QtNfc',
        'PySide6.QtPositioning',
        'PySide6.QtSql',
        'PySide6.QtTest',
        'PySide6.QtDesigner',
        'PySide6.QtHelp',
        'PySide6.Qt3DCore',
        'PySide6.Qt3DRender',
        'PySide6.QtCharts',
        'PySide6.QtDataVisualization',
        'PySide6.QtQuick',
        'PySide6.QtQml',
        # Exclude heavy ML stuff we don't use
        'tensorflow',
        'torch',
        'pandas',
        'matplotlib',
        'scipy'
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='StudyPal',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
