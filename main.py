#!/usr/bin/env python3
"""电子发票提取工具 - 主入口"""
import sys
import os

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
