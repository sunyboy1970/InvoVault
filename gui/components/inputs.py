"""
Input Components - LineEdit, SearchBox
"""

from typing import Optional, Callable
from PySide6.QtCore import Qt, Signal, QEvent
from PySide6.QtWidgets import (QLineEdit, QWidget, QHBoxLayout, QLabel, 
                               QPushButton, QCompleter, QApplication)
from PySide6.QtGui import QIcon, QFont, QAction, QCursor, QKeyEvent

from .theme import get_theme_manager, ThemeManager, COMPONENT_QSS_TEMPLATES
from .buttons import IconButton


class LineEdit(QLineEdit):
    """增强型输入框 - 支持前缀/后缀图标、清除按钮、密码切换、加载状态"""
    
    # 自定义信号
    clear_clicked = Signal()
    prefix_clicked = Signal()
    suffix_clicked = Signal()
    enter_pressed = Signal()
    escape_pressed = Signal()
    
    def __init__(self, parent: QWidget = None, placeholder: str = "",
                 clearable: bool = False, show_password: bool = False,
                 prefix_icon: QIcon = None, suffix_icon: QIcon = None,
                 max_length: int = 0, read_only: bool = False):
        super().__init__(parent)
        self._theme_manager = get_theme_manager()
        
        self._clearable = clearable
        self._show_password = show_password
        self._prefix_icon = prefix_icon
        self._suffix_icon = suffix_icon
        self._loading = False
        self._prefix_action = None
        self._suffix_action = None
        self._clear_action = None
        
        self.setPlaceholderText(placeholder)
        if max_length > 0:
            self.setMaxLength(max_length)
        self.setReadOnly(read_only)
        
        self._setup_ui()
        self._apply_theme()
        self._theme_manager.theme_changed.connect(self._apply_theme)
        
        # 连接信号
        self.textChanged.connect(self._on_text_changed)
        self._update_clear_button()
    
    def _setup_ui(self):
        """设置 UI"""
        # 设置字体
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(int(self._theme_manager.get_color("font_md").replace("px", "")))
        self.setFont(font)
        
        # 最小高度
        self.setMinimumHeight(40)
        
        # 前缀图标
        if self._prefix_icon:
            self._prefix_action = QAction(self._prefix_icon, "", self)
            self._prefix_action.triggered.connect(self.prefix_clicked.emit)
            self.addAction(self._prefix_action, QLineEdit.ActionPosition.LeadingPosition)
        
        # 后缀图标
        if self._suffix_icon:
            self._suffix_action = QAction(self._suffix_icon, "", self)
            self._suffix_action.triggered.connect(self.suffix_clicked.emit)
            self.addAction(self._suffix_action, QLineEdit.ActionPosition.TrailingPosition)
        
        # 密码显示切换
        if self._show_password:
            self._setup_password_toggle()
        
        # 清除按钮
        if self._clearable:
            self._setup_clear_button()
    
    def _setup_password_toggle(self):
        """设置密码显示切换按钮"""
        self._password_visible = False
        self.setEchoMode(QLineEdit.EchoMode.Password)
        
        # 创建眼睛图标动作（使用内置或简单文本）
        self._eye_action = QAction(self)
        self._eye_action.setToolTip("显示密码")
        self._eye_action.triggered.connect(self._toggle_password)
        self.addAction(self._eye_action, QLineEdit.ActionPosition.TrailingPosition)
        self._update_eye_icon()
    
    def _setup_clear_button(self):
        """设置清除按钮"""
        self._clear_action = QAction(self)
        self._clear_action.setToolTip("清除")
        self._clear_action.triggered.connect(self._on_clear_clicked)
        self.addAction(self._clear_action, QLineEdit.ActionPosition.TrailingPosition)
        self._update_clear_icon()
    
    def _toggle_password(self):
        """切换密码显示"""
        self._password_visible = not self._password_visible
        if self._password_visible:
            self.setEchoMode(QLineEdit.EchoMode.Normal)
            self._eye_action.setToolTip("隐藏密码")
        else:
            self.setEchoMode(QLineEdit.EchoMode.Password)
            self._eye_action.setToolTip("显示密码")
        self._update_eye_icon()
    
    def _update_eye_icon(self):
        """更新眼睛图标"""
        # 使用简单的字符作为图标
        if self._password_visible:
            self._eye_action.setText("👁")
        else:
            self._eye_action.setText("👁️")
    
    def _update_clear_icon(self):
        """更新清除图标"""
        self._clear_action.setText("✕")
    
    def _on_clear_clicked(self):
        """清除按钮点击"""
        self.clear()
        self.clear_clicked.emit()
        self.setFocus()
    
    def _on_text_changed(self, text: str):
        """文本变化时更新清除按钮显示"""
        self._update_clear_button()
    
    def _update_clear_button(self):
        """更新清除按钮可见性"""
        if self._clear_action:
            has_text = bool(self.text())
            self._clear_action.setVisible(has_text and not self._loading and not self.isReadOnly())
    
    def _apply_theme(self, theme=None):
        """应用主题"""
        tm = self._theme_manager
        qss = tm.get_qss(COMPONENT_QSS_TEMPLATES["line_edit"])
        
        # 添加内边距以容纳图标
        padding_left = "40px" if self._prefix_icon else "16px"
        padding_right = "40px" if (self._suffix_icon or self._show_password or self._clearable) else "16px"
        
        custom_qss = f"""
            QLineEdit {{
                padding-left: {padding_left};
                padding-right: {padding_right};
            }}
        """
        self.setStyleSheet(qss + custom_qss)
    
    def set_loading(self, loading: bool):
        """设置加载状态"""
        self._loading = loading
        if loading:
            self.setEnabled(False)
            self._update_clear_button()
        else:
            self.setEnabled(True)
            self._update_clear_button()
    
    def keyPressEvent(self, event: QKeyEvent):
        """键盘事件处理"""
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.enter_pressed.emit()
        elif event.key() == Qt.Key.Key_Escape:
            self.escape_pressed.emit()
        super().keyPressEvent(event)
    
    def set_prefix_icon(self, icon: QIcon):
        """设置前缀图标"""
        if self._prefix_action:
            self.removeAction(self._prefix_action)
        self._prefix_icon = icon
        if icon:
            self._prefix_action = QAction(icon, "", self)
            self._prefix_action.triggered.connect(self.prefix_clicked.emit)
            self.addAction(self._prefix_action, QLineEdit.ActionPosition.LeadingPosition)
        self._apply_theme()
    
    def set_suffix_icon(self, icon: QIcon):
        """设置后缀图标"""
        if self._suffix_action:
            self.removeAction(self._suffix_action)
        self._suffix_icon = icon
        if icon:
            self._suffix_action = QAction(icon, "", self)
            self._suffix_action.triggered.connect(self.suffix_clicked.emit)
            self.addAction(self._suffix_action, QLineEdit.ActionPosition.TrailingPosition)
        self._apply_theme()


