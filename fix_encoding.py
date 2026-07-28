"""PyInstaller 运行时钩子：修复 macOS 中文路径编码问题"""
import os
import sys
import locale

# 强制 UTF-8 编码，避免 PyQt5 在中文路径下 latin-1 崩溃
os.environ.setdefault("LANG", "zh_CN.UTF-8")
os.environ.setdefault("LC_ALL", "zh_CN.UTF-8")
# 修复 Python 默认编码
if hasattr(sys, 'setdefaultencoding'):
    pass  # Python 2 only

# 确保文件系统编码为 UTF-8
reload(sys).setdefaultencoding('utf-8') if hasattr(sys, 'setdefaultencoding') else None
