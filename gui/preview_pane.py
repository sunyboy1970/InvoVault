"""发票预览面板：双击行时从右侧滑出显示发票图片，随面板大小自适应缩放"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton,
                             QHBoxLayout, QScrollArea)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QResizeEvent
from pathlib import Path

MIN_PREVIEW_WIDTH = 360


class PreviewPane(QWidget):
    """发票预览面板，可隐藏/显示，可随 QSplitter 自由缩放"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_file = None
        self.current_info = ""
        self._pixmap_cache = None  # 缓存原始高分辨率 QPixmap
        self._setup_ui()
        self.setVisible(False)

    def _setup_ui(self):
        self.setMinimumWidth(MIN_PREVIEW_WIDTH)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题栏
        title_bar = QWidget()
        title_bar.setStyleSheet("background-color: #2c3e50;")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(10, 8, 8, 8)

        self.title_label = QLabel("发票预览")
        self.title_label.setStyleSheet(
            "color: white; font-weight: bold; font-size: 14px;")
        title_layout.addWidget(self.title_label)
        title_layout.addStretch()

        self.btn_close = QPushButton("✕")
        self.btn_close.setFixedSize(28, 28)
        self.btn_close.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c; color: white; font-weight: bold;
                border: none; border-radius: 4px; font-size: 14px;
            }
            QPushButton:hover { background-color: #c0392b; }
        """)
        self.btn_close.clicked.connect(self.hide_preview)
        title_layout.addWidget(self.btn_close)
        layout.addWidget(title_bar)

        # 文件信息
        self.info_label = QLabel()
        self.info_label.setWordWrap(True)
        self.info_label.setStyleSheet(
            "padding: 8px 12px; background: #f8f9fa; "
            "border-bottom: 1px solid #ddd; font-size: 12px;")
        layout.addWidget(self.info_label)

        # 滚动区域显示图片（关键：setWidgetResizable=True 让图片跟随）
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: #ecf0f1; border: none;")
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("padding: 10px;")
        self.image_label.setMinimumSize(MIN_PREVIEW_WIDTH - 20, 400)
        self.scroll.setWidget(self.image_label)
        layout.addWidget(self.scroll, stretch=1)

        # 分割线
        self.setStyleSheet("border-left: 2px solid #bdc3c7;")

    def show_preview(self, file_path: str, info_text: str = ""):
        """显示指定发票文件的预览图片，并缓存原始像素图"""
        self.current_file = file_path
        self.current_info = info_text
        self.info_label.setText(info_text)
        self.image_label.setText("加载中...")
        self._pixmap_cache = None
        self.setVisible(True)

        fp = Path(file_path)
        if fp.suffix.lower() == ".pdf":
            try:
                import fitz
                doc = fitz.open(str(fp))
                if doc.page_count > 0:
                    page = doc[0]
                    # 用 2x 渲染保证清晰度
                    rect = page.rect
                    zoom = max(2.0, 1200 / rect.width)
                    mat = fitz.Matrix(zoom, zoom)
                    pix = page.get_pixmap(matrix=mat)
                    img_bytes = pix.tobytes("png")
                    pixmap = QPixmap()
                    pixmap.loadFromData(img_bytes)
                    self._pixmap_cache = pixmap  # 存原始高清图
                    self._update_preview_size()  # 自适应缩放
                doc.close()
            except Exception as e:
                self.image_label.setText(f"无法渲染预览:\n{e}")
        elif fp.suffix.lower() == ".ofd":
            self.image_label.setText(
                "OFD 格式暂不支持图片预览\n"
                "（数据已提取为文本，可查看Excel输出）")
        else:
            self.image_label.setText("不支持的文件格式")

    def _update_preview_size(self):
        """根据当前面板宽度重新缩放图片"""
        if self._pixmap_cache is None:
            return
        # 可用宽度 = 面板宽度减去边距
        avail_width = max(self.width() - 40, MIN_PREVIEW_WIDTH - 40)
        # 缩放：按比例缩放到填满可用宽度
        scaled = self._pixmap_cache.scaledToWidth(
            avail_width, Qt.SmoothTransformation)
        # 限制最大高度（避免无限高），用户可滚动查看
        if scaled.height() > 900:
            scaled = scaled.scaledToHeight(900, Qt.SmoothTransformation)
        self.image_label.setPixmap(scaled)
        self.image_label.setFixedSize(scaled.size())

    def resizeEvent(self, event: QResizeEvent):
        """面板大小变化时自动重新缩放图片"""
        super().resizeEvent(event)
        if self._pixmap_cache is not None:
            self._update_preview_size()

    def hide_preview(self):
        self.setVisible(False)
        self.current_file = None
        self.current_info = ""
        self._pixmap_cache = None
        self.image_label.clear()