class SearchBox(LineEdit):
    """搜索框 - 带搜索图标、圆角胶囊形状、清除按钮"""
    
    search_requested = Signal(str)
    search_cleared = Signal()
    
    def __init__(self, parent: QWidget = None, placeholder: str = "搜索...",
                 show_clear: bool = True, debounce_ms: int = 300):
        super().__init__(parent, placeholder, clearable=show_clear, 
                         prefix_icon=None, suffix_icon=None)
        
        self._debounce_ms = debounce_ms
        self._search_timer = None
        
        # 设置搜索图标作为前缀
        self._setup_search_icon()
        
        # 连接回车搜索
        self.returnPressed.connect(self._on_search)
        
        # 连接文本变化防抖搜索
        self.textChanged.connect(self._on_text_changed_debounce)
        
        # ESC 清除搜索
        self.escape_pressed.connect(self.clear)
        
        self._apply_theme()
    
    def _setup_search_icon(self):
        """设置搜索图标"""
        # 使用简单的搜索字符
        self._search_action = QAction("🔍", self)
        self._search_action.setToolTip("搜索")
        self.addAction(self._search_action, QLineEdit.ActionPosition.LeadingPosition)
    
    def _apply_theme(self, theme=None):
        """应用主题 - 搜索框使用胶囊形状"""
        tm = self._theme_manager
        qss = tm.get_qss(COMPONENT_QSS_TEMPLATES["search_box"])
        self.setStyleSheet(qss)
        
        # 设置动作图标颜色
        self._search_action.setIconVisibleInMenu(True)
    
    def _on_search(self):
        """执行搜索"""
        text = self.text().strip()
        if text:
            self.search_requested.emit(text)
    
    def _on_text_changed_debounce(self, text: str):
        """文本变化防抖搜索"""
        if self._search_timer:
            self._search_timer.stop()
        
        if self._debounce_ms > 0:
            from PySide6.QtCore import QTimer
            self._search_timer = QTimer(self)
            self._search_timer.setSingleShot(True)
            self._search_timer.timeout.connect(lambda: self._on_search())
            self._search_timer.start(self._debounce_ms)
        else:
            self._on_search()
    
    def clear(self):
        """清除搜索"""
        super().clear()
        self.search_cleared.emit()
    
    def set_debounce(self, ms: int):
        """设置防抖时间"""
        self._debounce_ms = ms


