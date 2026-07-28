"""
File Drop Zone Component - 拖拽文件夹/文件，显示缩略图计数
"""

from typing import Optional, List, Callable, Union
from pathlib import Path
from PySide6.QtCore import (Qt, Signal, QTimer, QMimeData, QUrl, QSize, 
                            QPropertyAnimation, QEasingCurve, QRect)
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
                               QPushButton, QScrollArea, QGridLayout, QFileDialog,
                               QSizePolicy, QGraphicsOpacityEffect)
from PySide6.QtGui import (QFont, QIcon, QPixmap, QPainter, QColor, QBrush, 
                           QPen, QPainterPath, QDragEnterEvent, QDropEvent,
                           QMouseEvent, QImageReader, QDesktopServices)

from .theme import get_theme_manager, ThemeManager, COMPONENT_QSS_TEMPLATES
from .buttons import PrimaryButton, SecondaryButton, IconButton


class FileItem(QFrame):
    """单个文件项 - 显示缩略图/图标、文件名、大小、移除按钮"""
    
    removed = Signal(str)  # file_path
    clicked = Signal(str)  # file_path
    
    def __init__(self, file_path: str, parent: QWidget = None, 
                 show_thumbnail: bool = True, removable: bool = True):
        super().__init__(parent)
        self._theme_manager = get_theme_manager()
        
        self._file_path = file_path
        self._show_thumbnail = show_thumbnail
        self._removable = removable
        self._thumbnail = None
        
        self.setObjectName("FileItem")
        self.setProperty("fileItem", True)
        self.setFixedSize(140, 160)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        
        self._setup_ui()
        self._apply_theme()
        self._theme_manager.theme_changed.connect(self._apply_theme)
        
        # 异步加载缩略图
        QTimer.singleShot(0, self._load_thumbnail)
    
    def _setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)
        
        # 缩略图/图标区域
        self._thumb_label = QLabel()
        self._thumb_label.setFixedSize(120, 100)
        self._thumb_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumb_label.setScaledContents(False)
        layout.addWidget(self._thumb_label, 0, Qt.AlignmentFlag.AlignCenter)
        
        # 文件名
        self._name_label = QLabel(Path(self._file_path).name)
        self._name_label.setWordWrap(True)
        self._name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._name_label.setMaximumHeight(36)
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(int(self._theme_manager.get_color("font_sm").replace("px", "")))
        self._name_label.setFont(font)
        layout.addWidget(self._name_label)
        
        # 文件大小
        self._size_label = QLabel(self._format_size())
        self._size_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(int(self._theme_manager.get_color("font_xs").replace("px", "")))
        self._size_label.setFont(font)
        layout.addWidget(self._size_label)
        
        # 移除按钮（悬停显示）
        if self._removable:
            self._remove_btn = IconButton(tooltip="移除", size=20)
            self._remove_btn.setText("✕")
            font = QFont(self._theme_manager.get_color("font_family"))
            font.setPointSize(10)
            font.setWeight(QFont.Weight.Bold)
            self._remove_btn.setFont(font)
            self._remove_btn.hide()
            self._remove_btn.clicked.connect(lambda: self.removed.emit(self._file_path))
            
            # 放在右上角
            self._remove_btn.setParent(self)
            self._remove_btn.move(self.width() - 24, 4)
    
    def _format_size(self) -> str:
        """格式化文件大小"""
        try:
            size = Path(self._file_path).stat().st_size
            for unit in ['B', 'KB', 'MB', 'GB']:
                if size < 1024:
                    return f"{size:.1f} {unit}"
                size /= 1024
            return f"{size:.1f} TB"
        except:
            return "未知大小"
    
    def _load_thumbnail(self):
        """加载缩略图"""
        if not self._show_thumbnail:
            self._set_file_icon()
            return
        
        path = Path(self._file_path)
        suffix = path.suffix.lower()
        
        # 图片文件尝试生成缩略图
        image_extensions = {'.jpg', '.jpeg', '.png', '.bmp', '.gif', '.webp', '.tiff', '.tif'}
        if suffix in image_extensions:
            try:
                reader = QImageReader(str(path))
                reader.setAutoTransform(True)
                # 限制缩略图大小
                reader.setScaledSize(QSize(120, 100))
                image = reader.read()
                if not image.isNull():
                    pixmap = QPixmap.fromImage(image)
                    self._thumbnail = pixmap
                    self._thumb_label.setPixmap(pixmap)
                    return
            except:
                pass
        
        # 其他文件类型显示图标
        self._set_file_icon()
    
    def _set_file_icon(self):
        """设置文件类型图标"""
        path = Path(self._file_path)
        suffix = path.suffix.lower()
        
        # 根据扩展名设置图标文本
        icon_map = {
            '.pdf': '📄',
            '.doc': '📝', '.docx': '📝',
            '.xls': '📊', '.xlsx': '📊',
            '.ppt': '📽', '.pptx': '📽',
            '.txt': '📄', '.md': '📄',
            '.zip': '📦', '.rar': '📦', '.7z': '📦',
            '.py': '🐍', '.js': '📜', '.ts': '📜',
            '.html': '🌐', '.css': '🎨',
            '.json': '📋', '.xml': '📋', '.yaml': '📋', '.yml': '📋',
            '.mp4': '🎬', '.avi': '🎬', '.mov': '🎬',
            '.mp3': '🎵', '.wav': '🎵',
        }
        
        icon_text = icon_map.get(suffix, '📄')
        
        self._thumb_label.setText(icon_text)
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(48)
        self._thumb_label.setFont(font)
    
    def _apply_theme(self, theme=None):
        """应用主题"""
        tm = self._theme_manager
        colors = tm.colors
        
        self.setStyleSheet(f"""
            QFrame[fileItem="true"] {{
                background-color: {colors["card_bg"]};
                border: 1px solid {colors["card_border"]};
                border-radius: {colors["radius_md"]};
            }}
            QFrame[fileItem="true"]:hover {{
                background-color: {colors["bg_hover"]};
                border-color: {colors["border_primary"]};
            }}
            QLabel {{
                color: {colors["text_primary"]};
                background: transparent;
            }}
            QLabel[font_xs] {{
                color: {colors["text_tertiary"]};
            }}
        """)
        
        # 更新移除按钮位置
        if hasattr(self, '_remove_btn') and self._removable:
            self._remove_btn.move(self.width() - 24, 4)
    
    def enterEvent(self, event):
        """鼠标进入 - 显示移除按钮"""
        if hasattr(self, '_remove_btn') and self._removable:
            self._remove_btn.show()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开 - 隐藏移除按钮"""
        if hasattr(self, '_remove_btn') and self._removable:
            self._remove_btn.hide()
        super().leaveEvent(event)
    
    def mousePressEvent(self, event):
        """鼠标点击"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.clicked.emit(self._file_path)
        super().mousePressEvent(event)
    
    @property
    def file_path(self) -> str:
        return self._file_path


