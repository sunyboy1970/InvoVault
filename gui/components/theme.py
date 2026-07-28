"""
Theme Manager - 统一主题管理
支持浅色/深色模式切换，统一设计语言：圆角卡片、主色调 #1890FF
"""

from enum import Enum
from typing import Dict, Optional
from PySide6.QtCore import QObject, Signal, QSettings
from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtGui import QColor, QPalette


class Theme(Enum):
    """主题枚举"""
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"


# 浅色主题色彩定义
LIGHT_THEME = {
    # Primary colors
    "primary": "#1890FF",
    "primary_hover": "#40A9FF",
    "primary_pressed": "#096DD9",
    "primary_light": "#E6F7FF",
    "primary_text": "#FFFFFF",
    
    # Neutral colors
    "bg_primary": "#FFFFFF",
    "bg_secondary": "#F5F5F5",
    "bg_tertiary": "#FAFAFA",
    "bg_hover": "#F0F0F0",
    "bg_pressed": "#E8E8E8",
    
    # Card colors
    "card_bg": "#FFFFFF",
    "card_border": "#F0F0F0",
    "card_shadow": "rgba(0, 0, 0, 0.08)",
    "elevated_card_shadow": "rgba(0, 0, 0, 0.12)",
    
    # Text colors
    "text_primary": "#1F1F1F",
    "text_secondary": "#595959",
    "text_tertiary": "#8C8C8C",
    "text_disabled": "#BFBFBF",
    "text_inverse": "#FFFFFF",
    
    # Border colors
    "border_primary": "#D9D9D9",
    "border_secondary": "#F0F0F0",
    "border_focus": "#1890FF",
    
    # Status colors
    "success": "#52C41A",
    "success_light": "#F6FFED",
    "warning": "#FAAD14",
    "warning_light": "#FFFBE6",
    "error": "#FF4D4F",
    "error_light": "#FFF1F0",
    "info": "#1890FF",
    "info_light": "#E6F7FF",
    
    # Component specific
    "input_bg": "#FFFFFF",
    "input_border": "#D9D9D9",
    "input_placeholder": "#BFBFBF",
    "input_hover_border": "#40A9FF",
    "input_focus_border": "#1890FF",
    "input_focus_shadow": "rgba(24, 144, 255, 0.2)",
    
    "button_primary_bg": "#1890FF",
    "button_primary_hover": "#40A9FF",
    "button_primary_pressed": "#096DD9",
    "button_primary_text": "#FFFFFF",
    
    "button_secondary_bg": "#FFFFFF",
    "secondary_hover": "#F5F5F5",
    "button_secondary_pressed": "#F0F0F0",
    "button_secondary_text": "#1890FF",
    "button_secondary_border": "#1890FF",
    
    "button_danger_bg": "#FF4D4F",
    "button_danger_hover": "#FF7875",
    "button_danger_pressed": "#D9363E",
    "button_danger_text": "#FFFFFF",
    
    "disabled_bg": "#F5F5F5",
    "disabled_border": "#D9D9D9",
    "disabled_text": "#BFBFBF",
    
    "divider": "#F0F0F0",
    "shadow": "rgba(0, 0, 0, 0.08)",
    "overlay": "rgba(0, 0, 0, 0.45)",
    
    # Tooltip
    "tooltip_bg": "rgba(0, 0, 0, 0.75)",
    "tooltip_text": "#FFFFFF",
    
    # Scrollbar
    "scrollbar_bg": "transparent",
    "scrollbar_handle": "#C1C1C1",
    "scrollbar_handle_hover": "#999999",
    
    # Drop zone
    "dropzone_bg": "#FAFAFA",
    "dropzone_border": "#D9D9D9",
    "dropzone_hover_bg": "#E6F7FF",
    "dropzone_hover_border": "#1890FF",
    "dropzone_active_bg": "#E6F7FF",
    "dropzone_active_border": "#1890FF",
    
    # Settings panel
    "sidebar_bg": "#FAFAFA",
    "sidebar_border": "#F0F0F0",
    "sidebar_item_hover": "#F0F0F0",
    "sidebar_item_active": "#E6F7FF",
    "sidebar_item_active_text": "#1890FF",
    
    # Toast/Notification
    "toast_bg": "rgba(0, 0, 0, 0.85)",
    "toast_text": "#FFFFFF",
    "toast_success_bg": "#52C41A",
    "toast_error_bg": "#FF4D4F",
    "toast_warning_bg": "#FAAD14",
    "toast_info_bg": "#1890FF",
    
    # Progress
    "progress_bg": "#F0F0F0",
    "progress_bar": "#1890FF",
    
    # Badge
    "badge_bg": "#FF4D4F",
    "badge_text": "#FFFFFF",
    
    # Divider
    "divider_text": "#8C8C8C",
    
    # Tooltip
    "tooltip_bg": "rgba(0, 0, 0, 0.75)",
    "tooltip_text": "#FFFFFF",
    
    # Border radius
    "radius_sm": "4px",
    "radius_md": "8px",
    "radius_lg": "12px",
    "radius_xl": "16px",
    "radius_full": "9999px",
    
    # Shadows
    "shadow_sm": "0 1px 2px rgba(0, 0, 0, 0.03), 0 1px 6px -1px rgba(0, 0, 0, 0.02), 0 2px 4px rgba(0, 0, 0, 0.02)",
    "shadow_md": "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
    "shadow_lg": "0 10px 15px -3px rgba(0, 0, 0, 0.1), 0 4px 6px -2px rgba(0, 0, 0, 0.05)",
    "shadow_xl": "0 20px 25px -5px rgba(0, 0, 0, 0.1), 0 10px 10px -5px rgba(0, 0, 0, 0.04)",
    
    # Transitions
    "transition_fast": "150ms ease",
    "transition_base": "200ms ease",
    "transition_slow": "300ms ease",
    
    # Spacing
    "space_xs": "4px",
    "space_sm": "8px",
    "space_md": "16px",
    "space_lg": "24px",
    "space_xl": "32px",
    
    # Font sizes
    "font_xs": "11px",
    "font_sm": "12px",
    "font_md": "14px",
    "font_lg": "16px",
    "font_xl": "18px",
    "font_2xl": "20px",
    "font_3xl": "24px",
    
    # Font weights
    "font_normal": "400",
    "font_medium": "500",
    "font_semibold": "600",
    "font_bold": "700",
    
    # Font family
    "font_family": '"PingFang SC", "Microsoft YaHei", "Helvetica Neue", Helvetica, Arial, sans-serif',
    "font_mono": '"JetBrains Mono", "Fira Code", Consolas, monospace',
}