class TextArea(QWidget):
    """多行文本输入框 - 支持自动高度、字符计数"""
    
    text_changed = Signal(str)
    
    def __init__(self, parent: QWidget = None, placeholder: str = "",
                 max_length: int = 0, show_count: bool = False,
                 min_height: int = 100, max_height: int = 300,
                 auto_height: bool = True):
        super().__init__(parent)
        self._theme_manager = get_theme_manager()
        
        self._max_length = max_length
        self._show_count = show_count
        self._min_height = min_height
        self._max_height = max_height
        self._auto_height = auto_height
        
        self._setup_ui()
        self._apply_theme()
        self._theme_manager.theme_changed.connect(self._apply_theme)
    
    def _setup_ui(self):
        from PySide6.QtWidgets import QTextEdit, QVBoxLayout, QLabel
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        self._text_edit = QTextEdit()
        self._text_edit.setPlaceholderText(placeholder)
        self._text_edit.setMinimumHeight(self._min_height)
        self._text_edit.setMaximumHeight(self._max_height)
        self._text_edit.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self._text_edit.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._text_edit.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        
        if self._max_length > 0:
            self._text_edit.textChanged.connect(self._on_text_changed)
        
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(int(self._theme_manager.get_color("font_md").replace("px", "")))
        self._text_edit.setFont(font)
        
        layout.addWidget(self._text_edit)
        
        # 字符计数
        if self._show_count:
            self._count_label = QLabel()
            self._count_label.setAlignment(Qt.AlignmentFlag.AlignRight)
            font = QFont(self._theme_manager.get_color("font_family"))
            font.setPointSize(int(self._theme_manager.get_color("font_xs").replace("px", "")))
            self._count_label.setFont(font)
            layout.addWidget(self._count_label)
            self._update_count()
    
    def _apply_theme(self, theme=None):
        tm = self._theme_manager
        colors = tm.colors
        
        self._text_edit.setStyleSheet(f"""
            QTextEdit {{
                background-color: {colors["input_bg"]};
                border: 1px solid {colors["input_border"]};
                border-radius: {colors["radius_md"]};
                padding: {colors["space_sm"]} {colors["space_md"]};
                font-size: {colors["font_md"]};
                font-family: {colors["font_family"]};
                color: {colors["text_primary"]};
                selection-background-color: {colors["primary_light"]};
            }}
            QTextEdit:hover {{
                border-color: {colors["input_hover_border"]};
            }}
            QTextEdit:focus {{
                border-color: {colors["input_focus_border"]};
                outline: none;
            }}
            QTextEdit:disabled {{
                background-color: {colors["disabled_bg"]};
                border-color: {colors["disabled_border"]};
                color: {colors["disabled_text"]};
            }}
        """)
        
        if hasattr(self, '_count_label'):
            self._count_label.setStyleSheet(f"color: {colors['text_tertiary']};")
    
    def _on_text_changed(self):
        """文本变化处理"""
        text = self._text_edit.toPlainText()
        
        # 限制最大长度
        if self._max_length > 0 and len(text) > self._max_length:
            cursor = self._text_edit.textCursor()
            cursor.setPosition(self._max_length)
            cursor.movePosition(cursor.MoveOperation.Start, cursor.MoveMode.KeepAnchor)
            cursor.removeSelectedText()
            text = text[:self._max_length]
        
        if self._show_count:
            self._update_count()
        
        self.text_changed.emit(text)
        
        # 自动调整高度
        if self._auto_height:
            self._adjust_height()
    
    def _update_count(self):
        """更新字符计数"""
        text = self._text_edit.toPlainText()
        count = len(text)
        if self._max_length > 0:
            self._count_label.setText(f"{count}/{self._max_length}")
        else:
            self._count_label.setText(str(count))
    
    def _adjust_height(self):
        """自动调整高度"""
        doc = self._text_edit.document()
        height = doc.size().height() + 24  # padding
        height = max(self._min_height, min(height, self._max_height))
        self._text_edit.setFixedHeight(int(height))
    
    def text(self) -> str:
        return self._text_edit.toPlainText()
    
    def set_text(self, text: str):
        self._text_edit.setPlainText(text)
        self._on_text_changed()
    
    def clear(self):
        self._text_edit.clear()
    
    def set_placeholder(self, text: str):
        self._text_edit.setPlaceholderText(text)
    
    def set_read_only(self, read_only: bool):
        self._text_edit.setReadOnly(read_only)
        self._apply_theme()