class FileDropZone(QFrame):
    """文件拖拽区域 - 支持拖拽文件/文件夹、点击选择、显示文件列表"""
    
    files_changed = Signal(list)  # file_paths
    file_clicked = Signal(str)    # file_path
    
    def __init__(self, parent: QWidget = None, 
                 accept_folders: bool = True,
                 accept_files: bool = True,
                 multiple: bool = True,
                 filters: List[str] = None,
                 max_files: int = 0,
                 show_preview: bool = True,
                 compact: bool = False):
        super().__init__(parent)
        self._theme_manager = get_theme_manager()
        
        self._accept_folders = accept_folders
        self._accept_files = accept_files
        self._multiple = multiple
        self._filters = filters or []
        self._max_files = max_files
        self._show_preview = show_preview
        self._compact = compact
        
        self._file_paths: List[str] = []
        self._file_items: List[FileItem] = []
        self._dragging = False
        
        self.setObjectName("FileDropZone")
        self.setProperty("dropzone", True)
        self.setAcceptDrops(True)
        self.setMinimumHeight(200 if not compact else 120)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        
        self._setup_ui()
        self._apply_theme()
        self._theme_manager.theme_changed.connect(self._apply_theme)
    
    def _setup_ui(self):
        """设置 UI"""
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)
        
        # 空状态/拖拽区域
        self._empty_widget = QWidget()
        self._empty_widget.setObjectName("DropZoneEmpty")
        empty_layout = QVBoxLayout(self._empty_widget)
        empty_layout.setContentsMargins(24, 32, 24, 32)
        empty_layout.setSpacing(16)
        empty_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 图标
        self._icon_label = QLabel("📁")
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(48)
        self._icon_label.setFont(font)
        empty_layout.addWidget(self._icon_label)
        
        # 标题
        self._title_label = QLabel("拖拽文件或文件夹到此处")
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(int(self._theme_manager.get_color("font_lg").replace("px", "")))
        font.setWeight(QFont.Weight.Medium)
        self._title_label.setFont(font)
        empty_layout.addWidget(self._title_label)
        
        # 副标题
        self._subtitle_label = QLabel("或点击选择文件")
        self._subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(int(self._theme_manager.get_color("font_md").replace("px", "")))
        self._subtitle_label.setFont(font)
        empty_layout.addWidget(self._subtitle_label)
        
        # 选择按钮
        self._select_btn = PrimaryButton("选择文件", self._empty_widget)
        self._select_btn.setFixedWidth(160)
        self._select_btn.clicked.connect(self._on_select_clicked)
        empty_layout.addWidget(self._select_btn, 0, Qt.AlignmentFlag.AlignCenter)
        
        # 格式提示
        if self._filters:
            self._filter_label = QLabel(f"支持格式: {', '.join(self._filters)}")
            self._filter_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            font = QFont(self._theme_manager.get_color("font_family"))
            font.setPointSize(int(self._theme_manager.get_color("font_xs").replace("px", "")))
            self._filter_label.setFont(font)
            empty_layout.addWidget(self._filter_label)
        
        self._main_layout.addWidget(self._empty_widget)
        
        # 文件列表区域（默认隐藏）
        self._list_widget = QWidget()
        self._list_widget.hide()
        list_layout = QVBoxLayout(self._list_widget)
        list_layout.setContentsMargins(12, 12, 12, 12)
        list_layout.setSpacing(8)
        
        # 头部：文件计数 + 清空按钮
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        self._count_label = QLabel("0 个文件")
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(int(self._theme_manager.get_color("font_md").replace("px", "")))
        font.setWeight(QFont.Weight.Medium)
        self._count_label.setFont(font)
        header_layout.addWidget(self._count_label)
        
        header_layout.addStretch()
        
        if self._multiple:
            self._add_btn = SecondaryButton("添加更多", self._list_widget)
            self._add_btn.setFixedWidth(100)
            self._add_btn.clicked.connect(self._on_select_clicked)
            header_layout.addWidget(self._add_btn)
            
            self._clear_btn = SecondaryButton("清空", self._list_widget)
            self._clear_btn.setFixedWidth(80)
            self._clear_btn.danger = True
            self._clear_btn.clicked.connect(self.clear)
            header_layout.addWidget(self._clear_btn)
        
        list_layout.addLayout(header_layout)
        
        # 文件网格
        from PySide6.QtWidgets import QScrollArea
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        
        self._grid_widget = QWidget()
        self._grid_layout = QGridLayout(self._grid_widget)
        self._grid_layout.setContentsMargins(0, 0, 0, 0)
        self._grid_layout.setSpacing(12)
        self._grid_layout.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        self._scroll.setWidget(self._grid_widget)
        list_layout.addWidget(self._scroll, 1)
        
        self._main_layout.addWidget(self._list_widget)
    
    def _apply_theme(self, theme=None):
        """应用主题"""
        tm = self._theme_manager
        qss = tm.get_qss(COMPONENT_QSS_TEMPLATES["drop_zone"])
        
        # 额外样式
        extra_qss = f"""
            QWidget#DropZoneEmpty {{
                background: transparent;
            }}
            QLabel {{
                color: {tm.get_color("text_primary")};
            }}
        """
        self.setStyleSheet(qss + extra_qss)
    
    def _on_select_clicked(self):
        """点击选择文件/文件夹"""
        if self._accept_folders and not self._accept_files:
            # 只选文件夹
            dir_path = QFileDialog.getExistingDirectory(
                self, "选择文件夹", "", QFileDialog.Option.ShowDirsOnly)
            if dir_path:
                self._add_paths([dir_path])
        elif self._accept_files and not self._accept_folders:
            # 只选文件
            filter_str = "所有文件 (*.*)"
            if self._filters:
                filter_str = "支持格式 (" + " ".join(f"*{f}" for f in self._filters) + ");;" + filter_str
            
            files, _ = QFileDialog.getOpenFileNames(
                self, "选择文件", "", filter_str)
            if files:
                self._add_paths(files)
        else:
            # 文件和文件夹都可以选 - 使用自定义对话框或默认文件选择
            files, _ = QFileDialog.getOpenFileNames(
                self, "选择文件或文件夹", "", "所有文件 (*.*)")
            if files:
                self._add_paths(files)
    
    def _add_paths(self, paths: List[str]):
        """添加路径（去重、过滤、检查最大数量）"""
        for path in paths:
            path = str(Path(path).resolve())
            
            # 检查是否已存在
            if path in self._file_paths:
                continue
            
            # 检查最大数量
            if self._max_files > 0 and len(self._file_paths) >= self._max_files:
                show_toast(self, f"最多只能添加 {self._max_files} 个文件", ToastType.WARNING)
                break
            
            # 过滤文件类型
            if self._filters and Path(path).is_file():
                suffix = Path(path).suffix.lower()
                if suffix not in [f.lower() for f in self._filters]:
                    continue
            
            self._file_paths.append(path)
        
        self._update_ui()
        self.files_changed.emit(self._file_paths)
    
    def _update_ui(self):
        """更新 UI"""
        has_files = len(self._file_paths) > 0
        
        self._empty_widget.setVisible(not has_files)
        self._list_widget.setVisible(has_files)
        
        if has_files:
            self._count_label.setText(f"{len(self._file_paths)} 个文件")
            self._rebuild_grid()
    
    def _rebuild_grid(self):
        """重建文件网格"""
        # 清除旧项
        for item in self._file_items:
            item.removed.disconnect()
            item.clicked.disconnect()
            item.deleteLater()
        self._file_items.clear()
        
        # 计算列数
        container_width = self._scroll.viewport().width() or 600
        item_width = 140 + 12  # item + spacing
        cols = max(1, container_width // item_width)
        
        # 添加新项
        for i, path in enumerate(self._file_paths):
            item = FileItem(path, self._grid_widget, self._show_preview, True)
            item.removed.connect(self._on_file_removed)
            item.clicked.connect(self._on_file_clicked)
            
            row = i // cols
            col = i % cols
            self._grid_layout.addWidget(item, row, col)
            self._file_items.append(item)
    
    def _on_file_removed(self, file_path: str):
        """文件被移除"""
        self.remove_file(file_path)
    
    def _on_file_clicked(self, file_path: str):
        """文件被点击"""
        self.file_clicked.emit(file_path)
    
    def remove_file(self, file_path: str):
        """移除文件"""
        if file_path in self._file_paths:
            self._file_paths.remove(file_path)
            self._update_ui()
            self.files_changed.emit(self._file_paths)
    
    def clear(self):
        """清空所有文件"""
        self._file_paths.clear()
        self._update_ui()
        self.files_changed.emit(self._file_paths)
    
    def get_files(self) -> List[str]:
        """获取文件列表"""
        return self._file_paths.copy()
    
    def set_files(self, paths: List[str]):
        """设置文件列表"""
        self._file_paths = [str(Path(p).resolve()) for p in paths]
        self._update_ui()
        self.files_changed.emit(self._file_paths)
    
    def add_file(self, file_path: str):
        """添加单个文件"""
        self._add_paths([file_path])
    
    # 拖拽事件
    def dragEnterEvent(self, event: QDragEnterEvent):
        """拖拽进入"""
        if self._can_accept_mime(event.mimeData()):
            event.acceptProposedAction()
            self._set_dragging(True)
        else:
            event.ignore()
    
    def dragLeaveEvent(self, event):
        """拖拽离开"""
        self._set_dragging(False)
    
    def dragMoveEvent(self, event: QDragEnterEvent):
        """拖拽移动"""
        if self._can_accept_mime(event.mimeData()):
            event.acceptProposedAction()
        else:
            event.ignore()
    
    def dropEvent(self, event: QDropEvent):
        """放下文件"""
        self._set_dragging(False)
        
        if not self._can_accept_mime(event.mimeData()):
            return
        
        urls = event.mimeData().urls()
        paths = []
        for url in urls:
            if url.isLocalFile():
                paths.append(url.toLocalFile())
        
        if paths:
            self._add_paths(paths)
            event.acceptProposedAction()
    
    def _can_accept_mime(self, mime_data: QMimeData) -> bool:
        """检查是否接受 MIME 数据"""
        if not mime_data.hasUrls():
            return False
        
        urls = mime_data.urls()
        for url in urls:
            if not url.isLocalFile():
                return False
            
            path = url.toLocalFile()
            path_obj = Path(path)
            
            if path_obj.is_dir() and not self._accept_folders:
                return False
            if path_obj.is_file() and not self._accept_files:
                return False
        
        return True
    
    def _set_dragging(self, dragging: bool):
        """设置拖拽状态"""
        if self._dragging != dragging:
            self._dragging = dragging
            self.setProperty("dragging", dragging)
            self.style().unpolish(self)
            self.style().polish(self)
            
            if dragging:
                self._icon_label.setText("📥")
            else:
                self._icon_label.setText("📁")
    
    def mousePressEvent(self, event: QMouseEvent):
        """鼠标点击 - 空状态下打开选择"""
        if event.button() == Qt.MouseButton.LeftButton and not self._file_paths:
            self._on_select_clicked()
        super().mousePressEvent(event)


# 导入 Toast
from .notifications import Toast, ToastType, show_toast


class FileList(QWidget):
    """文件列表 - 紧凑模式，适合侧边栏或表格内嵌"""
    
    file_removed = Signal(str)
    file_clicked = Signal(str)
    files_reordered = Signal(list)
    
    def __init__(self, parent: QWidget = None, files: List[str] = None,
                 show_thumbnail: bool = True, removable: bool = True,
                 reorderable: bool = False):
        super().__init__(parent)
        self._theme_manager = get_theme_manager()
        
        self._show_thumbnail = show_thumbnail
        self._removable = removable
        self._reorderable = reorderable
        self._file_items = []
        
        self._setup_ui()
        self._apply_theme()
        self._theme_manager.theme_changed.connect(self._apply_theme)
        
        if files:
            self.set_files(files)
    
    def _setup_ui(self):
        """设置 UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        from PySide6.QtWidgets import QScrollArea
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self._container = QWidget()
        self._container_layout = QVBoxLayout(self._container)
        self._container_layout.setContentsMargins(0, 0, 0, 0)
        self._container_layout.setSpacing(4)
        self._container_layout.addStretch()
        
        self._scroll.setWidget(self._container)
        layout.addWidget(self._scroll)
    
    def _apply_theme(self, theme=None):
        tm = self._theme_manager
        colors = tm.colors
        self.setStyleSheet(f"""
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QWidget {{
                background: transparent;
            }}
        """)
    
    def set_files(self, files: List[str]):
        """设置文件列表"""
        self.clear()
        for f in files:
            self.add_file(f)
    
    def add_file(self, file_path: str):
        """添加文件"""
        item = FileItem(file_path, self._container, self._show_thumbnail, self._removable)
        item.setFixedWidth(self.width() - 20 if self.width() > 0 else 300)
        item.removed.connect(self._on_removed)
        item.clicked.connect(self.file_clicked.emit)
        
        # 插入到 stretch 之前
        self._container_layout.insertWidget(self._container_layout.count() - 1, item)
        self._file_items.append(item)
    
    def _on_removed(self, file_path: str):
        """文件移除"""
        self.remove_file(file_path)
        self.file_removed.emit(file_path)
    
    def remove_file(self, file_path: str):
        """移除文件"""
        for item in self._file_items:
            if item.file_path == file_path:
                item.removed.disconnect()
                item.clicked.disconnect()
                self._container_layout.removeWidget(item)
                item.deleteLater()
                self._file_items.remove(item)
                break
    
    def clear(self):
        """清空"""
        for item in self._file_items:
            item.removed.disconnect()
            item.clicked.disconnect()
            item.deleteLater()
        self._file_items.clear()
    
    def get_files(self) -> List[str]:
        return [item.file_path for item in self._file_items]