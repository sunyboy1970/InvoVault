#!/usr/bin/env python3
"""电子发票提取工具 - 主入口"""
import sys
import os

# ===== Windows 综合修复：彻底消除 MuPDF 窗口闪烁 =====
# 必须在任何第三方模块导入之前设置！
# MuPDF 在 Windows 上首次 open/get_pixmap 时会短暂创建渲染窗口
# 综合使用多个策略压制：
#   1. 环境变量 - 强制软件渲染、禁用 OpenGL/SDL 窗口
#   2. 预初始化 - 在 GUI 启动前吸收一次性的窗口创建开销
#   3. 子进程标志 - CREATE_NO_WINDOW 禁止控制台闪窗
#   4. 运行时钩子 - 从系统层面设置 env（spec 中配置）
if os.name == 'nt':
    # --- MuPDF/PyMuPDF 渲染后端控制 ---
    os.environ['MUPDF_RENDERER'] = 'strizle'     # 强制 Stripple 软件渲染
    os.environ['FZ_RENDERER'] = 'strizle'         # 别名，确保生效
    os.environ['MUPDF_DISABLE_GL'] = '1'          # 禁用 OpenGL 后端
    os.environ['PYMUPDF_DISABLE_GL'] = '1'        # PyMuPDF 禁用 GL
    os.environ['FITZ_BACKEND'] = 'AGG'            # AGG 软件渲染

    # --- SDL 视频驱动控制 ---
    os.environ['SDL_VIDEODRIVER'] = 'windib'       # Windows GDI（非 DirectX/OpenGL）
    # 'windib' 是 Windows 上最稳定的 GDI 后端
    # 'dummy' 可能导致某些功能不可用时回退创建窗口

    # --- Qt 渲染控制（防止 OpenGL 冲突）---
    os.environ['QT_OPENGL'] = 'software'           # Qt 软件 OpenGL 渲染
    os.environ['QT_QUICK_BACKEND'] = 'software'    # Qt Quick 软件后端

    # --- 禁止 Windows 错误弹窗 ---
    import ctypes
    ctypes.windll.kernel32.SetErrorMode(0x0001 | 0x0002 | 0x8000)
    # SEM_FAILCRITICALERRORS(0x0001) - 不显示严重错误对话框
    # SEM_NOGPFAULTERRORBOX(0x0002) - 不显示 GP 错误对话框
    # SEM_NOOPENFILEERRORBOX(0x8000) - 不显示文件打开错误对话框

    # --- 预初始化 fitz：在 GUI 启动前吸收一次性的窗口创建 ---
    try:
        import fitz
        # 极小体积 1x1 哑元渲染，让 MuPDF 完成所有一次性初始化
        doc = fitz.open()
        page = doc.new_page(width=1, height=1)
        pix = page.get_pixmap(dpi=72)
        _ = pix.tobytes("png")
        doc.close()
        # 标记已预初始化（供其它模块检测）
        os.environ['FITZ_PREINIT_DONE'] = '1'
    except Exception:
        pass  # 预初始化失败不影响主功能

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
