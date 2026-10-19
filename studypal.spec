# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_all, collect_submodules

block_cipher = None

# 1. Collect PySide6
pyside6_datas, pyside6_binaries, pyside6_hiddenimports = collect_all('PySide6')

# 2. Collect ML libraries safely
hidden_imports = []
hidden_imports += collect_submodules('faster_whisper')
hidden_imports += collect_submodules('ctranslate2')
hidden_imports += collect_submodules('argostranslate')
hidden_imports += collect_submodules('stt')
hidden_imports += collect_submodules('services')
hidden_imports += collect_submodules('gui')
hidden_imports += collect_submodules('annotations')
hidden_imports += collect_submodules('utils')

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=pyside6_binaries,
    datas=[
        ('src', 'src'),
    ] + pyside6_datas,
    hiddenimports=[
        'sounddevice', 'soundfile', 'numpy', 'pypdf', 'docx', 'pyttsx3',
    ] + hidden_imports + pyside6_hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'PySide6.QtWebEngine', 'PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets',
        'PySide6.QtMultimedia', 'PySide6.QtBluetooth', 'PySide6.QtNfc', 'PySide6.QtPositioning',
        'PySide6.QtSql', 'PySide6.QtTest', 'PySide6.QtDesigner', 'PySide6.QtHelp',
        'PySide6.Qt3DCore', 'PySide6.Qt3DRender', 'PySide6.QtCharts', 'PySide6.QtDataVisualization',
        'PySide6.QtQuick', 'PySide6.QtQml',
        'tensorflow', 'pandas', 'matplotlib', 'scipy', 'nvidia', 'cupy', 'cuda'
    ],
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# Create the executable, but DO NOT bundle binaries/datas into it
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True, # <--- THIS IS THE MAGIC FIX
    name='StudyPal',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
)

# Collect everything into a folder
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='StudyPal',
)
