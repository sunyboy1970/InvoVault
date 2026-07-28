# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller 打包配置：发票宝（全 ASCII 路径，杜绝 latin-1 编码崩溃）"""
import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[('/Users/hsq/dev/invoice-extractor-gui/fapiaobao.icns', '.')],
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
    name='InvoVault',        # 纯 ASCII，避免 PyQt5 latin-1 编码崩溃
    debug=False,
    bootloader_ignore_signals=False,
    strip=False, upx=True, upx_exclude=[],
    console=False,
    disable_windowed_traceback=False,
    icon='/Users/hsq/dev/invoice-extractor-gui/fapiaobao.icns',
)

coll = COLLECT(
    exe, a.binaries, a.zipfiles, a.datas,
    strip=False, upx=True, upx_exclude=[],
    name='InvoVault',
)

# .app 纯英文名，无编码问题
app = BUNDLE(
    coll,
    name='InvoVault.app',
    icon='/Users/hsq/dev/invoice-extractor-gui/fapiaobao.icns',
    bundle_identifier='com.invovault.invoice-tool',
    info_plist={
        'CFBundleName': 'InvoVault',
        'CFBundleDisplayName': 'InvoVault',
        'CFBundleExecutable': 'InvoVault',
        'CFBundleShortVersionString': '1.0.0',
        'CFBundleVersion': '1.0.0',
        'CFBundleDevelopmentRegion': 'zh_CN',
        'CFBundleInfoDictionaryVersion': '6.0',
        'CFBundlePackageType': 'APPL',
        'NSHighResolutionCapable': True,
        'NSHumanReadableCopyright': '© 2026 InvoVault',
    },
)