# 深色主题色彩定义
DARK_THEME = {
    # Primary colors
    "primary": "#177DD2",
    "primary_hover": "#3B9BEB",
    "primary_pressed": "#0C5CB8",
    "primary_light": "#112B42",
    "primary_text": "#FFFFFF",
    
    # Neutral colors
    "bg_primary": "#141414",
    "bg_secondary": "#1F1F1F",
    "bg_tertiary": "#262626",
    "bg_hover": "#2A2A2A",
    "bg_pressed": "#333333",
    
    # Card colors
    "card_bg": "#1F1F1F",
    "card_border": "#303030",
    "card_shadow": "rgba(0, 0, 0, 0.3)",
    "elevated_card_shadow": "rgba(0, 0, 0, 0.4)",
    
    # Text colors
    "text_primary": "#FFFFFF",
    "text_secondary": "#BFBFBF",
    "text_tertiary": "#8C8C8C",
    "text_disabled": "#595959",
    "text_inverse": "#141414",
    
    # Border colors
    "border_primary": "#303030",
    "border_secondary": "#262626",
    "border_focus": "#177DD2",
    
    # Status colors
    "success": "#49AA19",
    "success_light": "#162312",
    "warning": "#D48806",
    "warning_light": "#2B1F08",
    "error": "#D9363E",
    "error_light": "#2B1214",
    "info": "#177DD2",
    "info_light": "#10273E",
    
    # Component specific
    "input_bg": "#1F1F1F",
    "input_border": "#303030",
    "input_placeholder": "#595959",
    "input_hover_border": "#3B9BEB",
    "input_focus_border": "#177DD2",
    "input_focus_shadow": "rgba(23, 125, 210, 0.3)",
    
    "button_primary_bg": "#177DD2",
    "button_primary_hover": "#3B9BEB",
    "button_primary_pressed": "#0C5CB8",
    "button_primary_text": "#FFFFFF",
    
    "button_secondary_bg": "#1F1F1F",
    "secondary_hover": "#2A2A2A",
    "button_secondary_pressed": "#333333",
    "button_secondary_text": "#177DD2",
    "button_secondary_border": "#177DD2",
    
    "button_danger_bg": "#D9363E",
    "button_danger_hover": "#E6545B",
    "button_danger_pressed": "#A8242B",
    "button_danger_text": "#FFFFFF",
    
    "disabled_bg": "#262626",
    "disabled_border": "#303030",
    "disabled_text": "#595959",
    
    "divider": "#303030",
    "shadow": "rgba(0, 0, 0, 0.3)",
    "overlay": "rgba(0, 0, 0, 0.6)",
    
    # Tooltip
    "tooltip_bg": "rgba(255, 255, 255, 0.9)",
    "tooltip_text": "#141414",
    
    # Scrollbar
    "scrollbar_bg": "transparent",
    "scrollbar_handle": "#4D4D4D",
    "scrollbar_handle_hover": "#595959",
    
    # Drop zone
    "dropzone_bg": "#1F1F1F",
    "dropzone_border": "#303030",
    "dropzone_hover_bg": "#112B42",
    "dropzone_hover_border": "#177DD2",
    "dropzone_active_bg": "#112B42",
    "dropzone_active_border": "#177DD2",
    
    # Settings panel
    "sidebar_bg": "#1F1F1F",
    "sidebar_border": "#303030",
    "sidebar_item_hover": "#2A2A2A",
    "sidebar_item_active": "#112B42",
    "sidebar_item_active_text": "#177DD2",
    
    # Toast/Notification
    "toast_bg": "rgba(255, 255, 255, 0.9)",
    "toast_text": "#141414",
    "toast_success_bg": "#49AA19",
    "toast_error_bg": "#D9363E",
    "toast_warning_bg": "#D48806",
    "toast_info_bg": "#177DD2",
    
    # Progress
    "progress_bg": "#303030",
    "progress_bar": "#177DD2",
    
    # Badge
    "badge_bg": "#D9363E",
    "badge_text": "#FFFFFF",
    
    # Divider
    "divider_text": "#8C8C8C",
    
    # Tooltip
    "tooltip_bg": "rgba(255, 255, 255, 0.9)",
    "tooltip_text": "#141414",
    
    # Border radius (same as light)
    "radius_sm": "4px",
    "radius_md": "8px",
    "radius_lg": "12px",
    "radius_xl": "16px",
    "radius_full": "9999px",
    
    # Shadows (darker for dark mode)
    "shadow_sm": "0 1px 2px rgba(0, 0, 0, 0.15), 0 1px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px rgba(0, 0, 0, 0.1)",
    "shadow_md": "0 4px 6px -1px rgba(0, 0, 0, 0.3), 0 2px 4px -1px rgba(0, 0, 0, 0.2)",
    "shadow_lg": "0 10px 15px -3px rgba(0, 0, 0, 0.3), 0 4px 6px -2px rgba(0, 0, 0, 0.15)",
    "shadow_xl": "0 20px 25px -5px rgba(0, 0, 0, 0.3), 0 10px 10px -5px rgba(0, 0, 0, 0.15)",
    
    # Transitions (same as light)
    "transition_fast": "150ms ease",
    "transition_base": "200ms ease",
    "transition_slow": "300ms ease",
    
    # Spacing (same as light)
    "space_xs": "4px",
    "space_sm": "8px",
    "space_md": "16px",
    "space_lg": "24px",
    "space_xl": "32px",
    
    # Font sizes (same as light)
    "font_xs": "11px",
    "font_sm": "12px",
    "font_md": "14px",
    "font_lg": "16px",
    "font_xl": "18px",
    "font_2xl": "20px",
    "font_3xl": "24px",
    
    # Font weights (same as light)
    "font_normal": "400",
    "font_medium": "500",
    "font_semibold": "600",
    "font_bold": "700",
    
    # Font family (same as light)
    "font_family": '"PingFang SC", "Microsoft YaHei", "Helvetica Neue", Helvetica, Arial, sans-serif',
    "font_mono": '"JetBrains Mono", "Fira Code", Consolas, monospace',
}


