"""
Notification Components - Toast, Notification, ToastContainer
"""

from typing import Optional, List, Literal
from enum import Enum
from PySide6.QtCore import (Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve, 
                            QRect, QPoint, QSize, QParallelAnimationGroup, QSequentialAnimationGroup)
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
                               QPushButton, QApplication, QGraphicsOpacityEffect)
from PySide6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QBrush, QPen, QPainterPath

from .theme import get_theme_manager, ThemeManager, COMPONENT_QSS_TEMPLATES
from .buttons import IconButton


class ToastType(Enum):
    """Toast 类型"""
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    DEFAULT = "default"


class ToastPosition(Enum):
    """Toast 位置"""
    TOP_LEFT = "top-left"
    TOP_RIGHT = "top-right"
    BOTTOM_LEFT = "bottom-left"
    BOTTOM_RIGHT = "bottom-right"
    TOP_CENTER = "top-center"
    BOTTOM_CENTER = "bottom-center"


class Toast(QFrame):
    """Toast 消息提示 - 自动消失、可点击关闭"""
    
    closed = Signal()  # 关闭信号
    clicked = Signal()  # 点击信号
    
    def __init__(self, parent: QWidget = None, message: str = "", 
                 toast_type: ToastType = ToastType.INFO,
                 duration: int = 3000, closable: bool = True,
                 icon: QIcon = None, action_text: str = None,
                 action_callback=None):
        super().__init__(parent)
        self._theme_manager = get_theme_manager()
        
        self._message = message
        self._toast_type = toast_type
        self._duration = duration
        self._closable = closable
        self._icon = icon
        self._action_text = action_text
        self._action_callback = action_callback
        
        self._timer = QTimer(self)
        self._timer.setSingleShot(True)
        self._timer.timeout.connect(self.close_animate)
        
        self._animation = None
        self._opacity_effect = None
        
        self._setup_ui()
        self._apply_theme()
        self._theme_manager.theme_changed.connect(self._apply_theme)
    
    def _setup_ui(self):
        """设置 UI"""
        self.setObjectName("Toast")
        self.setProperty("toast", True)
        self.setProperty("type", self._toast_type.value)
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | 
                           Qt.WindowType.Tool | 
                           Qt.WindowType.WindowStaysOnTopHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        # 布局
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(16, 12, 16, 12)
        self._layout.setSpacing(12)
        
        # 图标
        self._icon_label = QLabel()
        self._icon_label.setFixedSize(20, 20)
        self._icon_label.setScaledContents(True)
        self._layout.addWidget(self._icon_label)
        
        # 消息文本
        self._message_label = QLabel(self._message)
        self._message_label.setWordWrap(True)
        self._message_label.setMaximumWidth(350)
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(int(self._theme_manager.get_color("font_md").replace("px", "")))
        self._message_label.setFont(font)
        self._layout.addWidget(self._message_label, 1)
        
        # 操作按钮
        if self._action_text:
            self._action_btn = QPushButton(self._action_text)
            self._action_btn.setCursor(Qt.CursorShape.PointingHandCursor)
            self._action_btn.clicked.connect(self._on_action_clicked)
            self._layout.addWidget(self._action_btn)
        
        # 关闭按钮
        if self._closable:
            self._close_btn = IconButton(tooltip="关闭", size=24)
            self._close_btn.setText("✕")
            font = QFont(self._theme_manager.get_color("font_family"))
            font.setPointSize(14)
            font.setWeight(QFont.Weight.Bold)
            self._close_btn.setFont(font)
            self._close_btn.clicked.connect(self.close_animate)
            self._layout.addWidget(self._close_btn)
        
        # 设置类型图标
        self._set_type_icon()
        
        # 透明度效果
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(0.0)
        self.setGraphicsEffect(self._opacity_effect)
    
    def _set_type_icon(self):
        """设置类型图标"""
        colors = self._theme_manager.colors
        
        # 根据类型设置图标和颜色
        if self._toast_type == ToastType.SUCCESS:
            self._icon_label.setText("✓")
            self.setProperty("type", "success")
        elif self._toast_type == ToastType.ERROR:
            self._icon_label.setText("✕")
            self.setProperty("type", "error")
        elif self._toast_type == ToastType.WARNING:
            self._icon_label.setText("⚠")
            self.setProperty("type", "warning")
        elif self._toast_type == ToastType.INFO:
            self._icon_label.setText("ℹ")
            self.setProperty("type", "info")
        else:
            self._icon_label.setText("•")
            self.setProperty("type", "default")
        
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(16)
        font.setWeight(QFont.Weight.Bold)
        self._icon_label.setFont(font)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    def _apply_theme(self, theme=None):
        """应用主题"""
        tm = self._theme_manager
        qss = tm.get_qss(COMPONENT_QSS_TEMPLATES["toast"])
        self.setStyleSheet(qss)
        
        # 重新应用类型属性
        self.setProperty("type", self._toast_type.value)
        self.style().unpolish(self)
        self.style().polish(self)
    
    def show_animate(self):
        """显示动画"""
        self.show()
        self.raise_()
        
        # 渐入动画
        self._animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._animation.setDuration(200)
        self._animation.setStartValue(0.0)
        self._animation.setEndValue(1.0)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.start()
        
        # 启动自动关闭定时器
        if self._duration > 0:
            self._timer.start(self._duration)
    
    def close_animate(self):
        """关闭动画"""
        if self._timer.isActive():
            self._timer.stop()
        
        # 渐出动画
        self._animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._animation.setDuration(200)
        self._animation.setStartValue(self._opacity_effect.opacity())
        self._animation.setEndValue(0.0)
        self._animation.setEasingCurve(QEasingCurve.Type.InCubic)
        self._animation.finished.connect(self._on_close_finished)
        self._animation.start()
    
    def _on_close_finished(self):
        """关闭动画完成"""
        self.closed.emit()
        self.deleteLater()
    
    def _on_action_clicked(self):
        """操作按钮点击"""
        if self._action_callback:
            self._action_callback()
        self.close_animate()
    
    def mousePressEvent(self, event):
        """鼠标点击"""
        self.clicked.emit()
        super().mousePressEvent(event)
    
    def enterEvent(self, event):
        """鼠标进入 - 暂停定时器"""
        if self._timer.isActive():
            self._timer.stop()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        """鼠标离开 - 恢复定时器"""
        if self._duration > 0:
            self._timer.start(self._duration)
        super().leaveEvent(event)
    
    @classmethod
    def show_message(cls, parent: QWidget, message: str, 
                     toast_type: ToastType = ToastType.INFO,
                     duration: int = 3000, position: ToastPosition = ToastPosition.TOP_RIGHT,
                     **kwargs) -> "Toast":
        """静态方法：快速显示消息"""
        toast = cls(parent, message, toast_type, duration, **kwargs)
        container = ToastContainer.get_instance(parent, position)
        container.add_toast(toast)
        toast.show_animate()
        return toast
    
    @classmethod
    def success(cls, parent: QWidget, message: str, **kwargs) -> "Toast":
        return cls.show_message(parent, message, ToastType.SUCCESS, **kwargs)
    
    @classmethod
    def error(cls, parent: QWidget, message: str, **kwargs) -> "Toast":
        return cls.show_message(parent, message, ToastType.ERROR, **kwargs)
    
    @classmethod
    def warning(cls, parent: QWidget, message: str, **kwargs) -> "Toast":
        return cls.show_message(parent, message, ToastType.WARNING, **kwargs)
    
    @classmethod
    def info(cls, parent: QWidget, message: str, **kwargs) -> "Toast":
        return cls.show_message(parent, message, ToastType.INFO, **kwargs)


