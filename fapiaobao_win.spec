# -*- mode: python ; coding: utf-8 -*-
"""InvoVault Windows PyInstaller 构建配置"""

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'PyQt5.sip',
        'openpyxl',
        'openpyxl.cell',
        'openpyxl.styles',
        'fitz',
        'requests',
        'lxml',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['win_runtime_hook.py'],
    excludes=[
        'numpy', 'pandas', 'matplotlib', 'scipy',
        'PIL.ImageShow', 'PIL.ImageGrab',
        'tkinter',
    ],
    noarchive=False,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='InvoVault',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # 无控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='fapiaobao.ico',
)
