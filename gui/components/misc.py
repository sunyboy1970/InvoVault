"""
Misc Components - Divider, Badge, Tooltip
"""

from typing import Optional, Literal
from PySide6.QtCore import (Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve, 
                            QRect, QPoint, QSize, QEvent)
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
                               QApplication, QGraphicsOpacityEffect)
from PySide6.QtGui import (QFont, QPainter, QColor, QBrush, QPen, QPainterPath,
                           QCursor, QIcon)

from .theme import get_theme_manager, ThemeManager, COMPONENT_QSS_TEMPLATES


class Divider(QFrame):
    """分割线 - 水平/垂直，支持文字"""
    
    def __init__(self, parent: QWidget = None, orientation: Qt.Orientation = Qt.Orientation.Horizontal,
                 text: str = "", dashed: bool = False, thick: bool = False):
        super().__init__(parent)
        self._theme_manager = get_theme_manager()
        
        self._orientation = orientation
        self._text = text
        self._dashed = dashed
        self._thick = thick
        
        self.setObjectName("Divider")
        
        if orientation == Qt.Orientation.Horizontal:
            self.setFrameShape(QFrame.Shape.HLine)
            self.setFixedHeight(2 if thick else 1)
        else:
            self.setFrameShape(QFrame.Shape.VLine)
            self.setFixedWidth(2 if thick else 1)
        
        self.setFrameShadow(QFrame.Shadow.Plain)
        
        if text:
            self._setup_text()
        
        self._apply_theme()
        self._theme_manager.theme_changed.connect(self._apply_theme)
    
    def _setup_text(self):
        """设置带文字的分割线"""
        # 使用布局包含文字
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 左线
        left_line = QFrame()
        left_line.setFrameShape(QFrame.Shape.HLine)
        left_line.setFrameShadow(QFrame.Shadow.Plain)
        left_line.setFixedHeight(1)
        layout.addWidget(left_line, 1)
        
        # 文字
        text_label = QLabel(self._text)
        text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(int(self._theme_manager.get_color("font_xs").replace("px", "")))
        text_label.setFont(font)
        layout.addWidget(text_label)
        
        # 右线
        right_line = QFrame()
        right_line.setFrameShape(QFrame.Shape.HLine)
        right_line.setFrameShadow(QFrame.Shadow.Plain)
        right_line.setFixedHeight(1)
        layout.addWidget(right_line, 1)
        
        self._text_label = text_label
        self._left_line = left_line
        self._right_line = right_line
    
    def _apply_theme(self, theme=None):
        """应用主题"""
        tm = self._theme_manager
        colors = tm.colors
        
        if self._dashed:
            style = f"border: none; border-top: 1px dashed {colors['divider']};"
        else:
            style = f"border: none; border-top: 1px solid {colors['divider']};"
        
        if self._thick:
            style = style.replace("1px", "2px")
        
        self.setStyleSheet(style)
        
        if hasattr(self, '_text_label'):
            self._text_label.setStyleSheet(f"color: {colors['divider_text']}; background: transparent;")
            self._left_line.setStyleSheet(f"background-color: {colors['divider']}; border: none;")
            self._right_line.setStyleSheet(f"background-color: {colors['divider']}; border: none;")
    
    def set_text(self, text: str):
        """设置文字"""
        self._text = text
        if hasattr(self, '_text_label'):
            self._text_label.setText(text)


