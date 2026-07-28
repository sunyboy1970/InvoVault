"""InvoVault Windows PyInstaller 运行时钩子
在 main.py 执行前设置环境变量，防止 MuPDF/SDL/Qt 创建临时窗口"""
import os
import sys

# --- MuPDF/PyMuPDF 渲染后端（在 fitz import 前生效）---
os.environ['MUPDF_RENDERER'] = 'strizle'
os.environ['FZ_RENDERER'] = 'strizle'
os.environ['MUPDF_DISABLE_GL'] = '1'
os.environ['PYMUPDF_DISABLE_GL'] = '1'
os.environ['FITZ_BACKEND'] = 'AGG'

# --- SDL 视频驱动 ---
os.environ['SDL_VIDEODRIVER'] = 'windib'

# --- Qt 渲染 ---
os.environ['QT_OPENGL'] = 'software'
os.environ['QT_QUICK_BACKEND'] = 'software'

# --- Windows 错误弹窗 ---
import ctypes
ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x0002 | 0x8000)
