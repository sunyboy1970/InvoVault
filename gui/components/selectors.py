"""
Selector Components - ComboBox, CheckBox, RadioGroup
"""

from typing import Optional, List, Union, Any
from PySide6.QtCore import Qt, Signal, QSize, QEvent
from PySide6.QtWidgets import (QComboBox, QCheckBox, QRadioButton, QWidget, 
                               QVBoxLayout, QHBoxLayout, QButtonGroup, QLabel,
                               QFrame, QScrollArea)
from PySide6.QtGui import QFont, QIcon, QStandardItemModel, QStandardItem

from .theme import get_theme_manager, ThemeManager, COMPONENT_QSS_TEMPLATES
from .inputs import LineEdit


class ComboBox(QComboBox):
    """增强型下拉框 - 支持搜索、多选、分组、图标"""
    
    # 信号
    selection_changed = Signal(int, str)  # index, text
    
    def __init__(self, parent: QWidget = None, items: List[Union[str, dict]] = None,
                 placeholder: str = "请选择", searchable: bool = False,
                 multi_select: bool = False, max_visible_items: int = 10,
                 icon_size: QSize = QSize(16, 16)):
        super().__init__(parent)
        self._theme_manager = get_theme_manager()
        
        self._searchable = searchable
        self._multi_select = multi_select
        self._placeholder = placeholder
        self._icon_size = icon_size
        self._items_data = []  # 存储完整数据
        
        self.setMaxVisibleItems(max_visible_items)
        self.setIconSize(icon_size)
        
        self._setup_ui()
        self._apply_theme()
        self._theme_manager.theme_changed.connect(self._apply_theme)
        
        if items:
            self.add_items(items)
        
        # 连接信号
        self.currentIndexChanged.connect(self._on_index_changed)
        if self._multi_select:
            self.view().pressed.connect(self._on_view_pressed)
    
    def _setup_ui(self):
        """设置 UI"""
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(int(self._theme_manager.get_color("font_md").replace("px", "")))
        self.setFont(font)
        
        self.setMinimumHeight(40)
        
        # 设置占位符（通过插入一个禁用项实现）
        if self._placeholder:
            self._add_placeholder()
        
        # 搜索功能
        if self._searchable:
            self._setup_search()
    
    def _add_placeholder(self):
        """添加占位符项"""
        placeholder_item = QStandardItem(self._placeholder)
        placeholder_item.setEnabled(False)
        placeholder_item.setForeground(self._theme_manager.get_color("text_tertiary"))
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(int(self._theme_manager.get_color("font_md").replace("px", "")))
        placeholder_item.setFont(font)
        
        model = self.model()
        if isinstance(model, QStandardItemModel):
            model.insertRow(0, placeholder_item)
        else:
            # 转换为 StandardItemModel
            new_model = QStandardItemModel()
            new_model.appendRow(placeholder_item)
            self.setModel(new_model)
    
    def _setup_search(self):
        """设置搜索功能"""
        self.setEditable(True)
        self.setInsertPolicy(QComboBox.InsertPolicy.NoInsert)
        
        # 设置行编辑器
        line_edit = self.lineEdit()
        line_edit.setPlaceholderText(self._placeholder)
        line_edit.setReadOnly(False)
        line_edit.textChanged.connect(self._on_search_text_changed)
        
        # 设置完成器
        self._completer = None
        self._update_completer()
    
    def _update_completer(self):
        """更新完成器"""
        if not self._searchable:
            return
        
        from PySide6.QtWidgets import QCompleter
        self._completer = QCompleter(self._get_item_texts(), self)
        self._completer.setCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self._completer.setFilterMode(Qt.MatchFlag.MatchContains)
        self._completer.setCompletionMode(QCompleter.CompletionMode.PopupCompletion)
        self.setCompleter(self._completer)
    
    def _get_item_texts(self) -> List[str]:
        """获取所有项目文本"""
        texts = []
        for i in range(self.count()):
            texts.append(self.itemText(i))
        return texts
    
    def _on_search_text_changed(self, text: str):
        """搜索文本变化"""
        if not self._searchable:
            return
        
        # 过滤下拉列表
        for i in range(self.count()):
            item_text = self.itemText(i)
            match = text.lower() in item_text.lower()
            self.model().item(i).setHidden(not match)
    
    def _on_index_changed(self, index: int):
        """索引变化"""
        if index >= 0:
            text = self.itemText(index)
            self.selection_changed.emit(index, text)
    
    def _on_view_pressed(self, index):
        """视图点击（多选模式）"""
        if not self._multi_select:
            return
        
        item = self.model().itemFromIndex(index)
        if item and item.isEnabled():
            item.setCheckState(
                Qt.CheckState.Unchecked if item.checkState() == Qt.CheckState.Checked 
                else Qt.CheckState.Checked
            )
            self._update_multi_selection()
    
    def _update_multi_selection(self):
        """更新多选状态"""
        selected = []
        for i in range(self.count()):
            item = self.model().item(i)
            if item and item.checkState() == Qt.CheckState.Checked:
                selected.append(item.text())
        
        if selected:
            self.lineEdit().setText(", ".join(selected))
        else:
            self.lineEdit().setText("")
            self.lineEdit().setPlaceholderText(self._placeholder)
    
    def add_items(self, items: List[Union[str, dict]]):
        """批量添加项目
        items 可以是:
        - 字符串列表: ["Item 1", "Item 2"]
        - 字典列表: [{"text": "Item 1", "icon": icon, "data": "value1"}, ...]
        """
        model = self.model()
        if not isinstance(model, QStandardItemModel):
            model = QStandardItemModel()
            self.setModel(model)
        
        # 保留占位符
        start_row = 1 if self._placeholder and model.rowCount() > 0 else 0
        
        for item_data in items:
            if isinstance(item_data, str):
                item = QStandardItem(item_data)
                item.setData(item_data, Qt.ItemDataRole.UserRole)
            elif isinstance(item_data, dict):
                text = item_data.get("text", "")
                icon = item_data.get("icon")
                data = item_data.get("data", text)
                disabled = item_data.get("disabled", False)
                
                item = QStandardItem(text)
                item.setData(data, Qt.ItemDataRole.UserRole)
                if icon:
                    item.setIcon(icon)
                if disabled:
                    item.setEnabled(False)
            else:
                continue
            
            item.setFont(QFont(self._theme_manager.get_color("font_family"),
                             int(self._theme_manager.get_color("font_md").replace("px", ""))))
            
            if self._multi_select:
                item.setCheckable(True)
                item.setCheckState(Qt.CheckState.Unchecked)
            
            model.appendRow(item)
            self._items_data.append(item_data)
        
        self._update_completer()
    
    def add_item(self, text: str, data: Any = None, icon: QIcon = None, disabled: bool = False):
        """添加单个项目"""
        self.add_items([{
            "text": text,
            "data": data if data is not None else text,
            "icon": icon,
            "disabled": disabled
        }])
    
    def clear_items(self, keep_placeholder: bool = True):
        """清空项目"""
        model = self.model()
        if isinstance(model, QStandardItemModel):
            if keep_placeholder and self._placeholder:
                # 只保留第一行（占位符）
                while model.rowCount() > 1:
                    model.removeRow(1)
            else:
                model.clear()
                if self._placeholder:
                    self._add_placeholder()
        self._items_data.clear()
        self._update_completer()
    
    def get_current_data(self) -> Any:
        """获取当前选中项的数据"""
        index = self.currentIndex()
        if index >= 0:
            item = self.model().item(index)
            if item:
                return item.data(Qt.ItemDataRole.UserRole)
        return None
    
    def get_selected_data(self) -> List[Any]:
        """获取所有选中项的数据（多选模式）"""
        if not self._multi_select:
            return [self.get_current_data()] if self.get_current_data() else []
        
        data = []
        for i in range(self.count()):
            item = self.model().item(i)
            if item and item.checkState() == Qt.CheckState.Checked:
                data.append(item.data(Qt.ItemDataRole.UserRole))
        return data
    
    def set_current_data(self, data: Any):
        """通过数据设置当前项"""
        for i in range(self.count()):
            item = self.model().item(i)
            if item and item.data(Qt.ItemDataRole.UserRole) == data:
                self.setCurrentIndex(i)
                break
    
    def _apply_theme(self, theme=None):
        """应用主题"""
        tm = self._theme_manager
        qss = tm.get_qss(COMPONENT_QSS_TEMPLATES["combo_box"])
        self.setStyleSheet(qss)


