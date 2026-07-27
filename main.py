#!/usr/bin/env python3
"""电子发票提取工具 - 主入口"""
import sys
import os

# ===== Windows 修复：PyMuPDF/MuPDF 首次初始化会短暂创建窗口 =====
# 设置 dummy 视频驱动和 AGG 软件渲染，让 MuPDF 完全离屏工作
# macOS 不存在此问题（Native Cocoa 渲染无窗口闪烁）
if os.name == 'nt':
    os.environ.setdefault('SDL_VIDEODRIVER', 'dummy')
    os.environ.setdefault('PYMUPDF_DISABLE_GL', '1')
    os.environ.setdefault('FITZ_BACKEND', 'AGG')

# 确保项目根目录在路径中
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont, QIcon

from gui.main_window import MainWindow


def main():
    # 高DPI支持
    QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
    QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)

    app = QApplication(sys.argv)
    app.setApplicationName("InvoVault")
    app.setOrganizationName("InvoVault")
    app.setApplicationDisplayName("InvoVault")
    app.setDesktopFileName("InvoVault")

    # 设置全局字体
    font = QFont("PingFang SC, Microsoft YaHei, Sans", 12)
    app.setFont(font)

    # 设置窗口图标（兼容 Windows .ico 和 macOS .icns）
    base_dir = getattr(sys, '_MEIPASS', os.path.dirname(os.path.abspath(__file__)))
    for icn in ["fapiaobao.ico", "fapiaobao.icns", "invoice_icon.icns"]:
        icon_path = os.path.join(base_dir, icn)
        if os.path.exists(icon_path):
            app.setWindowIcon(QIcon(icon_path))
            break

    window = MainWindow()
    window.show()

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
