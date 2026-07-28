"""发票预览面板：双击行时从右侧滑出显示发票图片，随面板大小自适应缩放"""
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QLabel, QPushButton,
                             QHBoxLayout, QScrollArea)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap, QResizeEvent, QCursor
from pathlib import Path
import hashlib

MIN_PREVIEW_WIDTH = 280
_PREVIEW_CACHE = Path.home() / ".cache" / "invoice-extractor" / "previews"


class PreviewPane(QWidget):
    """发票预览面板，可隐藏/显示，随 QSplitter 自由缩放"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.current_file = None
        self.current_info = ""
        self._pixmap_cache = None  # 缓存原始高分辨率 QPixmap
        self._resize_timer = QTimer(self)
        self._resize_timer.setSingleShot(True)
        self._resize_timer.timeout.connect(self._delayed_resize)
        _PREVIEW_CACHE.mkdir(parents=True, exist_ok=True)
        self._setup_ui()
        self.setVisible(False)

    def _setup_ui(self):
        self.setMinimumWidth(MIN_PREVIEW_WIDTH)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # 标题栏（含左侧拖拽手柄提示条）
        title_bar = QWidget()
        title_bar.setStyleSheet("background-color: #2c3e50;")
        title_layout = QHBoxLayout(title_bar)
        title_layout.setContentsMargins(10, 8, 8, 8)

        # 拖拽提示条：三条竖线，提示用户可左右拖拽调整预览宽度
        drag_hint = QLabel("⋮⋮")
        drag_hint.setStyleSheet(
            "color: rgba(255,255,255,0.5); font-size: 16px; font-weight: bold; "
            "padding: 0 4px 0 0; letter-spacing: -2px;")
        drag_hint.setToolTip("← 拖拽此区域调整预览宽度 →")
        title_layout.addWidget(drag_hint)

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

        # 滚动区域显示图片
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(False)  # 改为 False，手动控制图片大小
        self.scroll.setStyleSheet("background: #ecf0f1; border: none;")
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("padding: 5px;")
        self.scroll.setWidget(self.image_label)
        layout.addWidget(self.scroll, stretch=1)

        # 预览面板左侧视觉分隔条（整个面板边框即为拖拽手柄，由 QSplitter 提供 8px 宽手柄）

    def show_preview(self, file_path: str, info_text: str = ""):
        """显示指定发票文件的预览图片，并缓存原始像素图"""
        self.current_file = file_path
        self.current_info = info_text
        self.info_label.setText(info_text)
        self.setVisible(True)

        fp = Path(file_path)
        if fp.suffix.lower() == ".pdf":
            try:
                # 1) 尝试加载缓存图
                preview_path = self._get_cached_preview(file_path)
                if preview_path and preview_path.exists():
                    pixmap = QPixmap(str(preview_path))
                    if not pixmap.isNull():
                        self._pixmap_cache = pixmap
                        self._update_preview_size()
                        return

                # 2) 缓存未命中 → 用 fitz 渲染并写入缓存
                self.info_label.setText(info_text + "\n⏳ 正在渲染预览...")
                # 先刷新界面让用户看到加载提示
                QTimer.singleShot(10, lambda: self._render_preview(file_path, preview_path))
            except Exception as e:
                self.image_label.setText(f"无法加载预览:\n{e}")
        elif fp.suffix.lower() == ".ofd":
            self.image_label.setText(
                "OFD 格式暂不支持图片预览\n"
                "（数据已提取为文本，可查看Excel输出）")
        else:
            self.image_label.setText("不支持的文件格式")

    def _render_preview(self, file_path: str, preview_path: Path):
        """在子线程友好的方式下渲染PDF预览"""
        try:
            import fitz
            doc = fitz.open(file_path)
            if doc.page_count > 0:
                page = doc[0]
                rect = page.rect
                zoom = max(2.0, 1200 / rect.width)
                mat = fitz.Matrix(zoom, zoom)
                pix = page.get_pixmap(matrix=mat)
                img_bytes = pix.tobytes("png")
                if preview_path:
                    preview_path.parent.mkdir(parents=True, exist_ok=True)
                    preview_path.write_bytes(img_bytes)
                pixmap = QPixmap()
                pixmap.loadFromData(img_bytes)
                self._pixmap_cache = pixmap
                self._update_preview_size()
            doc.close()
        except Exception as e:
            self.image_label.setText(f"无法渲染预览:\n{e}")

    def _get_cached_preview(self, file_path: str) -> Path:
        h = hashlib.sha256(str(file_path).encode('utf-8')).hexdigest()[:16]
        return _PREVIEW_CACHE / f"{h}.png"

    def _update_preview_size(self):
        """根据当前滚动区域宽度重新缩放图片"""
        if self._pixmap_cache is None:
            return

        # 用滚动区域的视口宽度更可靠（比 self.width() 减去边框更准确）
        viewport_w = self.scroll.viewport().width()
        avail_width = max(viewport_w - 20, MIN_PREVIEW_WIDTH - 40)

        # 按可用宽度等比缩放
        src_w = self._pixmap_cache.width()
        src_h = self._pixmap_cache.height()
        if src_w <= 0:
            return

        ratio = avail_width / src_w
        new_w = int(src_w * ratio)
        new_h = int(src_h * ratio)

        # 限制最大高度（保留滚动查看长图的能力）
        viewport_h = self.scroll.viewport().height()
        max_h = max(viewport_h - 20, 400)
        if new_h > max_h:
            ratio2 = max_h / new_h
            new_w = int(new_w * ratio2)
            new_h = max_h

        scaled = self._pixmap_cache.scaled(
            new_w, new_h,
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation)

        self.image_label.setPixmap(scaled)
        # 让 label 尺寸适配缩放后的图片（不要 setFixedSize，以免拖动后残留旧尺寸）
        self.image_label.resize(scaled.size())

    def resizeEvent(self, event: QResizeEvent):
        """面板大小变化时防抖重新缩放（避免频繁渲染导致卡顿）"""
        super().resizeEvent(event)
        if self._pixmap_cache is not None and self.isVisible():
            # 防抖：50ms 内多次触发只做一次缩放
            self._resize_timer.start(50)

    def _delayed_resize(self):
        """防抖后的实际缩放操作"""
        if self._pixmap_cache is not None and self.isVisible():
            self._update_preview_size()

    def hide_preview(self):
        self.setVisible(False)
        self.current_file = None
        self.current_info = ""
        self._pixmap_cache = None
        self.image_label.clear()