class CheckBox(QCheckBox):
    """增强型复选框 - 支持三态、不确定状态、自定义文本"""
    
    state_changed = Signal(bool)  # checked
    
    def __init__(self, text: str = "", parent: QWidget = None, 
                 tristate: bool = False, checked: bool = False):
        super().__init__(text, parent)
        self._theme_manager = get_theme_manager()
        
        self.setTristate(tristate)
        self.setChecked(checked)
        
        self._setup_ui()
        self._apply_theme()
        self._theme_manager.theme_changed.connect(self._apply_theme)
        
        self.stateChanged.connect(self._on_state_changed)
    
    def _setup_ui(self):
        """设置 UI"""
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(int(self._theme_manager.get_color("font_md").replace("px", "")))
        self.setFont(font)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def _on_state_changed(self, state: int):
        """状态变化"""
        checked = state == Qt.CheckState.Checked.value
        self.state_changed.emit(checked)
    
    def _apply_theme(self, theme=None):
        """应用主题"""
        tm = self._theme_manager
        qss = tm.get_qss(COMPONENT_QSS_TEMPLATES["checkbox"])
        self.setStyleSheet(qss)
    
    def set_text(self, text: str):
        """设置文本"""
        self.setText(text)
    
    def set_indeterminate(self, indeterminate: bool):
        """设置不确定状态（三态模式）"""
        if self.isTristate():
            self.setCheckState(Qt.CheckState.PartiallyChecked if indeterminate else Qt.CheckState.Unchecked)