class Badge(QLabel):
    """徽标/标签 - 用于显示计数、状态、标签"""
    
    def __init__(self, parent: QWidget = None, text: str = "",
                 badge_type: Literal["default", "success", "warning", "error", "info"] = "default",
                 dot: bool = False, count: int = 0, max_count: int = 99,
                 show_zero: bool = False, size: str = "md"):
        super().__init__(parent)
        self._theme_manager = get_theme_manager()
        
        self._badge_type = badge_type
        self._dot = dot
        self._count = count
        self._max_count = max_count
        self._show_zero = show_zero
        self._size = size  # sm, md, lg
        
        self.setObjectName("Badge")
        self.setProperty("badge", True)
        self.setProperty("type", badge_type)
        
        # 尺寸配置
        sizes = {
            "sm": {"height": 16, "padding": "0 6px", "font_size": "10px", "min_width": 16},
            "md": {"height": 20, "padding": "0 8px", "font_size": "11px", "min_width": 20},
            "lg": {"height": 24, "padding": "0 10px", "font_size": "12px", "min_width": 24},
        }
        self._size_config = sizes.get(size, sizes["md"])
        
        self.setText(text)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self._setup_ui()
        self._apply_theme()
        self._theme_manager.theme_changed.connect(self._apply_theme)
    
    def _setup_ui(self):
        """设置 UI"""
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(int(self._size_config["font_size"].replace("px", "")))
        font.setWeight(QFont.Weight.Medium)
        self.setFont(font)
        
        self.setFixedHeight(self._size_config["height"])
        self.setMinimumWidth(self._size_config["min_width"])
        
        if self._dot:
            self.setText("●")
            font.setPointSize(int(self._size_config["font_size"].replace("px", "")) + 2)
            self.setFont(font)
        
        self._update_count_display()
    
    def _update_count_display(self):
        """更新计数显示"""
        if self._count > 0:
            if self._count > self._max_count:
                self.setText(f"{self._max_count}+")
            else:
                self.setText(str(self._count))
        elif self._show_zero:
            self.setText("0")
        elif not self._dot:
            self.setText("")
    
    def _apply_theme(self, theme=None):
        """应用主题"""
        tm = self._theme_manager
        colors = tm.colors
        
        type_colors = {
            "default": (colors["badge_bg"], colors["badge_text"]),
            "success": (colors["success"], colors["badge_text"]),
            "warning": (colors["warning"], colors["badge_text"]),
            "error": (colors["error"], colors["badge_text"]),
            "info": (colors["info"], colors["badge_text"]),
        }
        
        bg_color, text_color = type_colors.get(self._badge_type, type_colors["default"])
        
        self.setStyleSheet(f"""
            QLabel[badge="true"] {{
                background-color: {bg_color};
                color: {text_color};
                border-radius: {self._size_config['height'] // 2}px;
                padding: {self._size_config['padding']};
                min-width: {self._size_config['min_width']}px;
                font-family: {colors['font_family']};
                font-size: {self._size_config['font_size']};
                font-weight: 500;
            }}
        """)
        
        if self._dot:
            # 点模式：小圆点
            self.setStyleSheet(f"""
                QLabel[badge="true"] {{
                    color: {bg_color};
                    font-size: {self._size_config['font_size']};
                }}
            """)
    
    def set_type(self, badge_type: str):
        """设置类型"""
        self._badge_type = badge_type
        self.setProperty("type", badge_type)
        self._apply_theme()
    
    def set_count(self, count: int):
        """设置计数"""
        self._count = max(0, count)
        self._update_count_display()
    
    def increment(self, step: int = 1):
        """增加计数"""
        self.set_count(self._count + step)
    
    def decrement(self, step: int = 1):
        """减少计数"""
        self.set_count(self._count - step)
    
    def set_text(self, text: str):
        """设置文本（非计数模式）"""
        self._dot = False
        self.setText(text)
    
    def set_dot(self, dot: bool):
        """设置点模式"""
        self._dot = dot
        if dot:
            self.setText("●")
        else:
            self._update_count_display()


