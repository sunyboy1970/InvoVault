# -*- mode: python ; coding: utf-8 -*-
"""InvoVault Windows PyInstaller 构建配置（onedir 模式）
用法: pyinstaller fapiaobao_win.spec
生成: dist/InvoVault/InvoVault.exe  (整个 InvoVault 文件夹需一起分发)
"""
import os

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[],
    hiddenimports=[
        'core.models', 'core.pipeline', 'core.pdf_parser',
        'core.ofd_parser', 'core.tax_rules', 'core.excel_exporter',
        'core.category_mapper',
        'core.extractors.base', 'core.extractors.vat_special',
        'core.extractors.vat_normal', 'core.extractors.railway',
        'core.extractors.air', 'core.extractors.toll',
        'core.extractors.ride_hailing', 'core.extractors.vehicle_sales',
        'core.extractors.customs', 'core.extractors.others',
        'gui.main_window', 'gui.invoice_table', 'gui.preview_pane', 'gui.worker',
        'PyQt5.QtCore', 'PyQt5.QtWidgets', 'PyQt5.QtGui', 'PyQt5.QtSvg',
        'openpyxl', 'openpyxl.styles', 'openpyxl.utils',
        'fitz', 'requests', 'lxml',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=['win_runtime_hook.py'],
    excludes=[
        'tkinter', 'matplotlib', 'scipy', 'sympy',
        'notebook', 'jupyter', 'IPython', 'PIL', 'Pillow',
        'numpy', 'pandas',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz, a.scripts,
    exclude_binaries=True,
    name='InvoVault',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    console=False,
    disable_windowed_traceback=False,
    icon='fapiaobao.ico',
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=True, upx_exclude=[],
    name='InvoVault',
)