class RadioButton(QRadioButton):
    """单选按钮"""
    
    def __init__(self, text: str = "", parent: QWidget = None, checked: bool = False):
        super().__init__(text, parent)
        self._theme_manager = get_theme_manager()
        
        self.setChecked(checked)
        self._setup_ui()
        self._apply_theme()
        self._theme_manager.theme_changed.connect(self._apply_theme)
    
    def _setup_ui(self):
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(int(self._theme_manager.get_color("font_md").replace("px", "")))
        self.setFont(font)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def _apply_theme(self, theme=None):
        tm = self._theme_manager
        qss = tm.get_qss(COMPONENT_QSS_TEMPLATES["radio_button"])
        self.setStyleSheet(qss)


class RadioGroup(QWidget):
    """单选组 - 管理一组单选按钮，支持水平/垂直布局"""
    
    value_changed = Signal(str)  # selected value
    
    def __init__(self, parent: QWidget = None, options: List[dict] = None,
                 orientation: Qt.Orientation = Qt.Orientation.Vertical,
                 spacing: int = 12, default_value: str = None):
        super().__init__(parent)
        self._theme_manager = get_theme_manager()
        
        self._orientation = orientation
        self._spacing = spacing
        self._buttons = {}
        self._button_group = QButtonGroup(self)
        self._button_group.setExclusive(True)
        self._button_group.idClicked.connect(self._on_button_clicked)
        
        self._setup_ui()
        self._apply_theme()
        self._theme_manager.theme_changed.connect(self._apply_theme)
        
        if options:
            self.add_options(options)
        
        if default_value:
            self.set_value(default_value)
    
    def _setup_ui(self):
        """设置 UI"""
        if self._orientation == Qt.Orientation.Horizontal:
            self._layout = QHBoxLayout(self)
        else:
            self._layout = QVBoxLayout(self)
        
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(self._spacing)
    
    def add_options(self, options: List[dict]):
        """批量添加选项
        options: [{"value": "v1", "text": "Option 1", "disabled": False}, ...]
        """
        for i, opt in enumerate(options):
            self.add_option(
                value=opt.get("value", str(i)),
                text=opt.get("text", str(i)),
                disabled=opt.get("disabled", False)
            )
    
    def add_option(self, value: str, text: str, disabled: bool = False):
        """添加单个选项"""
        radio = RadioButton(text, self)
        radio.setProperty("radioValue", value)
        radio.setEnabled(not disabled)
        
        button_id = len(self._buttons)
        self._button_group.addButton(radio, button_id)
        self._buttons[value] = radio
        
        self._layout.addWidget(radio)
    
    def remove_option(self, value: str):
        """移除选项"""
        if value in self._buttons:
            radio = self._buttons.pop(value)
            self._button_group.removeButton(radio)
            radio.deleteLater()
    
    def clear_options(self):
        """清空选项"""
        for radio in self._buttons.values():
            self._button_group.removeButton(radio)
            radio.deleteLater()
        self._buttons.clear()
    
    def _on_button_clicked(self, button_id: int):
        """按钮点击"""
        button = self._button_group.button(button_id)
        if button:
            value = button.property("radioValue")
            self.value_changed.emit(value)
    
    def _apply_theme(self, theme=None):
        """应用主题"""
        # RadioButton 自己处理主题
        pass
    
    def value(self) -> Optional[str]:
        """获取当前选中的值"""
        checked_button = self._button_group.checkedButton()
        if checked_button:
            return checked_button.property("radioValue")
        return None
    
    def set_value(self, value: str):
        """设置选中的值"""
        if value in self._buttons:
            self._buttons[value].setChecked(True)
    
    def get_button(self, value: str) -> Optional[RadioButton]:
        """获取指定值的按钮"""
        return self._buttons.get(value)
    
    def set_enabled(self, value: str, enabled: bool):
        """设置某个选项的启用状态"""
        if value in self._buttons:
            self._buttons[value].setEnabled(enabled)


