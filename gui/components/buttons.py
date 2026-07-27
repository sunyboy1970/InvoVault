"""
Button Components - PrimaryButton, SecondaryButton, IconButton
"""

from typing import Optional
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtWidgets import QPushButton, QWidget, QHBoxLayout, QLabel
from PySide6.QtGui import QIcon, QFont, QCursor

from .theme import get_theme_manager, ThemeManager, COMPONENT_QSS_TEMPLATES


class BaseButton(QPushButton):
    """基础按钮类 - 统一主题管理"""
    
    def __init__(self, text: str = "", parent: QWidget = None, qss_template: str = ""):
        super().__init__(text, parent)
        self._theme_manager = get_theme_manager()
        self._qss_template = qss_template
        self._apply_theme()
        
        # 连接主题变化信号
        self._theme_manager.theme_changed.connect(self._apply_theme)
        
        # 设置光标
        self.setCursor(QCursor(Qt.CursorShape.PointingHandCursor))
        self.setFont(QFont(self._theme_manager.get_color("font_family"), 
                          int(self._theme_manager.get_color("font_md").replace("px", ""))))
    
    def _apply_theme(self, theme=None):
        """应用主题样式"""
        if self._qss_template:
            qss = self._theme_manager.get_qss(self._qss_template)
            self.setStyleSheet(qss)
    
    def set_theme_template(self, template: str):
        """设置 QSS 模板"""
        self._qss_template = template
        self._apply_theme()


class PrimaryButton(BaseButton):
    """主按钮 - 主色调 #1890FF，白色文字，圆角"""
    
    def __init__(self, text: str = "", parent: QWidget = None, 
                 loading: bool = False, icon: QIcon = None):
        super().__init__(text, parent, COMPONENT_QSS_TEMPLATES["button_primary"])
        self._loading = loading
        self._original_text = text
        self._icon = icon
        
        if icon:
            self.setIcon(icon)
            self.setIconSize(QSize(18, 18))
        
        self.setMinimumHeight(40)
        self.setMinimumWidth(88)
    
    @property
    def loading(self) -> bool:
        return self._loading
    
    @loading.setter
    def loading(self, value: bool):
        self._loading = value
        if value:
            self._original_text = self.text()
            self.setText("")
            self.setEnabled(False)
            # TODO: 添加 loading spinner
        else:
            self.setText(self._original_text)
            self.setEnabled(True)
            if self._icon:
                self.setIcon(self._icon)
                self.setIconSize(QSize(18, 18))


class SecondaryButton(BaseButton):
    """次要按钮 - 白底蓝框蓝字，圆角"""
    
    def __init__(self, text: str = "", parent: QWidget = None, 
                 icon: QIcon = None, danger: bool = False):
        template = COMPONENT_QSS_TEMPLATES["button_danger"] if danger else COMPONENT_QSS_TEMPLATES["button_secondary"]
        super().__init__(text, parent, template)
        self._danger = danger
        self._icon = icon
        
        if icon:
            self.setIcon(icon)
            self.setIconSize(QSize(18, 18))
        
        self.setMinimumHeight(40)
        self.setMinimumWidth(88)
    
    @property
    def danger(self) -> bool:
        return self._danger
    
    @danger.setter
    def danger(self, value: bool):
        if value != self._danger:
            self._danger = value
            template = COMPONENT_QSS_TEMPLATES["button_danger"] if value else COMPONENT_QSS_TEMPLATES["button_secondary"]
            self.set_theme_template(template)


class IconButton(BaseButton):
    """图标按钮 - 圆形/圆角，仅图标，悬停显示背景"""
    
    def __init__(self, icon: QIcon = None, parent: QWidget = None, 
                 size: int = 36, tooltip: str = "", round_shape: bool = True):
        super().__init__("", parent, COMPONENT_QSS_TEMPLATES["icon_button"])
        self._size = size
        self._round_shape = round_shape
        
        if icon:
            self.setIcon(icon)
        self.setIconSize(QSize(size - 12, size - 12))
        self.setFixedSize(size, size)
        
        if tooltip:
            self.setToolTip(tooltip)
        
        if round_shape:
            # 圆形按钮额外样式
            self.setProperty("round", True)
        
        self._apply_theme()
    
    def _apply_theme(self, theme=None):
        super()._apply_theme(theme)
        if self._round_shape:
            # 圆形按钮额外样式
            radius = self._theme_manager.get_color("radius_full")
            self.setStyleSheet(self.styleSheet() + f"""
                QPushButton[round="true"] {{
                    border-radius: {radius};
                }}
            """)


class TextButton(BaseButton):
    """文字按钮 - 无背景无边框，仅文字，悬停有背景"""
    
    def __init__(self, text: str = "", parent: QWidget = None, 
                 color: str = "primary", underline: bool = False):
        # 文字按钮使用简化模板
        template = """
            QPushButton {
                background-color: transparent;
                color: {text_secondary};
                border: none;
                border-radius: {radius_sm};
                padding: {space_xs} {space_sm};
                font-size: {font_md};
                font-weight: {font_medium};
                font-family: {font_family};
            }
            QPushButton:hover {
                background-color: {bg_hover};
                color: {text_primary};
            }
            QPushButton:pressed {
                background-color: {bg_pressed};
            }
            QPushButton:disabled {
                color: {disabled_text};
            }
        """
        super().__init__(text, parent, template)
        
        if underline:
            self.setStyleSheet(self.styleSheet() + "QPushButton { text-decoration: underline; }")


class ButtonGroup(QWidget):
    """按钮组 - 水平排列的按钮组"""
    
    def __init__(self, parent: QWidget = None, spacing: int = 8):
        super().__init__(parent)
        self._layout = QHBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(spacing)
        self._layout.addStretch()
    
    def add_button(self, button: QPushButton, stretch: int = 0):
        """添加按钮到组末尾（stretch 之前）"""
        self._layout.insertWidget(self._layout.count() - 1, button, stretch)
    
    def insert_button(self, index: int, button: QPushButton, stretch: int = 0):
        """在指定位置插入按钮"""
        self._layout.insertWidget(index, button, stretch)
    
    def add_stretch(self, stretch: int = 1):
        """添加弹性空间"""
        self._layout.insertStretch(self._layout.count() - 1, stretch)
    
    def clear(self):
        """清空所有按钮"""
        while self._layout.count() > 1:  # 保留最后的 stretch
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()