class ThemeManager(QObject):
    """主题管理器 - 单例模式"""
    
    theme_changed = Signal(Theme)
    
    _instance: Optional["ThemeManager"] = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if hasattr(self, "_initialized"):
            return
        super().__init__()
        self._initialized = True
        
        self._current_theme = Theme.SYSTEM
        self._themes: Dict[Theme, Dict[str, str]] = {
            Theme.LIGHT: LIGHT_THEME,
            Theme.DARK: DARK_THEME,
        }
        self._settings = QSettings("InvoiceExtractor", "Theme")
        self._load_theme()
        self._apply_system_theme()
        
        # 监听系统主题变化
        app = QApplication.instance()
        if app:
            app.paletteChanged.connect(self._on_palette_changed)
    
    def _load_theme(self):
        """从设置加载主题"""
        saved = self._settings.value("theme", Theme.SYSTEM.value)
        try:
            self._current_theme = Theme(saved)
        except ValueError:
            self._current_theme = Theme.SYSTEM
    
    def _save_theme(self):
        """保存主题到设置"""
        self._settings.setValue("theme", self._current_theme.value)
    
    def _apply_system_theme(self):
        """根据系统主题应用主题"""
        if self._current_theme == Theme.SYSTEM:
            app = QApplication.instance()
            if app:
                palette = app.palette()
                # 检测系统主题（简单检测：窗口背景色亮度）
                bg_color = palette.color(QPalette.ColorRole.Window)
                is_dark = bg_color.lightness() < 128
                effective_theme = Theme.DARK if is_dark else Theme.LIGHT
                self._apply_theme(effective_theme)
    
    def _on_palette_changed(self, palette: QPalette):
        """系统调色板变化时自动切换主题"""
        if self._current_theme == Theme.SYSTEM:
            self._apply_system_theme()
    
    def _apply_theme(self, theme: Theme):
        """应用主题到应用程序"""
        theme_colors = self._themes[theme]
        qss = self._generate_qss(theme_colors)
        app = QApplication.instance()
        if app:
            app.setStyleSheet(qss)
    
    def _generate_qss(self, colors: Dict[str, str]) -> str:
        """生成全局 QSS 样式表"""
        return f"""
        /* ===== Global Base Styles ===== */
        * {{
            font-family: {colors["font_family"]};
            font-size: {colors["font_md"]};
            color: {colors["text_primary"]};
        }}
        
        QWidget {{
            background-color: {colors["bg_primary"]};
            color: {colors["text_primary"]};
        }}
        
        /* ===== Scrollbar ===== */
        QScrollBar:vertical {{
            background: {colors["scrollbar_bg"]};
            width: 8px;
            border-radius: 4px;
            margin: 0;
        }}
        QScrollBar::handle:vertical {{
            background: {colors["scrollbar_handle"]};
            border-radius: 4px;
            min-height: 30px;
        }}
        QScrollBar::handle:vertical:hover {{
            background: {colors["scrollbar_handle_hover"]};
        }}
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
            height: 0;
        }}
        QScrollBar:horizontal {{
            background: {colors["scrollbar_bg"]};
            height: 8px;
            border-radius: 4px;
            margin: 0;
        }}
        QScrollBar::handle:horizontal {{
            background: {colors["scrollbar_handle"]};
            border-radius: 4px;
            min-width: 30px;
        }}
        QScrollBar::handle:horizontal:hover {{
            background: {colors["scrollbar_handle_hover"]};
        }}
        QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{
            width: 0;
        }}
        
        /* ===== Tooltip ===== */
        QToolTip {{
            background-color: {colors["tooltip_bg"]};
            color: {colors["tooltip_text"]};
            border: none;
            border-radius: {colors["radius_sm"]};
            padding: {colors["space_xs"]} {colors["space_sm"]};
            font-size: {colors["font_sm"]};
        }}
        
        /* ===== Focus ===== */
        QWidget:focus {{
            outline: none;
        }}
        
        /* ===== Selection ===== */
        QWidget::item:selected {{
            background-color: {colors["primary_light"]};
            color: {colors["primary"]};
        }}
        
        /* ===== Scroll Area ===== */
        QScrollArea {{
            border: none;
            background: transparent;
        }}
        QScrollArea > QWidget > QWidget {{
            background: transparent;
        }}
        """
    
    @property
    def current_theme(self) -> Theme:
        return self._current_theme
    
    @property
    def effective_theme(self) -> Theme:
        """获取实际生效的主题（SYSTEM 时返回实际系统主题）"""
        if self._current_theme == Theme.SYSTEM:
            app = QApplication.instance()
            if app:
                palette = app.palette()
                bg_color = palette.color(QPalette.ColorRole.Window)
                return Theme.DARK if bg_color.lightness() < 128 else Theme.LIGHT
        return self._current_theme
    
    @property
    def colors(self) -> Dict[str, str]:
        """获取当前生效主题的色彩字典"""
        return self._themes[self.effective_theme]
    
    def set_theme(self, theme: Theme):
        """设置主题"""
        if theme != self._current_theme:
            self._current_theme = theme
            self._save_theme()
            effective = self.effective_theme
            self._apply_theme(effective)
            self.theme_changed.emit(effective)
    
    def toggle_theme(self):
        """切换主题（浅色 <-> 深色）"""
        effective = self.effective_theme
        new_theme = Theme.DARK if effective == Theme.LIGHT else Theme.LIGHT
        self.set_theme(new_theme)
    
    def get_color(self, key: str) -> str:
        """获取当前主题的颜色值"""
        return self.colors.get(key, "")
    
    def get_qss(self, template: str) -> str:
        """使用当前主题颜色格式化 QSS 模板"""
        return template.format(**self.colors)
    
    def apply_to_widget(self, widget: QWidget, qss_template: str):
        """将 QSS 模板应用到指定控件"""
        widget.setStyleSheet(self.get_qss(qss_template))
    
    def get_component_qss(self, component: str) -> str:
        """获取组件的 QSS 模板"""
        return COMPONENT_QSS_TEMPLATES.get(component, "")