class CheckBoxGroup(QWidget):
    """复选框组 - 管理一组复选框"""
    
    values_changed = Signal(list)  # selected values
    
    def __init__(self, parent: QWidget = None, options: List[dict] = None,
                 orientation: Qt.Orientation = Qt.Orientation.Vertical,
                 spacing: int = 12, max_columns: int = 0):
        super().__init__(parent)
        self._theme_manager = get_theme_manager()
        
        self._orientation = orientation
        self._spacing = spacing
        self._max_columns = max_columns
        self._checkboxes = {}
        
        self._setup_ui()
        self._apply_theme()
        self._theme_manager.theme_changed.connect(self._apply_theme)
        
        if options:
            self.add_options(options)
    
    def _setup_ui(self):
        """设置 UI"""
        if self._max_columns > 0 and self._orientation == Qt.Orientation.Horizontal:
            # 网格布局
            from PySide6.QtWidgets import QGridLayout
            self._layout = QGridLayout(self)
        elif self._orientation == Qt.Orientation.Horizontal:
            self._layout = QHBoxLayout(self)
        else:
            self._layout = QVBoxLayout(self)
        
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(self._spacing)
    
    def add_options(self, options: List[dict]):
        """批量添加选项"""
        for i, opt in enumerate(options):
            self.add_option(
                value=opt.get("value", str(i)),
                text=opt.get("text", str(i)),
                checked=opt.get("checked", False),
                disabled=opt.get("disabled", False)
            )
    
    def add_option(self, value: str, text: str, checked: bool = False, disabled: bool = False):
        """添加单个选项"""
        checkbox = CheckBox(text, self)
        checkbox.setProperty("checkboxValue", value)
        checkbox.setChecked(checked)
        checkbox.setEnabled(not disabled)
        checkbox.state_changed.connect(self._on_state_changed)
        
        self._checkboxes[value] = checkbox
        
        if isinstance(self._layout, QGridLayout):
            row = len(self._checkboxes) // self._max_columns
            col = len(self._checkboxes) % self._max_columns
            self._layout.addWidget(checkbox, row, col)
        else:
            self._layout.addWidget(checkbox)
    
    def _on_state_changed(self, checked: bool):
        """任意复选框状态变化"""
        self.values_changed.emit(self.values())
    
    def _apply_theme(self, theme=None):
        pass
    
    def values(self) -> List[str]:
        """获取所有选中的值"""
        return [v for v, cb in self._checkboxes.items() if cb.isChecked()]
    
    def set_values(self, values: List[str]):
        """设置选中的值"""
        for v, cb in self._checkboxes.items():
            cb.setChecked(v in values)
    
    def is_checked(self, value: str) -> bool:
        """检查某个值是否选中"""
        cb = self._checkboxes.get(value)
        return cb.isChecked() if cb else False
    
    def set_enabled(self, value: str, enabled: bool):
        """设置某个选项的启用状态"""
        if value in self._checkboxes:
            self._checkboxes[value].setEnabled(enabled)
    
    def clear(self):
        """清空所有选中"""
        for cb in self._checkboxes.values():
            cb.setChecked(False)
    
    def select_all(self):
        """全选"""
        for cb in self._checkboxes.values():
            if cb.isEnabled():
                cb.setChecked(True)


class Switch(QCheckBox):
    """开关组件 - iOS 风格开关"""
    
    def __init__(self, parent: QWidget = None, checked: bool = False, 
                 size: str = "md"):
        super().__init__("", parent)
        self._theme_manager = get_theme_manager()
        self._size = size  # sm, md, lg
        
        self.setChecked(checked)
        self.setTristate(False)
        
        self._setup_ui()
        self._apply_theme()
        self._theme_manager.theme_changed.connect(self._apply_theme)
    
    def _setup_ui(self):
        """设置 UI"""
        sizes = {
            "sm": {"width": 36, "height": 20, "thumb": 16},
            "md": {"width": 44, "height": 24, "thumb": 20},
            "lg": {"width": 52, "height": 28, "thumb": 24},
        }
        s = sizes.get(self._size, sizes["md"])
        self._track_width = s["width"]
        self._track_height = s["height"]
        self._thumb_size = s["thumb"]
        
        self.setFixedSize(self._track_width, self._track_height)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def _apply_theme(self, theme=None):
        tm = self._theme_manager
        colors = tm.colors
        
        qss = f"""
            QCheckBox {{
                spacing: 0;
            }}
            QCheckBox::indicator {{
                width: {self._track_width}px;
                height: {self._track_height}px;
                border-radius: {self._track_height // 2}px;
                border: none;
            }}
            QCheckBox::indicator:unchecked {{
                background-color: {colors["border_primary"]};
            }}
            QCheckBox::indicator:unchecked:hover {{
                background-color: {colors["border_primary"]};
                opacity: 0.8;
            }}
            QCheckBox::indicator:checked {{
                background-color: {colors["primary"]};
            }}
            QCheckBox::indicator:checked:hover {{
                background-color: {colors["primary_hover"]};
            }}
            QCheckBox::indicator:disabled {{
                background-color: {colors["disabled_border"]};
                opacity: 0.5;
            }}
        """
        self.setStyleSheet(qss)