class Tooltip(QWidget):
    """自定义 Tooltip - 支持富文本、箭头、动画"""
    
    def __init__(self, parent: QWidget = None, text: str = "",
                 position: Literal["top", "bottom", "left", "right"] = "top",
                 offset: int = 8, show_arrow: bool = True,
                 max_width: int = 280, hide_delay: int = 200):
        super().__init__(parent, Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self._theme_manager = get_theme_manager()
        
        self._text = text
        self._position = position
        self._offset = offset
        self._show_arrow = show_arrow
        self._max_width = max_width
        self._hide_delay = hide_delay
        
        self._target_widget = None
        self._visible = False
        
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        
        # 隐藏定时器
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)
        
        # 显示动画
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)
        
        self._show_animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._show_animation.setDuration(150)
        self._show_animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
        self._hide_animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._hide_animation.setDuration(150)
        self._hide_animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self._hide_animation.finished.connect(self._on_hide_finished)
        
        self._setup_ui()
        self._apply_theme()
        self._theme_manager.theme_changed.connect(self._apply_theme)
    
    def _setup_ui(self):
        """设置 UI"""
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        
        # 内容容器
        self._content = QFrame()
        self._content.setObjectName("TooltipContent")
        content_layout = QVBoxLayout(self._content)
        content_layout.setContentsMargins(10, 8, 10, 8)
        
        self._label = QLabel(self._text)
        self._label.setWordWrap(True)
        self._label.setMaximumWidth(self._max_width)
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(int(self._theme_manager.get_color("font_sm").replace("px", "")))
        self._label.setFont(font)
        content_layout.addWidget(self._label)
        
        self._layout.addWidget(self._content)
    
    def _apply_theme(self, theme=None):
        """应用主题"""
        tm = self._theme_manager
        colors = tm.colors
        
        self._content.setStyleSheet(f"""
            QFrame#TooltipContent {{
                background-color: {colors["tooltip_bg"]};
                color: {colors["tooltip_text"]};
                border-radius: {colors["radius_sm"]};
            }}
            QLabel {{
                color: {colors["tooltip_text"]};
                background: transparent;
            }}
        """)
    
    def show_at(self, target: QWidget, pos: QPoint = None):
        """在目标控件位置显示"""
        self._target_widget = target
        
        if pos is None:
            # 计算位置
            target_rect = target.rect()
            global_pos = target.mapToGlobal(target_rect.center())
            
            # 根据位置调整
            self.adjustSize()
            tooltip_size = self.sizeHint()
            
            x, y = global_pos.x(), global_pos.y()
            
            if self._position == "top":
                x -= tooltip_size.width() // 2
                y -= tooltip_size.height() + self._offset
            elif self._position == "bottom":
                x -= tooltip_size.width() // 2
                y += self._offset
            elif self._position == "left":
                x -= tooltip_size.width() + self._offset
                y -= tooltip_size.height() // 2
            elif self._position == "right":
                x += self._offset
                y -= tooltip_size.height() // 2
            
            self.move(x, y)
        else:
            self.move(pos)
        
        self._show_animate()
    
    def _show_animate(self):
        """显示动画"""
        self.show()
        self.raise_()
        
        self._show_animation.stop()
        self._show_animation.setStartValue(0.0)
        self._show_animation.setEndValue(1.0)
        self._show_animation.start()
        
        self._visible = True
        self._hide_timer.stop()
    
    def hide_animate(self):
        """隐藏动画"""
        self._hide_timer.start(self._hide_delay)
    
    def _on_hide_finished(self):
        """隐藏动画完成"""
        self.hide()
        self._visible = False
    
    def enterEvent(self, event):
        """鼠标进入 - 取消隐藏"""
        self._hide_timer.stop()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开 - 开始隐藏"""
        self.hide_animate()
        super().leaveEvent(event)
    
    def set_text(self, text: str):
        """设置文本"""
        self._text = text
        self._label.setText(text)
    
    @classmethod
    def show_for_widget(cls, widget: QWidget, text: str, 
                        position: str = "top", **kwargs) -> "Tooltip":
        """为控件显示 tooltip（静态方法）"""
        tooltip = cls(widget, text, position, **kwargs)
        tooltip.show_at(widget)
        return tooltip


class Avatar(QWidget):
    """头像组件 - 支持图片、文字、状态指示"""
    
    def __init__(self, parent: QWidget = None, text: str = "", 
                 image: QPixmap = None, size: str = "md",
                 shape: Literal["circle", "square"] = "circle",
                 status: Literal["online", "offline", "busy", "away"] = None):
        super().__init__(parent)
        self._theme_manager = get_theme_manager()
        
        self._text = text
        self._image = image
        self._size = size  # xs, sm, md, lg, xl
        self._shape = shape
        self._status = status
        
        # 尺寸配置
        sizes = {
            "xs": 24, "sm": 32, "md": 40, "lg": 48, "xl": 56
        }
        self._diameter = sizes.get(size, 40)
        
        self.setFixedSize(self._diameter, self._diameter)
        
        self._apply_theme()
        self._theme_manager.theme_changed.connect(self._apply_theme)
    
    def _apply_theme(self, theme=None):
        self.update()
    
    def paintEvent(self, event):
        """绘制头像"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        colors = self._theme_manager.colors
        rect = self.rect()
        
        # 背景
        if self._shape == "circle":
            path = QPainterPath()
            path.addEllipse(rect)
            painter.setClipPath(path)
        
        if self._image and not self._image.isNull():
            # 绘制图片
            scaled = self._image.scaled(self._diameter, self._diameter,
                                        Qt.AspectRatioMode.KeepAspectRatioByExpanding,
                                        Qt.TransformationMode.SmoothTransformation)
            # 居中裁剪
            x = (scaled.width() - self._diameter) // 2
            y = (scaled.height() - self._diameter) // 2
            painter.drawPixmap(0, 0, scaled, x, y, self._diameter, self._diameter)
        else:
            # 绘制背景色 + 文字
            # 根据文字生成一致的颜色
            hash_val = hash(self._text) if self._text else 0
            hue = (hash_val * 137) % 360
            bg_color = QColor.fromHsv(hue, 60, 85)
            
            painter.fillRect(rect, bg_color)
            
            if self._text:
                # 取首字母
                display_text = self._text.strip()[:2].upper()
                painter.setPen(QColor(colors["primary_text"]))
                font = QFont(colors["font_family"])
                font.setPointSize(self._diameter // 2)
                font.setWeight(QFont.Weight.Medium)
                painter.setFont(font)
                painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, display_text)
        
        # 状态指示点
        if self._status:
            status_colors = {
                "online": colors["success"],
                "offline": colors["text_tertiary"],
                "busy": colors["error"],
                "away": colors["warning"],
            }
            status_color = status_colors.get(self._status, colors["text_tertiary"])
            
            dot_size = max(8, self._diameter // 5)
            dot_rect = QRect(
                self._diameter - dot_size - 2,
                self._diameter - dot_size - 2,
                dot_size, dot_size
            )
            
            painter.setBrush(QBrush(status_color))
            painter.setPen(QPen(colors["card_bg"], 2))
            painter.drawEllipse(dot_rect)
    
    def set_text(self, text: str):
        self._text = text
        self.update()
    
    def set_image(self, image: QPixmap):
        self._image = image
        self.update()
    
    def set_status(self, status: str):
        self._status = status
        self.update()


class Skeleton(QWidget):
    """骨架屏 - 加载占位动画"""
    
    def __init__(self, parent: QWidget = None, lines: int = 3,
                 width: int = 0, height: int = 16, radius: int = 4,
                 animated: bool = True):
        super().__init__(parent)
        self._theme_manager = get_theme_manager()
        
        self._lines = lines
        self._width = width
        self._height = height
        self._radius = radius
        self._animated = animated
        
        self._animation = None
        self._phase = 0
        
        self._setup_ui()
        self._apply_theme()
        self._theme_manager.theme_changed.connect(self._apply_theme)
        
        if animated:
            self._start_animation()
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        self._line_widgets = []
        for i in range(self._lines):
            line = QWidget()
            line.setFixedHeight(self._height)
            if self._width > 0:
                line.setFixedWidth(self._width)
            layout.addWidget(line)
            self._line_widgets.append(line)
        
        layout.addStretch()
    
    def _apply_theme(self, theme=None):
        tm = self._theme_manager
        colors = tm.colors
        
        base_color = colors["border_secondary"]
        highlight_color = colors["border_primary"]
        
        for widget in self._line_widgets:
            widget.setStyleSheet(f"""
                QWidget {{
                    background-color: {base_color};
                    border-radius: {self._radius}px;
                }}
            """)
    
    def _start_animation(self):
        """启动闪烁动画"""
        self._animation = QPropertyAnimation(self, b"_phase")
        self._animation.setDuration(1500)
        self._animation.setStartValue(0)
        self._animation.setEndValue(100)
        self._animation.setLoopCount(-1)
        self._animation.valueChanged.connect(self._on_phase_changed)
        self._animation.start()
    
    def _on_phase_changed(self, value):
        """动画相位变化"""
        self._phase = value
        self.update()
    
    def paintEvent(self, event):
        """绘制闪烁效果"""
        if not self._animated:
            return
        
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        colors = self._theme_manager.colors
        base_color = QColor(colors["border_secondary"])
        highlight_color = QColor(colors["border_primary"])
        
        # 计算渐变位置
        progress = (self._phase % 100) / 100.0
        
        for i, widget in enumerate(self._line_widgets):
            rect = widget.rect()
            # 错开每行的动画
            line_progress = (progress + i * 0.15) % 1.0
            
            # 创建线性渐变
            from PySide6.QtGui import QLinearGradient
            gradient = QLinearGradient(rect.topLeft(), rect.topRight())
            gradient.setColorAt(0, base_color)
            
            # 高亮位置
            highlight_pos = line_progress
            gradient.setColorAt(max(0, highlight_pos - 0.3), base_color)
            gradient.setColorAt(highlight_pos, highlight_color)
            gradient.setColorAt(min(1, highlight_pos + 0.3), base_color)
            gradient.setColorAt(1, base_color)
            
            painter.fillRect(rect, gradient)


class EmptyState(QWidget):
    """空状态组件 - 图标、标题、描述、操作按钮"""
    
    action_clicked = Signal()
    
    def __init__(self, parent: QWidget = None, icon: str = "📭",
                 title: str = "暂无数据", description: str = "",
                 action_text: str = "", action_callback: Callable = None):
        super().__init__(parent)
        self._theme_manager = get_theme_manager()
        
        self._icon = icon
        self._title = title
        self._description = description
        self._action_text = action_text
        self._action_callback = action_callback
        
        self._setup_ui()
        self._apply_theme()
        self._theme_manager.theme_changed.connect(self._apply_theme)
    
    def _setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 32, 24, 32)
        layout.setSpacing(16)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # 图标
        self._icon_label = QLabel(self._icon)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(64)
        self._icon_label.setFont(font)
        layout.addWidget(self._icon_label)
        
        # 标题
        self._title_label = QLabel(self._title)
        self._title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(int(self._theme_manager.get_color("font_xl").replace("px", "")))
        font.setWeight(QFont.Weight.Medium)
        self._title_label.setFont(font)
        layout.addWidget(self._title_label)
        
        # 描述
        if self._description:
            self._desc_label = QLabel(self._description)
            self._desc_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self._desc_label.setWordWrap(True)
            font = QFont(self._theme_manager.get_color("font_family"))
            font.setPointSize(int(self._theme_manager.get_color("font_md").replace("px", "")))
            self._desc_label.setFont(font)
            layout.addWidget(self._desc_label)
        
        # 操作按钮
        if self._action_text:
            self._action_btn = PrimaryButton(self._action_text)
            self._action_btn.setFixedWidth(160)
            self._action_btn.clicked.connect(self._on_action_clicked)
            layout.addWidget(self._action_btn, 0, Qt.AlignmentFlag.AlignCenter)
    
    def _apply_theme(self, theme=None):
        tm = self._theme_manager
        colors = tm.colors
        
        self._title_label.setStyleSheet(f"color: {colors['text_primary']};")
        if hasattr(self, '_desc_label'):
            self._desc_label.setStyleSheet(f"color: {colors['text_secondary']};")
    
    def _on_action_clicked(self):
        self.action_clicked.emit()
        if self._action_callback:
            self._action_callback()


# 导入 typing.Callable
from typing import Callable