class ToastContainer(QWidget):
    """Toast 容器 - 管理多个 Toast 的堆叠显示"""
    
    _instances = {}  # 位置 -> 实例
    
    def __init__(self, parent: QWidget = None, position: ToastPosition = ToastPosition.TOP_RIGHT):
        super().__init__(parent)
        self._theme_manager = get_theme_manager()
        self._position = position
        self._toasts: List[Toast] = []
        self._spacing = 8
        self._padding = 16
        
        self._setup_ui()
        self._apply_theme()
        self._theme_manager.theme_changed.connect(self._apply_theme)
    
    @classmethod
    def get_instance(cls, parent: QWidget, position: ToastPosition) -> "ToastContainer":
        """获取或创建容器实例（单例模式，按位置）"""
        key = (parent, position)
        if key not in cls._instances:
            cls._instances[key] = cls(parent, position)
        return cls._instances[key]
    
    def _setup_ui(self):
        """设置 UI"""
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | 
                           Qt.WindowType.Tool | 
                           Qt.WindowType.WindowStaysOnTopHint)
        
        # 布局方向根据位置决定
        if self._position in [ToastPosition.TOP_LEFT, ToastPosition.TOP_RIGHT, ToastPosition.TOP_CENTER]:
            self._layout = QVBoxLayout(self)
            self._layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        else:
            self._layout = QVBoxLayout(self)
            self._layout.setAlignment(Qt.AlignmentFlag.AlignBottom)
        
        self._layout.setContentsMargins(self._padding, self._padding, self._padding, self._padding)
        self._layout.setSpacing(self._spacing)
    
    def _apply_theme(self, theme=None):
        """应用主题"""
        # 容器本身透明
        self.setStyleSheet("background: transparent;")
    
    def add_toast(self, toast: Toast):
        """添加 Toast"""
        self._toasts.append(toast)
        self._layout.addWidget(toast)
        self._reposition()
        toast.closed.connect(lambda: self._on_toast_closed(toast))
    
    def _on_toast_closed(self, toast: Toast):
        """Toast 关闭回调"""
        if toast in self._toasts:
            self._toasts.remove(toast)
        self._reposition()
    
    def _reposition(self):
        """重新定位容器"""
        if not self.parentWidget():
            return
        
        parent_rect = self.parentWidget().rect()
        container_size = self.sizeHint()
        
        x, y = 0, 0
        
        if self._position == ToastPosition.TOP_RIGHT:
            x = parent_rect.width() - container_size.width() - self._padding
            y = self._padding
        elif self._position == ToastPosition.TOP_LEFT:
            x = self._padding
            y = self._padding
        elif self._position == ToastPosition.TOP_CENTER:
            x = (parent_rect.width() - container_size.width()) // 2
            y = self._padding
        elif self._position == ToastPosition.BOTTOM_RIGHT:
            x = parent_rect.width() - container_size.width() - self._padding
            y = parent_rect.height() - container_size.height() - self._padding
        elif self._position == ToastPosition.BOTTOM_LEFT:
            x = self._padding
            y = parent_rect.height() - container_size.height() - self._padding
        elif self._position == ToastPosition.BOTTOM_CENTER:
            x = (parent_rect.width() - container_size.width()) // 2
            y = parent_rect.height() - container_size.height() - self._padding
        
        self.move(x, y)
        self.resize(container_size)
    
    def resizeEvent(self, event):
        """父窗口大小变化时重新定位"""
        super().resizeEvent(event)
        QTimer.singleShot(0, self._reposition)
    
    def showEvent(self, event):
        """显示时定位"""
        super().showEvent(event)
        self._reposition()
    
    def clear(self):
        """清空所有 Toast"""
        for toast in self._toasts[:]:
            toast.close_animate()
        self._toasts.clear()


