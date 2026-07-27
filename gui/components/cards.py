"""
Card Components - Card, ElevatedCard
"""

from typing import Optional
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame
from PySide6.QtGui import QFont, QPainter, QColor, QBrush, QPen

from .theme import get_theme_manager, ThemeManager


class Card(QFrame):
    """基础卡片 - 白底/深色底，浅边框，圆角，轻微阴影"""
    
    def __init__(self, parent: QWidget = None, title: str = "", 
                 subtitle: str = "", extra: QWidget = None):
        super().__init__(parent)
        self._theme_manager = get_theme_manager()
        
        self.setObjectName("Card")
        self.setProperty("card", True)
        self.setFrameShape(QFrame.Shape.NoFrame)
        
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
        
        # Header
        if title or subtitle or extra:
            self._header = QWidget()
            self._header.setObjectName("CardHeader")
            header_layout = QHBoxLayout(self._header)
            header_layout.setContentsMargins(24, 20, 24, 12)
            header_layout.setSpacing(8)
            
            if title or subtitle:
                text_widget = QWidget()
                text_layout = QVBoxLayout(text_widget)
                text_layout.setContentsMargins(0, 0, 0, 0)
                text_layout.setSpacing(4)
                
                if title:
                    self._title_label = QLabel(title)
                    self._title_label.setObjectName("CardTitle")
                    font = QFont(self._theme_manager.get_color("font_family"))
                    font.setPointSize(int(self._theme_manager.get_color("font_lg").replace("px", "")))
                    font.setWeight(QFont.Weight.Medium)
                    self._title_label.setFont(font)
                    text_layout.addWidget(self._title_label)
                
                if subtitle:
                    self._subtitle_label = QLabel(subtitle)
                    self._subtitle_label.setObjectName("CardSubtitle")
                    font = QFont(self._theme_manager.get_color("font_family"))
                    font.setPointSize(int(self._theme_manager.get_color("font_sm").replace("px", "")))
                    self._subtitle_label.setFont(font)
                    text_layout.addWidget(self._subtitle_label)
                
                header_layout.addWidget(text_widget, 1)
            
            if extra:
                header_layout.addWidget(extra)
            
            self._layout.addWidget(self._header)
            
            # Divider
            self._divider = QFrame()
            self._divider.setFrameShape(QFrame.Shape.HLine)
            self._divider.setFrameShadow(QFrame.Shadow.Plain)
            self._divider.setFixedHeight(1)
            self._divider.setObjectName("CardDivider")
            self._layout.addWidget(self._divider)
        
        # Content
        self._content = QWidget()
        self._content.setObjectName("CardContent")
        self._content_layout = QVBoxLayout(self._content)
        self._content_layout.setContentsMargins(24, 16, 24, 24)
        self._content_layout.setSpacing(12)
        self._layout.addWidget(self._content, 1)
        
        self._apply_theme()
        self._theme_manager.theme_changed.connect(self._apply_theme)
    
    def _apply_theme(self, theme=None):
        tm = self._theme_manager
        self.setStyleSheet(f"""
            QFrame[card="true"] {{
                background-color: {tm.get_color("card_bg")};
                border: 1px solid {tm.get_color("card_border")};
                border-radius: {tm.get_color("radius_lg")};
            }}
            QFrame#CardDivider {{
                background-color: {tm.get_color("divider")};
                border: none;
            }}
            QLabel#CardTitle {{
                color: {tm.get_color("text_primary")};
            }}
            QLabel#CardSubtitle {{
                color: {tm.get_color("text_secondary")};
            }}
        """)
        self._divider.setStyleSheet(f"background-color: {tm.get_color('divider')}; border: none;")
    
    @property
    def content_layout(self) -> QVBoxLayout:
        """获取内容区域布局"""
        return self._content_layout
    
    def add_widget(self, widget: QWidget, stretch: int = 0):
        """添加组件到内容区"""
        self._content_layout.addWidget(widget, stretch)
    
    def add_layout(self, layout: QVBoxLayout | QHBoxLayout, stretch: int = 0):
        """添加布局到内容区"""
        self._content_layout.addLayout(layout, stretch)
    
    def set_title(self, title: str):
        """设置标题"""
        if hasattr(self, '_title_label'):
            self._title_label.setText(title)
        elif title:
            # 如果原来没有标题，需要重建 header（简化处理）
            pass
    
    def set_subtitle(self, subtitle: str):
        """设置副标题"""
        if hasattr(self, '_subtitle_label'):
            self._subtitle_label.setText(subtitle)


class ElevatedCard(Card):
    """高架卡片 - 更深阴影，用于悬浮面板、弹出层等"""
    
    def __init__(self, parent: QWidget = None, title: str = "", 
                 subtitle: str = "", extra: QWidget = None):
        super().__init__(parent, title, subtitle, extra)
        self.setProperty("elevated", True)
        self._apply_theme()
    
    def _apply_theme(self, theme=None):
        tm = self._theme_manager
        self.setStyleSheet(f"""
            QFrame[card="true"][elevated="true"] {{
                background-color: {tm.get_color("card_bg")};
                border: 1px solid {tm.get_color("card_border")};
                border-radius: {tm.get_color("radius_lg")};
            }}
            QFrame#CardDivider {{
                background-color: {tm.get_color("divider")};
                border: none;
            }}
            QLabel#CardTitle {{
                color: {tm.get_color("text_primary")};
            }}
            QLabel#CardSubtitle {{
                color: {tm.get_color("text_secondary")};
            }}
        """)


class CardGrid(QWidget):
    """卡片网格布局 - 自适应列数"""
    
    def __init__(self, parent: QWidget = None, spacing: int = 16, 
                 min_card_width: int = 280):
        super().__init__(parent)
        self._spacing = spacing
        self._min_card_width = min_card_width
        self._cards = []
        
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(spacing)
    
    def add_card(self, card: Card, row: int = -1, col: int = -1):
        """添加卡片到网格（简化版：垂直堆叠）"""
        self._cards.append(card)
        self._layout.addWidget(card)
    
    def clear(self):
        """清空所有卡片"""
        for card in self._cards:
            card.deleteLater()
        self._cards.clear()


class CardGroup(QWidget):
    """卡片组 - 垂直堆叠的卡片，带间距"""
    
    def __init__(self, parent: QWidget = None, spacing: int = 12):
        super().__init__(parent)
        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(spacing)
    
    def add_card(self, card: Card, stretch: int = 0):
        self._layout.addWidget(card, stretch)
    
    def add_stretch(self, stretch: int = 1):
        self._layout.addStretch(stretch)
    
    def clear(self):
        while self._layout.count():
            item = self._layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()