class NumberInput(QWidget):
    """数字输入框 - 带加减按钮、步长控制"""
    
    value_changed = Signal(float)
    
    def __init__(self, parent: QWidget = None, value: float = 0,
                 min_value: float = -999999, max_value: float = 999999,
                 step: float = 1, decimals: int = 0, prefix: str = "", 
                 suffix: str = ""):
        super().__init__(parent)
        self._theme_manager = get_theme_manager()
        
        self._value = value
        self._min_value = min_value
        self._max_value = max_value
        self._step = step
        self._decimals = decimals
        self._prefix = prefix
        self._suffix = suffix
        
        self._setup_ui()
        self._apply_theme()
        self._theme_manager.theme_changed.connect(self._apply_theme)
        self._update_display()
    
    def _setup_ui(self):
        from PySide6.QtWidgets import QHBoxLayout, QLabel
        from .buttons import IconButton
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # 减号按钮
        self._btn_minus = IconButton(tooltip="减少", size=36)
        self._btn_minus.setText("−")
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(18)
        font.setWeight(QFont.Weight.Bold)
        self._btn_minus.setFont(font)
        self._btn_minus.clicked.connect(self._decrease)
        layout.addWidget(self._btn_minus)
        
        # 输入框
        self._line_edit = LineEdit()
        self._line_edit.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._line_edit.setMinimumWidth(80)
        self._line_edit.editingFinished.connect(self._on_editing_finished)
        self._line_edit.enter_pressed.connect(self._on_editing_finished)
        layout.addWidget(self._line_edit, 1)
        
        # 加号按钮
        self._btn_plus = IconButton(tooltip="增加", size=36)
        self._btn_plus.setText("+")
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(18)
        font.setWeight(QFont.Weight.Bold)
        self._btn_plus.setFont(font)
        self._btn_plus.clicked.connect(self._increase)
        layout.addWidget(self._btn_plus)
        
        # 前缀/后缀标签
        if self._prefix:
            self._prefix_label = QLabel(self._prefix)
            layout.insertWidget(1, self._prefix_label)
        
        if self._suffix:
            self._suffix_label = QLabel(self._suffix)
            layout.addWidget(self._suffix_label)
    
    def _apply_theme(self, theme=None):
        tm = self._theme_manager
        colors = tm.colors
        
        self._line_edit.setStyleSheet(f"""
            QLineEdit {{
                background-color: {colors["input_bg"]};
                border: 1px solid {colors["input_border"]};
                border-radius: 0;
                border-top-left-radius: {colors["radius_md"]};
                border-bottom-left-radius: {colors["radius_md"]};
                padding: {colors["space_sm"]} {colors["space_md"]};
                font-size: {colors["font_md"]};
                font-family: {colors["font_family"]};
                color: {colors["text_primary"]};
            }}
            QLineEdit:hover {{
                border-color: {colors["input_hover_border"]};
            }}
            QLineEdit:focus {{
                border-color: {colors["input_focus_border"]};
                outline: none;
            }}
        """)
    
    def _update_display(self):
        """更新显示"""
        fmt = f"{{:.{self._decimals}f}}"
        self._line_edit.setText(fmt.format(self._value))
    
    def _increase(self):
        new_value = min(self._value + self._step, self._max_value)
        if new_value != self._value:
            self._value = new_value
            self._update_display()
            self.value_changed.emit(self._value)
    
    def _decrease(self):
        new_value = max(self._value - self._step, self._min_value)
        if new_value != self._value:
            self._value = new_value
            self._update_display()
            self.value_changed.emit(self._value)
    
    def _on_editing_finished(self):
        try:
            text = self._line_edit.text().replace(self._prefix, "").replace(self._suffix, "").strip()
            value = float(text)
            value = max(self._min_value, min(value, self._max_value))
            if value != self._value:
                self._value = value
                self._update_display()
                self.value_changed.emit(self._value)
            else:
                self._update_display()
        except ValueError:
            self._update_display()
    
    def value(self) -> float:
        return self._value
    
    def set_value(self, value: float):
        self._value = max(self._min_value, min(value, self._max_value))
        self._update_display()
    
    def set_range(self, min_value: float, max_value: float):
        self._min_value = min_value
        self._max_value = max_value
        self._value = max(min_value, min(self._value, max_value))
        self._update_display()
    
    def set_step(self, step: float):
        self._step = step
    
    def set_decimals(self, decimals: int):
        self._decimals = decimals
        self._update_display()