class Notification(QFrame):
    """通知面板 - 不自动消失、可包含更多内容、支持操作"""
    
    closed = Signal()
    action_clicked = Signal(str)  # action_id
    
    def __init__(self, parent: QWidget = None, title: str = "", message: str = "",
                 notification_type: ToastType = ToastType.INFO,
                 closable: bool = True, actions: List[dict] = None,
                 icon: QIcon = None):
        super().__init__(parent)
        self._theme_manager = get_theme_manager()
        
        self._title = title
        self._message = message
        self._notification_type = notification_type
        self._closable = closable
        self._actions = actions or []
        self._icon = icon
        
        self._setup_ui()
        self._apply_theme()
        self._theme_manager.theme_changed.connect(self._apply_theme)
    
    def _setup_ui(self):
        """设置 UI"""
        self.setObjectName("Notification")
        self.setProperty("toast", True)
        self.setProperty("type", self._notification_type.value)
        
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | 
                           Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        
        # 主布局
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(16, 16, 16, 16)
        self._layout.setSpacing(12)
        
        # 头部：标题 + 关闭按钮
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        # 图标
        self._icon_label = QLabel()
        self._icon_label.setFixedSize(24, 24)
        self._icon_label.setScaledContents(True)
        header_layout.addWidget(self._icon_label)
        
        # 标题
        if self._title:
            self._title_label = QLabel(self._title)
            font = QFont(self._theme_manager.get_color("font_family"))
            font.setPointSize(int(self._theme_manager.get_color("font_md").replace("px", "")))
            font.setWeight(QFont.Weight.SemiBold)
            self._title_label.setFont(font)
            header_layout.addWidget(self._title_label)
        
        header_layout.addStretch()
        
        # 关闭按钮
        if self._closable:
            self._close_btn = IconButton(tooltip="关闭", size=24)
            self._close_btn.setText("✕")
            font = QFont(self._theme_manager.get_color("font_family"))
            font.setPointSize(14)
            font.setWeight(QFont.Weight.Bold)
            self._close_btn.setFont(font)
            self._close_btn.clicked.connect(self.close)
            header_layout.addWidget(self._close_btn)
        
        self._layout.addLayout(header_layout)
        
        # 消息内容
        if self._message:
            self._message_label = QLabel(self._message)
            self._message_label.setWordWrap(True)
            font = QFont(self._theme_manager.get_color("font_family"))
            font.setPointSize(int(self._theme_manager.get_color("font_sm").replace("px", "")))
            self._message_label.setFont(font)
            self._layout.addWidget(self._message_label)
        
        # 操作按钮
        if self._actions:
            actions_layout = QHBoxLayout()
            actions_layout.setSpacing(8)
            actions_layout.addStretch()
            
            for action in self._actions:
                btn = QPushButton(action.get("text", "Action"))
                btn.setCursor(Qt.CursorShape.PointingHandCursor)
                btn.setProperty("actionId", action.get("id", ""))
                btn.clicked.connect(lambda checked, aid=action.get("id"): self._on_action_clicked(aid))
                actions_layout.addWidget(btn)
            
            self._layout.addLayout(actions_layout)
        
        # 设置类型图标
        self._set_type_icon()
    
    def _set_type_icon(self):
        """设置类型图标"""
        if self._notification_type == ToastType.SUCCESS:
            self._icon_label.setText("✓")
            self.setProperty("type", "success")
        elif self._notification_type == ToastType.ERROR:
            self._icon_label.setText("✕")
            self.setProperty("type", "error")
        elif self._notification_type == ToastType.WARNING:
            self._icon_label.setText("⚠")
            self.setProperty("type", "warning")
        elif self._notification_type == ToastType.INFO:
            self._icon_label.setText("ℹ")
            self.setProperty("type", "info")
        else:
            self._icon_label.setText("•")
            self.setProperty("type", "default")
        
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(18)
        font.setWeight(QFont.Weight.Bold)
        self._icon_label.setFont(font)
        self._icon_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
    
    def _apply_theme(self, theme=None):
        """应用主题"""
        tm = self._theme_manager
        qss = tm.get_qss(COMPONENT_QSS_TEMPLATES["toast"])
        self.setStyleSheet(qss)
        
        self.setProperty("type", self._notification_type.value)
        self.style().unpolish(self)
        self.style().polish(self)
    
    def _on_action_clicked(self, action_id: str):
        """操作按钮点击"""
        self.action_clicked.emit(action_id)
        # 如果动作指定了关闭，则关闭
        for action in self._actions:
            if action.get("id") == action_id and action.get("close_on_click", True):
                self.close()
                break
    
    def closeEvent(self, event):
        """关闭事件"""
        self.closed.emit()
        super().closeEvent(event)


