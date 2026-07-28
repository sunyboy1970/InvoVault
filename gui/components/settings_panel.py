"""
Settings Panel Component - 侧边滑出设置面板 (续)
"""

from typing import Optional, List, Dict, Any, Callable
from PySide6.QtCore import (Qt, Signal, QPropertyAnimation, QEasingCurve, QRect, 
                            QTimer, QPoint, QSize, QEvent)
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
                               QPushButton, QScrollArea, QStackedWidget, QSizePolicy,
                               QGraphicsOpacityEffect, QColorDialog, QDialogButtonBox,
                               QDialog, QApplication)
from PySide6.QtGui import QFont, QIcon, QPixmap, QPainter, QColor, QBrush, QPen, QCursor

from .theme import get_theme_manager, ThemeManager, COMPONENT_QSS_TEMPLATES
from .buttons import IconButton, PrimaryButton, SecondaryButton
from .cards import Card
from .inputs import LineEdit, SearchBox
from .selectors import ComboBox, CheckBox, Switch, RadioGroup
from .progress import ProgressBar


class SettingsDialog(QDialog):
    """设置对话框 - 模态对话框形式的设置"""
    
    accepted = Signal(dict)  # values
    rejected = Signal()
    
    def __init__(self, parent: QWidget = None, title: str = "设置", 
                 width: int = 500, height: int = 600):
        super().__init__(parent, Qt.WindowType.Dialog | Qt.WindowType.FramelessWindowHint)
        self._theme_manager = get_theme_manager()
        
        self._title = title
        self._width = width
        self._height = height
        self._values = {}
        
        self.setFixedSize(width, height)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        self._setup_ui()
        self._apply_theme()
        self._theme_manager.theme_changed.connect(self._apply_theme)
    
    def _setup_ui(self):
        """设置 UI"""
        # 主容器（带圆角阴影）
        self._container = QFrame()
        self._container.setObjectName("SettingsDialogContainer")
        self._container.setProperty("card", True)
        
        container_layout = QVBoxLayout(self._container)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(0)
        
        # 头部
        header = QWidget()
        header.setObjectName("SettingsDialogHeader")
        header_layout = QHBoxLayout(header)
        header_layout.setContentsMargins(20, 16, 20, 16)
        
        self._title_label = QLabel(self._title)
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(int(self._theme_manager.get_color("font_xl").replace("px", "")))
        font.setWeight(QFont.Weight.SemiBold)
        self._title_label.setFont(font)
        header_layout.addWidget(self._title_label)
        
        header_layout.addStretch()
        
        # 关闭按钮
        self._close_btn = IconButton(tooltip="关闭", size=32)
        self._close_btn.setText("✕")
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(16)
        font.setWeight(QFont.Weight.Bold)
        self._close_btn.setFont(font)
        self._close_btn.clicked.connect(self.reject)
        header_layout.addWidget(self._close_btn)
        
        container_layout.addWidget(header)
        
        # 分割线
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFixedHeight(1)
        container_layout.addWidget(divider)
        
        # 内容区域
        self._content = QWidget()
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(20, 20, 20, 20)
        self._content_layout.setSpacing(16)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setWidget(self._content)
        
        container_layout.addWidget(scroll, 1)
        
        # 底部按钮
        button_box = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self._on_accept)
        button_box.rejected.connect(self.reject)
        
        ok_btn = button_box.button(QDialogButtonBox.StandardButton.Ok)
        ok_btn.setText("确定")
        cancel_btn = button_box.button(QDialogButtonBox.StandardButton.Cancel)
        cancel_btn.setText("取消")
        
        container_layout.addWidget(button_box)
        
        # 主布局
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self._container)
    
    def _apply_theme(self, theme=None):
        tm = self._theme_manager
        colors = tm.colors
        
        self.setStyleSheet(f"""
            QDialog {{
                background: transparent;
            }}
            QFrame#SettingsDialogContainer {{
                background-color: {colors["card_bg"]};
                border: 1px solid {colors["card_border"]};
                border-radius: {colors["radius_xl"]};
            }}
            QWidget#SettingsDialogHeader {{
                background: transparent;
            }}
            QScrollArea {{
                background: transparent;
                border: none;
            }}
            QScrollArea > QWidget > QWidget {{
                background: transparent;
            }}
            QFrame[frameShape="4"] {{  /* HLine */
                background-color: {colors["divider"]};
                border: none;
            }}
            QDialogButtonBox QPushButton {{
                min-width: 80px;
                min-height: 36px;
            }}
        """)
        
        divider = self._container.findChild(QFrame)
        if divider:
            divider.setStyleSheet(f"background-color: {colors['divider']}; border: none;")
    
    def _on_accept(self):
        """确定按钮点击"""
        self._values = self.get_all_values()
        self.accepted.emit(self._values)
        self.accept()
    
    def add_section(self, key: str, title: str, icon: str = None) -> QWidget:
        """添加设置分组"""
        section = QWidget()
        section.setObjectName(f"SettingsSection_{key}")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 标题
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        if icon:
            icon_label = QLabel(icon)
            font = QFont(self._theme_manager.get_color("font_family"))
            font.setPointSize(int(self._theme_manager.get_color("font_lg").replace("px", "")))
            icon_label.setFont(font)
            header_layout.addWidget(icon_label)
        
        title_label = QLabel(title)
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(int(self._theme_manager.get_color("font_md").replace("px", "")))
        font.setWeight(QFont.Weight.Medium)
        title_label.setFont(font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        layout.addLayout(header_layout)
        
        # 分割线
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFixedHeight(1)
        layout.addWidget(divider)
        
        layout.addStretch()
        
        self._content_layout.addWidget(section)
        return section
    
    def add_setting(self, section: QWidget, key: str, label: str, 
                    widget: QWidget, description: str = None) -> QWidget:
        """向分组添加设置项"""
        section_layout = section.layout()
        
        item_widget = QWidget()
        item_layout = QVBoxLayout(item_widget)
        item_layout.setContentsMargins(0, 8, 0, 8)
        item_layout.setSpacing(4)
        
        # 标签行
        label_layout = QHBoxLayout()
        label_layout.setSpacing(8)
        
        label_widget = QLabel(label)
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(int(self._theme_manager.get_color("font_md").replace("px", "")))
        label_widget.setFont(font)
        label_layout.addWidget(label_widget)
        
        label_layout.addStretch()
        item_layout.addLayout(label_layout)
        
        # 描述
        if description:
            desc_label = QLabel(description)
            font = QFont(self._theme_manager.get_color("font_family"))
            font.setPointSize(int(self._theme_manager.get_color("font_xs").replace("px", "")))
            desc_label.setFont(font)
            desc_label.setWordWrap(True)
            item_layout.addWidget(desc_label)
        
        # 控件
        item_layout.addWidget(widget)
        
        # 分割线
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFixedHeight(1)
        item_layout.addWidget(divider)
        
        # 插入到 stretch 之前
        section_layout.insertWidget(section_layout.count() - 1, item_widget)
        
        # 连接信号
        self._connect_widget_signal(widget, key)
        
        return item_widget
    
    def _connect_widget_signal(self, widget: QWidget, key: str):
        """连接控件信号"""
        if hasattr(widget, 'value_changed'):
            widget.value_changed.connect(lambda v: self._on_value_changed(key, v))
        elif hasattr(widget, 'state_changed'):
            widget.state_changed.connect(lambda v: self._on_value_changed(key, v))
        elif hasattr(widget, 'currentIndexChanged'):
            widget.currentIndexChanged.connect(lambda i: self._on_value_changed(key, i))
        elif hasattr(widget, 'textChanged'):
            widget.textChanged.connect(lambda t: self._on_value_changed(key, t))
        elif hasattr(widget, 'valueChanged'):
            widget.valueChanged.connect(lambda v: self._on_value_changed(key, v))
    
    def _on_value_changed(self, key: str, value: Any):
        """值变化"""
        self._values[key] = value
    
    def add_switch_setting(self, section: QWidget, key: str, label: str,
                           checked: bool = False, description: str = None) -> Switch:
        switch = Switch()
        switch.setChecked(checked)
        self.add_setting(section, key, label, switch, description)
        return switch
    
    def add_combo_setting(self, section: QWidget, key: str, label: str,
                          options: List[dict], current_index: int = 0,
                          description: str = None) -> ComboBox:
        combo = ComboBox(items=options)
        combo.setCurrentIndex(current_index)
        self.add_setting(section, key, label, combo, description)
        return combo
    
    def add_text_setting(self, section: QWidget, key: str, label: str,
                         placeholder: str = "", default: str = "",
                         description: str = None, password: bool = False) -> LineEdit:
        line_edit = LineEdit(placeholder=placeholder, show_password=password)
        line_edit.setText(default)
        self.add_setting(section, key, label, line_edit, description)
        return line_edit
    
    def get_all_values(self) -> Dict[str, Any]:
        """获取所有值"""
        return self._values.copy()
    
    def set_values(self, values: Dict[str, Any]):
        """设置值"""
        self._values = values.copy()
    
    def showEvent(self, event):
        """显示时居中"""
        super().showEvent(event)
        if self.parentWidget():
            parent_rect = self.parentWidget().geometry()
            x = parent_rect.x() + (parent_rect.width() - self.width()) // 2
            y = parent_rect.y() + (parent_rect.height() - self.height()) // 2
            self.move(x, y)
        else:
            screen = QApplication.primaryScreen().geometry()
            x = (screen.width() - self.width()) // 2
            y = (screen.height() - self.height()) // 2
            self.move(x, y)


class SettingsPanel(QFrame):
    """侧边滑出设置面板 - 支持分组、搜索、动画展开/折叠"""
    
    # 信号
    setting_changed = Signal(str, object)  # key, value
    panel_opened = Signal()
    panel_closed = Signal()
    
    def __init__(self, parent: QWidget = None, position: str = "right",
                 width: int = 360, title: str = "设置"):
        super().__init__(parent)
        self._theme_manager = get_theme_manager()
        
        self._position = position  # "left" or "right"
        self._width = width
        self._title = title
        
        self._is_open = False
        self._animating = False
        self._overlay = None
        self._sections = {}
        
        self.setObjectName("SettingsPanel")
        self.setProperty("settingsPanel", True)
        self.setFixedWidth(width)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)
        
        # 动画
        self._animation = QPropertyAnimation(self, b"geometry")
        self._animation.setDuration(300)
        self._animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        self._animation.finished.connect(self._on_animation_finished)
        
        self._setup_ui()
        self._apply_theme()
        self._theme_manager.theme_changed.connect(self._apply_theme)
        
        # 初始隐藏
        self.hide()
    
    def _setup_ui(self):
        """设置 UI"""
        # 主布局
        self._main_layout = QVBoxLayout(self)
        self._main_layout.setContentsMargins(0, 0, 0, 0)
        self._main_layout.setSpacing(0)
        
        # 头部
        self._header = QWidget()
        self._header.setObjectName("SettingsPanelHeader")
        header_layout = QHBoxLayout(self._header)
        header_layout.setContentsMargins(16, 12, 16, 12)
        header_layout.setSpacing(8)
        
        # 返回按钮（用于子页面）
        self._back_btn = IconButton(tooltip="返回", size=32)
        self._back_btn.setText("←")
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(18)
        font.setWeight(QFont.Weight.Bold)
        self._back_btn.setFont(font)
        self._back_btn.hide()
        self._back_btn.clicked.connect(self._go_back)
        header_layout.addWidget(self._back_btn)
        
        # 标题
        self._title_label = QLabel(self._title)
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(int(self._theme_manager.get_color("font_lg").replace("px", "")))
        font.setWeight(QFont.Weight.SemiBold)
        self._title_label.setFont(font)
        header_layout.addWidget(self._title_label)
        
        header_layout.addStretch()
        
        # 关闭按钮
        self._close_btn = IconButton(tooltip="关闭", size=32)
        self._close_btn.setText("✕")
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(16)
        font.setWeight(QFont.Weight.Bold)
        self._close_btn.setFont(font)
        self._close_btn.clicked.connect(self.close_panel)
        header_layout.addWidget(self._close_btn)
        
        self._main_layout.addWidget(self._header)
        
        # 分割线
        self._divider = QFrame()
        self._divider.setFrameShape(QFrame.Shape.HLine)
        self._divider.setFixedHeight(1)
        self._main_layout.addWidget(self._divider)
        
        # 内容区域 - 使用堆叠 widget 支持多级页面
        self._stack = QStackedWidget()
        self._stack.setFrameShape(QFrame.Shape.NoFrame)
        
        # 主页面
        self._main_page = self._create_main_page()
        self._stack.addWidget(self._main_page)
        
        self._main_layout.addWidget(self._stack, 1)
        
        # 搜索栏（可选）
        self._search_box = None
    
    def _create_main_page(self) -> QWidget:
        """创建主设置页面"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        
        # 搜索框
        self._search_box = SearchBox(placeholder="搜索设置...", show_clear=True)
        self._search_box.setFixedHeight(36)
        self._search_box.textChanged.connect(self._on_search)
        layout.addWidget(self._search_box)
        
        # 滚动区域
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        
        self._content_widget = QWidget()
        self._content_layout = QVBoxLayout(self._content_widget)
        self._content_layout.setContentsMargins(0, 0, 0, 0)
        self._content_layout.setSpacing(16)
        self._content_layout.addStretch()
        
        scroll.setWidget(self._content_widget)
        layout.addWidget(scroll, 1)
        
        return page
    
    def _apply_theme(self, theme=None):
        """应用主题"""
        tm = self._theme_manager
        colors = tm.colors
        
        self.setStyleSheet(f"""
            QFrame[settingsPanel="true"] {{
                background-color: {colors["sidebar_bg"]};
                border-left: 1px solid {colors["sidebar_border"]};
            }}
            QWidget#SettingsPanelHeader {{
                background-color: transparent;
            }}
            QFrame[settingsPanel="true"] QFrame[frameShape="4"] {{  /* HLine */
                background-color: {colors["divider"]};
                border: none;
            }}
            QScrollArea {{
                background: transparent;
                border: none;
            }}
        """)
        
        self._divider.setStyleSheet(f"background-color: {colors['divider']}; border: none;")
        
        if self._search_box:
            self._search_box._apply_theme()
    
    def add_section(self, key: str, title: str, icon: str = None, 
                    widget: QWidget = None, builder: Callable = None) -> QWidget:
        """添加设置分组
        
        Args:
            key: 唯一标识
            title: 显示标题
            icon: 图标文本（emoji）
            widget: 直接提供的控件
            builder: 构建函数，接收 parent 返回控件
        
        Returns:
            创建的分组控件
        """
        section = QWidget()
        section.setObjectName(f"SettingsSection_{key}")
        layout = QVBoxLayout(section)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)
        
        # 标题行
        header_layout = QHBoxLayout()
        header_layout.setSpacing(8)
        
        if icon:
            icon_label = QLabel(icon)
            font = QFont(self._theme_manager.get_color("font_family"))
            font.setPointSize(int(self._theme_manager.get_color("font_lg").replace("px", "")))
            icon_label.setFont(font)
            header_layout.addWidget(icon_label)
        
        title_label = QLabel(title)
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(int(self._theme_manager.get_color("font_md").replace("px", "")))
        font.setWeight(QFont.Weight.Medium)
        title_label.setFont(font)
        header_layout.addWidget(title_label)
        
        header_layout.addStretch()
        
        layout.addLayout(header_layout)
        
        # 分割线
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFixedHeight(1)
        layout.addWidget(divider)
        
        # 内容
        if widget:
            layout.addWidget(widget)
        elif builder:
            content = builder(section)
            if content:
                layout.addWidget(content)
        
        self._sections[key] = {
            "widget": section,
            "title": title,
            "icon": icon,
            "items": []  # 存储设置项引用
        }
        
        self._content_layout.insertWidget(self._content_layout.count() - 1, section)
        return section
    
    def add_setting(self, section_key: str, key: str, label: str, 
                    widget: QWidget, description: str = None,
                    value_getter: Callable = None, value_setter: Callable = None) -> QWidget:
        """向分组添加设置项"""
        if section_key not in self._sections:
            return None
        
        section = self._sections[section_key]["widget"]
        section_layout = section.layout()
        
        # 设置项容器
        item_widget = QWidget()
        item_layout = QVBoxLayout(item_widget)
        item_layout.setContentsMargins(0, 8, 0, 8)
        item_layout.setSpacing(4)
        
        # 标签行
        label_layout = QHBoxLayout()
        label_layout.setSpacing(8)
        
        label_widget = QLabel(label)
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(int(self._theme_manager.get_color("font_md").replace("px", "")))
        label_widget.setFont(font)
        label_layout.addWidget(label_widget)
        
        label_layout.addStretch()
        
        item_layout.addLayout(label_layout)
        
        # 描述
        if description:
            desc_label = QLabel(description)
            font = QFont(self._theme_manager.get_color("font_family"))
            font.setPointSize(int(self._theme_manager.get_color("font_xs").replace("px", "")))
            desc_label.setFont(font)
            desc_label.setWordWrap(True)
            item_layout.addWidget(desc_label)
        
        # 控件
        item_layout.addWidget(widget)
        
        # 分割线
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setFixedHeight(1)
        item_layout.addWidget(divider)
        
        # 插入到分组的 stretch 之前
        section_layout.insertWidget(section_layout.count() - 1, item_widget)
        
        # 存储引用
        self._sections[section_key]["items"].append({
            "key": key,
            "widget": widget,
            "getter": value_getter,
            "setter": value_setter,
            "container": item_widget
        })
        
        # 连接值变化信号
        self._connect_widget_signal(widget, key)
        
        return item_widget
    
    def _connect_widget_signal(self, widget: QWidget, key: str):
        """连接控件的值变化信号"""
        if hasattr(widget, 'value_changed'):
            widget.value_changed.connect(lambda v: self.setting_changed.emit(key, v))
        elif hasattr(widget, 'state_changed'):
            widget.state_changed.connect(lambda v: self.setting_changed.emit(key, v))
        elif hasattr(widget, 'currentIndexChanged'):
            widget.currentIndexChanged.connect(lambda i: self.setting_changed.emit(key, i))
        elif hasattr(widget, 'textChanged'):
            widget.textChanged.connect(lambda t: self.setting_changed.emit(key, t))
        elif hasattr(widget, 'valueChanged'):
            widget.valueChanged.connect(lambda v: self.setting_changed.emit(key, v))
        elif hasattr(widget, 'files_changed'):
            widget.files_changed.connect(lambda f: self.setting_changed.emit(key, f))
    
    def add_switch_setting(self, section_key: str, key: str, label: str,
                           checked: bool = False, description: str = None) -> Switch:
        """添加开关设置"""
        switch = Switch()
        switch.setChecked(checked)
        self.add_setting(section_key, key, label, switch, description)
        return switch
    
    def add_combo_setting(self, section_key: str, key: str, label: str,
                          options: List[dict], current_index: int = 0,
                          description: str = None) -> ComboBox:
        """添加下拉框设置"""
        combo = ComboBox(items=options)
        combo.setCurrentIndex(current_index)
        self.add_setting(section_key, key, label, combo, description)
        return combo
    
    def add_text_setting(self, section_key: str, key: str, label: str,
                         placeholder: str = "", default: str = "",
                         description: str = None, password: bool = False) -> LineEdit:
        """添加文本输入设置"""
        line_edit = LineEdit(placeholder=placeholder, show_password=password)
        line_edit.setText(default)
        self.add_setting(section_key, key, label, line_edit, description)
        return line_edit
    
    def add_radio_setting(self, section_key: str, key: str, label: str,
                          options: List[dict], default_value: str = None,
                          description: str = None) -> RadioGroup:
        """添加单选组设置"""
        radio_group = RadioGroup(options=options, default_value=default_value)
        self.add_setting(section_key, key, label, radio_group, description)
        return radio_group
    
    def add_checkbox_setting(self, section_key: str, key: str, label: str,
                             checked: bool = False, description: str = None) -> CheckBox:
        """添加复选框设置"""
        checkbox = CheckBox(text=label, checked=checked)
        self.add_setting(section_key, key, label, checkbox, description)
        return checkbox
    
    def add_button_setting(self, section_key: str, key: str, label: str,
                           text: str, callback: Callable, 
                           primary: bool = False, description: str = None) -> QPushButton:
        """添加按钮设置"""
        btn = PrimaryButton(text) if primary else SecondaryButton(text)
        btn.clicked.connect(callback)
        self.add_setting(section_key, key, label, btn, description)
        return btn
    
    def add_slider_setting(self, section_key: str, key: str, label: str,
                           value: int = 50, minimum: int = 0, maximum: int = 100,
                           description: str = None) -> QWidget:
        """添加滑块设置"""
        from PySide6.QtWidgets import QSlider, QHBoxLayout
        
        container = QWidget()
        layout = QHBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(12)
        
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setRange(minimum, maximum)
        slider.setValue(value)
        
        value_label = QLabel(str(value))
        value_label.setFixedWidth(40)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        
        slider.valueChanged.connect(lambda v: value_label.setText(str(v)))
        slider.valueChanged.connect(lambda v: self.setting_changed.emit(key, v))
        
        layout.addWidget(slider, 1)
        layout.addWidget(value_label)
        
        self.add_setting(section_key, key, label, container, description)
        return container
    
    def get_value(self, key: str) -> Any:
        """获取设置值"""
        for section in self._sections.values():
            for item in section["items"]:
                if item["key"] == key:
                    if item["getter"]:
                        return item["getter"](item["widget"])
                    widget = item["widget"]
                    if hasattr(widget, 'isChecked'):
                        return widget.isChecked()
                    elif hasattr(widget, 'currentIndex'):
                        return widget.currentIndex()
                    elif hasattr(widget, 'text'):
                        return widget.text()
                    elif hasattr(widget, 'value'):
                        return widget.value()
                    elif hasattr(widget, 'get_files'):
                        return widget.get_files()
        return None
    
    def set_value(self, key: str, value: Any):
        """设置设置值"""
        for section in self._sections.values():
            for item in section["items"]:
                if item["key"] == key:
                    if item["setter"]:
                        item["setter"](item["widget"], value)
                    else:
                        widget = item["widget"]
                        if hasattr(widget, 'setChecked'):
                            widget.setChecked(value)
                        elif hasattr(widget, 'setCurrentIndex'):
                            widget.setCurrentIndex(value)
                        elif hasattr(widget, 'setText'):
                            widget.setText(str(value))
                        elif hasattr(widget, 'setValue'):
                            widget.setValue(value)
                        elif hasattr(widget, 'set_files'):
                            widget.set_files(value)
                    break
    
    def get_all_values(self) -> Dict[str, Any]:
        """获取所有设置值"""
        values = {}
        for section in self._sections.values():
            for item in section["items"]:
                values[item["key"]] = self.get_value(item["key"])
        return values
    
    def set_all_values(self, values: Dict[str, Any]):
        """批量设置值"""
        for key, value in values.items():
            self.set_value(key, value)
    
    def _on_search(self, text: str):
        """搜索过滤"""
        text = text.lower()
        for section in self._sections.values():
            section_widget = section["widget"]
            visible = False
            
            for item in section["items"]:
                item_widget = item["container"]
                label = item_widget.findChild(QLabel)
                match = text in item["key"].lower()
                if label:
                    match = match or text in label.text().lower()
                
                item_widget.setVisible(match)
                if match:
                    visible = True
            
            section_widget.setVisible(visible)
    
    def open_panel(self):
        """打开面板"""
        if self._is_open or self._animating:
            return
        
        self._is_open = True
        self._animating = True
        
        # 创建遮罩层
        if not self._overlay and self.parentWidget():
            self._overlay = QWidget(self.parentWidget())
            self._overlay.setStyleSheet("background-color: rgba(0, 0, 0, 0.3);")
            self._overlay.setGeometry(self.parentWidget().rect())
            self._overlay.mousePressEvent = lambda e: self.close_panel()
            self._overlay.show()
            self._overlay.raise_()
            
            # 淡入动画
            opacity_effect = QGraphicsOpacityEffect(self._overlay)
            opacity_effect.setOpacity(0.0)
            self._overlay.setGraphicsEffect(opacity_effect)
            
            anim = QPropertyAnimation(opacity_effect, b"opacity")
            anim.setDuration(200)
            anim.setStartValue(0.0)
            anim.setEndValue(1.0)
            anim.start()
        
        # 面板滑入动画
        self.show()
        self.raise_()
        
        parent_rect = self.parentWidget().rect() if self.parentWidget() else self.screen().geometry()
        
        if self._position == "right":
            start_x = parent_rect.width()
            end_x = parent_rect.width() - self._width
        else:
            start_x = -self._width
            end_x = 0
        
        start_rect = QRect(start_x, 0, self._width, parent_rect.height())
        end_rect = QRect(end_x, 0, self._width, parent_rect.height())
        
        self.setGeometry(start_rect)
        self._animation.setStartValue(start_rect)
        self._animation.setEndValue(end_rect)
        self._animation.start()
        
        self.panel_opened.emit()
    
    def close_panel(self):
        """关闭面板"""
        if not self._is_open or self._animating:
            return
        
        self._is_open = False
        self._animating = True
        
        parent_rect = self.parentWidget().rect() if self.parentWidget() else self.screen().geometry()
        
        if self._position == "right":
            end_x = parent_rect.width()
        else:
            end_x = -self._width
        
        start_rect = self.geometry()
        end_rect = QRect(end_x, 0, self._width, parent_rect.height())
        
        self._animation.setStartValue(start_rect)
        self._animation.setEndValue(end_rect)
        self._animation.start()
        
        # 遮罩层淡出
        if self._overlay:
            opacity_effect = self._overlay.graphicsEffect()
            if opacity_effect:
                anim = QPropertyAnimation(opacity_effect, b"opacity")
                anim.setDuration(200)
                anim.setStartValue(1.0)
                anim.setEndValue(0.0)
                anim.finished.connect(self._remove_overlay)
                anim.start()
    
    def _remove_overlay(self):
        """移除遮罩层"""
        if self._overlay:
            self._overlay.deleteLater()
            self._overlay = None
    
    def _on_animation_finished(self):
        """动画完成"""
        self._animating = False
        if not self._is_open:
            self.hide()
            self.panel_closed.emit()
    
    def _go_back(self):
        """返回主页面"""
        self._stack.setCurrentIndex(0)
        self._back_btn.hide()
        self._title_label.setText(self._title)
    
    def show_sub_page(self, widget: QWidget, title: str):
        """显示子页面"""
        self._stack.addWidget(widget)
        self._stack.setCurrentWidget(widget)
        self._back_btn.show()
        self._title_label.setText(title)
    
    def toggle_panel(self):
        """切换面板显示"""
        if self._is_open:
            self.close_panel()
        else:
            self.open_panel()
    
    @property
    def is_open(self) -> bool:
        return self._is_open
    
    def resizeEvent(self, event):
        """父窗口大小变化时更新位置"""
        super().resizeEvent(event)
        if self._is_open and self.parentWidget():
            parent_rect = self.parentWidget().rect()
            if self._position == "right":
                self.setGeometry(parent_rect.width() - self._width, 0, 
                                self._width, parent_rect.height())
            else:
                self.setGeometry(0, 0, self._width, parent_rect.height())
            
            if self._overlay:
                self._overlay.setGeometry(parent_rect)


# 导入 FileDropZone
from .file_drop_zone import FileDropZone