# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置：InvoVault Windows 版"""
import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    # 使用相对于 spec 文件所在目录的路径
    datas=[('fapiaobao.ico', '.')],
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
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'scipy', 'sympy',
              'notebook', 'jupyter', 'IPython', 'PIL', 'Pillow',
              'numpy', 'pandas'],
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
    strip=False, upx=True, upx_exclude=[],
    console=False,              # 不显示命令行窗口
    disable_windowed_traceback=False,
    icon='fapiaobao.ico',       # .ico 格式（Windows 专用）
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=True, upx_exclude=[],
    name='InvoVault',
)

# Windows 无需 BUNDLE（那是 macOS .app 用的）