# 组件 QSS 模板
COMPONENT_QSS_TEMPLATES = {
    "button_primary": """
        QPushButton {{
            background-color: {button_primary_bg};
            color: {button_primary_text};
            border: none;
            border-radius: {radius_md};
            padding: {space_sm} {space_md};
            font-size: {font_md};
            font-weight: {font_medium};
            font-family: {font_family};
        }}
        QPushButton:hover {{
            background-color: {button_primary_hover};
        }}
        QPushButton:pressed {{
            background-color: {button_primary_pressed};
        }}
        QPushButton:disabled {{
            background-color: {disabled_bg};
            color: {disabled_text};
        }}
        QPushButton:focus {{
            outline: none;
            border: 2px solid {border_focus};
        }}
    """,
    
    "button_secondary": """
        QPushButton {{
            background-color: {button_secondary_bg};
            color: {button_secondary_text};
            border: 1px solid {button_secondary_border};
            border-radius: {radius_md};
            padding: {space_sm} {space_md};
            font-size: {font_md};
            font-weight: {font_medium};
            font-family: {font_family};
        }}
        QPushButton:hover {{
            background-color: {secondary_hover};
        }}
        QPushButton:pressed {{
            background-color: {button_secondary_pressed};
        }}
        QPushButton:disabled {{
            background-color: {disabled_bg};
            color: {disabled_text};
            border-color: {disabled_border};
        }}
        QPushButton:focus {{
            outline: none;
            border: 2px solid {border_focus};
        }}
    """,
    
    "button_danger": """
        QPushButton {{
            background-color: {button_danger_bg};
            color: {button_danger_text};
            border: none;
            border-radius: {radius_md};
            padding: {space_sm} {space_md};
            font-size: {font_md};
            font-weight: {font_medium};
            font-family: {font_family};
        }}
        QPushButton:hover {{
            background-color: {button_danger_hover};
        }}
        QPushButton:pressed {{
            background-color: {button_danger_pressed};
        }}
        QPushButton:disabled {{
            background-color: {disabled_bg};
            color: {disabled_text};
        }}
        QPushButton:focus {{
            outline: none;
            border: 2px solid {border_focus};
        }}
    """,
    
    "icon_button": """
        QPushButton {{
            background-color: transparent;
            color: {text_secondary};
            border: none;
            border-radius: {radius_md};
            padding: {space_sm};
            font-size: {font_lg};
        }}
        QPushButton:hover {{
            background-color: {bg_hover};
            color: {text_primary};
        }}
        QPushButton:pressed {{
            background-color: {bg_pressed};
        }}
        QPushButton:disabled {{
            color: {disabled_text};
        }}
    """,
    
    "card": """
        QFrame {{
            background-color: {card_bg};
            border: 1px solid {card_border};
            border-radius: {radius_lg};
            background-clip: padding-box;
        }}
    """,
    
    "elevated_card": """
        QFrame {{
            background-color: {card_bg};
            border: 1px solid {card_border};
            border-radius: {radius_lg};
            background-clip: padding-box;
        }}
    """,
    
    "line_edit": """
        QLineEdit {{
            background-color: {input_bg};
            border: 1px solid {input_border};
            border-radius: {radius_md};
            padding: {space_sm} {space_md};
            font-size: {font_md};
            font-family: {font_family};
            color: {text_primary};
            selection-background-color: {primary_light};
        }}
        QLineEdit:hover {{
            border-color: {input_hover_border};
        }}
        QLineEdit:focus {{
            border-color: {input_focus_border};
            outline: none;
        }}
        QLineEdit:disabled {{
            background-color: {disabled_bg};
            border-color: {disabled_border};
            color: {disabled_text};
        }}
        QLineEdit::placeholder {{
            color: {input_placeholder};
        }}
    """,
    
    "search_box": """
        QLineEdit {{
            background-color: {input_bg};
            border: 1px solid {input_border};
            border-radius: {radius_full};
            padding: {space_sm} {space_md};
            padding-left: 36px;
            font-size: {font_md};
            font-family: {font_family};
            color: {text_primary};
            selection-background-color: {primary_light};
        }}
        QLineEdit:hover {{
            border-color: {input_hover_border};
        }}
        QLineEdit:focus {{
            border-color: {input_focus_border};
            outline: none;
        }}
        QLineEdit:disabled {{
            background-color: {disabled_bg};
            border-color: {disabled_border};
            color: {disabled_text};
        }}
        QLineEdit::placeholder {{
            color: {input_placeholder};
        }}
    """,
    
    "combo_box": """
        QComboBox {{
            background-color: {input_bg};
            border: 1px solid {input_border};
            border-radius: {radius_md};
            padding: {space_sm} {space_md};
            padding-right: 32px;
            font-size: {font_md};
            font-family: {font_family};
            color: {text_primary};
            selection-background-color: {primary_light};
        }}
        QComboBox:hover {{
            border-color: {input_hover_border};
        }}
        QComboBox:focus {{
            border-color: {input_focus_border};
            outline: none;
        }}
        QComboBox:disabled {{
            background-color: {disabled_bg};
            border-color: {disabled_border};
            color: {disabled_text};
        }}
        QComboBox::drop-down {{
            border: none;
            width: 28px;
        }}
        QComboBox::down-arrow {{
            image: none;
            border-left: 5px solid transparent;
            border-right: 5px solid transparent;
            border-top: 6px solid {text_tertiary};
            width: 0;
            height: 0;
        }}
        QComboBox::down-arrow:disabled {{
            border-top-color: {disabled_text};
        }}
        QComboBox QAbstractItemView {{
            background-color: {card_bg};
            border: 1px solid {card_border};
            border-radius: {radius_md};
            selection-background-color: {primary_light};
            selection-color: {primary};
            outline: none;
            padding: {space_xs};
        }}
        QComboBox QAbstractItemView::item {{
            padding: {space_sm} {space_md};
            border-radius: {radius_sm};
            min-height: 32px;
        }}
        QComboBox QAbstractItemView::item:hover {{
            background-color: {bg_hover};
        }}
        QComboBox QAbstractItemView::item:selected {{
            background-color: {primary_light};
            color: {primary};
        }}
    """,
    
    "checkbox": """
        QCheckBox {{
            font-size: {font_md};
            font-family: {font_family};
            color: {text_primary};
            spacing: {space_sm};
        }}
        QCheckBox::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {input_border};
            border-radius: {radius_sm};
            background-color: {input_bg};
        }}
        QCheckBox::indicator:hover {{
            border-color: {input_hover_border};
        }}
        QCheckBox::indicator:checked {{
            background-color: {primary};
            border-color: {primary};
            image: url(data:image/svg+xml;base64,PHN2ZyB3aWR0aD0iMTIiIGhlaWdodD0iOSIgdmlld0JveD0iMCAwIDEyIDkiIGZpbGw9Im5vbmUiIHhtbG5zPSJodHRwOi8vd3d3LnczLm9yZy8yMDAwL3N2ZyI+CjxwYXRoIGQ9Ik0xIDQuNUw0LjUgOEwxMSAxIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjIiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCIvPgo8L3N2Zz4K);
        }}
        QCheckBox::indicator:checked:hover {{
            background-color: {primary_hover};
            border-color: {primary_hover};
        }}
        QCheckBox::indicator:disabled {{
            background-color: {disabled_bg};
            border-color: {disabled_border};
        }}
        QCheckBox::indicator:checked:disabled {{
            background-color: {disabled_text};
            border-color: {disabled_text};
        }}
    """,
    
    "radio_button": """
        QRadioButton {{
            font-size: {font_md};
            font-family: {font_family};
            color: {text_primary};
            spacing: {space_sm};
        }}
        QRadioButton::indicator {{
            width: 18px;
            height: 18px;
            border: 2px solid {input_border};
            border-radius: {radius_full};
            background-color: {input_bg};
        }}
        QRadioButton::indicator:hover {{
            border-color: {input_hover_border};
        }}
        QRadioButton::indicator:checked {{
            border-color: {primary};
            background-color: {input_bg};
        }}
        QRadioButton::indicator:checked::after {{
            content: "";
            display: block;
            width: 8px;
            height: 8px;
            margin: 3px;
            border-radius: {radius_full};
            background-color: {primary};
        }}
        QRadioButton::indicator:disabled {{
            background-color: {disabled_bg};
            border-color: {disabled_border};
        }}
        QRadioButton::indicator:checked:disabled::after {{
            background-color: {disabled_text};
        }}
    """,
    
    "progress_bar": """
        QProgressBar {{
            background-color: {progress_bg};
            border: none;
            border-radius: {radius_full};
            height: 8px;
            text-align: center;
            font-size: {font_xs};
            color: {text_tertiary};
        }}
        QProgressBar::chunk {{
            background-color: {progress_bar};
            border-radius: {radius_full};
        }}
    """,
    
    "circular_progress": """
        QProgressBar {{
            background-color: transparent;
            border: none;
        }}
    """,
    
    "tooltip": """
        QToolTip {{
            background-color: {tooltip_bg};
            color: {tooltip_text};
            border: none;
            border-radius: {radius_sm};
            padding: {space_xs} {space_sm};
            font-size: {font_sm};
        }}
    """,
    
    "divider": """
        QFrame[divider="true"] {{
            border: none;
            border-top: 1px solid {divider};
        }}
    """,
    
    "badge": """
        QLabel[badge="true"] {{
            background-color: {badge_bg};
            color: {badge_text};
            border-radius: {radius_full};
            padding: 0 {space_sm};
            min-width: 18px;
            min-height: 18px;
            font-size: {font_xs};
            font-weight: {font_medium};
            font-family: {font_family};
            qproperty-alignment: AlignCenter;
        }}
    """,
    
    "drop_zone": """
        QFrame[dropzone="true"] {{
            background-color: {dropzone_bg};
            border: 2px dashed {dropzone_border};
            border-radius: {radius_lg};
            background-clip: padding-box;
        }}
        QFrame[dropzone="true"]:hover {{
            background-color: {dropzone_hover_bg};
            border-color: {dropzone_hover_border};
        }}
        QFrame[dropzone="true"][dragging="true"] {{
            background-color: {dropzone_active_bg};
            border-color: {dropzone_active_border};
            border-style: solid;
        }}
    """,
    
    "settings_panel": """
        QFrame[settingsPanel="true"] {{
            background-color: {sidebar_bg};
            border-left: 1px solid {sidebar_border};
        }}
        QFrame[settingsPanel="true"] QPushButton[tabButton="true"] {{
            background-color: transparent;
            color: {text_secondary};
            border: none;
            border-radius: {radius_md};
            padding: {space_sm} {space_md};
            text-align: left;
            font-size: {font_md};
            font-weight: {font_medium};
        }}
        QFrame[settingsPanel="true"] QPushButton[tabButton="true"]:hover {{
            background-color: {sidebar_item_hover};
            color: {text_primary};
        }}
        QFrame[settingsPanel="true"] QPushButton[tabButton="true"][active="true"] {{
            background-color: {sidebar_item_active};
            color: {sidebar_item_active_text};
        }}
    """,
    
    "toast": """
        QFrame[toast="true"] {{
            background-color: {toast_bg};
            color: {toast_text};
            border-radius: {radius_md};
            padding: {space_sm} {space_md};
        }}
        QFrame[toast="true"][type="success"] {{
            background-color: {toast_success_bg};
        }}
        QFrame[toast="true"][type="error"] {{
            background-color: {toast_error_bg};
        }}
        QFrame[toast="true"][type="warning"] {{
            background-color: {toast_warning_bg};
        }}
        QFrame[toast="true"][type="info"] {{
            background-color: {toast_info_bg};
        }}
    """,
    
    "file_item": """
        QFrame[fileItem="true"] {{
            background-color: {card_bg};
            border: 1px solid {card_border};
            border-radius: {radius_md};
            padding: {space_sm};
        }}
        QFrame[fileItem="true"]:hover {{
            background-color: {bg_hover};
            border-color: {border_primary};
        }}
    """,
}


def apply_theme(theme: Theme = Theme.SYSTEM):
    """便捷函数：应用主题"""
    manager = ThemeManager()
    manager.set_theme(theme)


def get_theme_manager() -> ThemeManager:
    """获取主题管理器单例"""
    return ThemeManager()