class NotificationPanel(QWidget):
    """通知面板 - 侧边栏式通知中心"""
    
    def __init__(self, parent: QWidget = None, position: str = "right"):
        super().__init__(parent)
        self._theme_manager = get_theme_manager()
        self._position = position  # "left" or "right"
        self._notifications: List[Notification] = []
        
        self._setup_ui()
        self._apply_theme()
        self._theme_manager.theme_changed.connect(self._apply_theme)
        
        # 默认隐藏
        self.hide()
    
    def _setup_ui(self):
        """设置 UI"""
        self.setObjectName("NotificationPanel")
        self.setFixedWidth(360)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 头部
        header = QWidget()
        header.setObjectName("NotificationPanelHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(16, 12, 16, 12)
        
        title_label = QLabel("通知中心")
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(int(self._theme_manager.get_color("font_lg").replace("px", "")))
        font.setWeight(QFont.Weight.SemiBold)
        title_label.setFont(font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        clear_btn = QPushButton("清空")
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.clicked.connect(self.clear_all)
        header_layout.addWidget(clear_btn)
        
        layout.addWidget(header)
        
        # 分割线
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFixedHeight(1)
        layout.addWidget(divider)
        
        # 列表区域
        from PySide6.QtWidgets import QScrollArea
        self._scroll = QScrollArea()
        self._scroll.setWidgetResizable(True)
        self._scroll.setFrameShape(QFrame.Shape.NoFrame)
        self._scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self._list_widget = QWidget()
        self._list_layout = QVBoxLayout(self._list_widget)
        self._list_layout.setContentsMargins(12, 12, 12, 12)
        self._list_layout.setSpacing(8)
        self._list_layout.addStretch()
        
        self._scroll.setWidget(self._list_widget)
        layout.addWidget(self._scroll, 1)
        
        # 空状态
        self._empty_label = QLabel("暂无通知")
        self._empty_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(int(self._theme_manager.get_color("font_md").replace("px", "")))
        self._empty_label.setFont(font)
        self._list_layout.insertWidget(0, self._empty_label)
        self._empty_label.show()
    
    def _apply_theme(self, theme=None):
        """应用主题"""
        tm = self._theme_manager
        colors = tm.colors
        
        self.setStyleSheet(f"""
            QWidget#NotificationPanel {{
                background-color: {colors["sidebar_bg"]};
                border-left: 1px solid {colors["sidebar_border"]};
            }}
            QWidget#NotificationPanelHeader {{
                background-color: transparent;
            }}
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QWidget {{
                background: transparent;
            }}
        """)
        
        self._empty_label.setStyleSheet(f"color: {colors['text_tertiary']};")
    
    def add_notification(self, notification: Notification):
        """添加通知"""
        self._notifications.insert(0, notification)
        self._list_layout.insertWidget(0, notification)
        self._empty_label.hide()
        
        notification.closed.connect(lambda: self._on_notification_closed(notification))
        notification.action_clicked.connect(self._on_action_clicked)
    
    def _on_notification_closed(self, notification: Notification):
        """通知关闭"""
        if notification in self._notifications:
            self._notifications.remove(notification)
        notification.deleteLater()
        
        if not self._notifications:
            self._empty_label.show()
    
    def _on_action_clicked(self, action_id: str):
        """操作点击"""
        # 可以在这里处理全局操作
        pass
    
    def clear_all(self):
        """清空所有通知"""
        for notification in self._notifications[:]:
            notification.close()
    
    def show_panel(self):
        """显示面板"""
        self._reposition()
        self.show()
        self.raise_()
    
    def hide_panel(self):
        """隐藏面板"""
        self.hide()
    
    def toggle_panel(self):
        """切换面板显示"""
        if self.isVisible():
            self.hide_panel()
        else:
            self.show_panel()
    
    def _reposition(self):
        """重新定位"""
        if not self.parentWidget():
            return
        
        parent_rect = self.parentWidget().rect()
        x = parent_rect.width() - self.width() if self._position == "right" else 0
        y = 0
        self.move(x, y)
        self.setFixedHeight(parent_rect.height())


def show_toast(parent: QWidget, message: str, 
               toast_type: ToastType = ToastType.INFO,
               duration: int = 3000, position: ToastPosition = ToastPosition.TOP_RIGHT,
               **kwargs) -> Toast:
    """便捷函数：显示 Toast"""
    return Toast.show_message(parent, message, toast_type, duration, position, **kwargs)


def show_notification(parent: QWidget, title: str, message: str,
                      notification_type: ToastType = ToastType.INFO,
                      actions: List[dict] = None, **kwargs) -> Notification:
    """便捷函数：显示通知"""
    notification = Notification(parent, title, message, notification_type, actions=actions, **kwargs)
    notification.show()
    return notification