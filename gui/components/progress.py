"""
Progress Components - ProgressBar, CircularProgress
"""

from typing import Optional
from PySide6.QtCore import Qt, Signal, QTimer, QPropertyAnimation, QEasingCurve, QRect, QPoint
from PySide6.QtWidgets import (QProgressBar, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QFrame, QSizePolicy)
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QFont, QPainterPath

from .theme import get_theme_manager, ThemeManager, COMPONENT_QSS_TEMPLATES


class ProgressBar(QProgressBar):
    """增强型进度条 - 支持多种样式、动画、标签"""
    
    def __init__(self, parent: QWidget = None, value: int = 0, maximum: int = 100,
                 show_text: bool = True, format: str = "%p%", 
                 animated: bool = False, height: int = 8):
        super().__init__(parent)
        self._theme_manager = get_theme_manager()
        
        self._animated = animated
        self._animation = None
        
        self.setRange(0, maximum)
        self.setValue(value)
        self.setTextVisible(show_text)
        self.setFormat(format)
        self.setFixedHeight(height)
        
        # 隐藏默认文本（我们自定义绘制或使用内置）
        if not show_text:
            self.setFormat("")
        
        self._setup_ui()
        self._apply_theme()
        self._theme_manager.theme_changed.connect(self._apply_theme)
    
    def _setup_ui(self):
        """设置 UI"""
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        if self._animated:
            self._start_animation()
    
    def _start_animation(self):
        """启动动画（用于不确定进度）"""
        if self._animation:
            self._animation.stop()
        
        self._animation = QPropertyAnimation(self, b"value")
        self._animation.setDuration(1000)
        self._animation.setStartValue(0)
        self._animation.setEndValue(self.maximum())
        self._animation.setEasingCurve(QEasingCurve.Type.InOutQuad)
        self._animation.setLoopCount(-1)  # 无限循环
        self._animation.start()
    
    def set_animated(self, animated: bool):
        """设置是否动画"""
        self._animated = animated
        if animated:
            self._start_animation()
        elif self._animation:
            self._animation.stop()
            self._animation = None
    
    def set_range(self, minimum: int, maximum: int):
        """设置范围"""
        self.setRange(minimum, maximum)
        if self._animated:
            self._start_animation()
    
    def _apply_theme(self, theme=None):
        """应用主题"""
        tm = self._theme_manager
        qss = tm.get_qss(COMPONENT_QSS_TEMPLATES["progress_bar"])
        self.setStyleSheet(qss)
    
    def set_format(self, format: str):
        """设置格式字符串"""
        self.setFormat(format)
    
    def increment(self, step: int = 1):
        """增加进度"""
        self.setValue(min(self.value() + step, self.maximum()))
    
    def reset(self):
        """重置进度"""
        self.setValue(0)
        if self._animated:
            self._start_animation()


class CircularProgress(QWidget):
    """圆形进度条 - 支持确定/不确定模式、多种尺寸"""
    
    value_changed = Signal(int)
    
    def __init__(self, parent: QWidget = None, value: int = 0, maximum: int = 100,
                 size: int = 48, stroke_width: int = 4, 
                 show_text: bool = True, indeterminate: bool = False,
                 clockwise: bool = True, start_angle: int = -90):
        super().__init__(parent)
        self._theme_manager = get_theme_manager()
        
        self._value = value
        self._maximum = maximum
        self._size = size
        self._stroke_width = stroke_width
        self._show_text = show_text
        self._indeterminate = indeterminate
        self._clockwise = clockwise
        self._start_angle = start_angle
        
        self._animation = None
        self._animation_angle = 0
        
        self.setFixedSize(size, size)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        
        self._setup_ui()
        self._apply_theme()
        self._theme_manager.theme_changed.connect(self._apply_theme)
        
        if self._indeterminate:
            self._start_indeterminate_animation()
    
    def _setup_ui(self):
        """设置 UI"""
        pass
    
    def _start_indeterminate_animation(self):
        """启动不确定模式动画"""
        self._animation = QPropertyAnimation(self, b"_animation_angle")
        self._animation.setDuration(1000)
        self._animation.setStartValue(0)
        self._animation.setEndValue(360)
        self._animation.setEasingCurve(QEasingCurve.Type.Linear)
        self._animation.setLoopCount(-1)
        self._animation.valueChanged.connect(self._on_animation_value_changed)
        self._animation.start()
    
    def _on_animation_value_changed(self, value):
        """动画值变化"""
        self._animation_angle = value
        self.update()
    
    def paintEvent(self, event):
        """绘制圆形进度条"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        colors = self._theme_manager.colors
        rect = self.rect().adjusted(self._stroke_width // 2, self._stroke_width // 2,
                                     -self._stroke_width // 2, -self._stroke_width // 2)
        
        # 背景圆环
        pen_bg = QPen(QColor(colors["progress_bg"]), self._stroke_width)
        pen_bg.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_bg)
        painter.drawEllipse(rect)
        
        # 进度圆环
        if self._indeterminate:
            # 不确定模式：绘制一段弧
            pen_fg = QPen(QColor(colors["progress_bar"]), self._stroke_width)
            pen_fg.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_fg)
            
            # 绘制 90 度的弧，跟随动画角度
            sweep = 90
            start = self._animation_angle + self._start_angle
            painter.drawArc(rect, start * 16, sweep * 16)
        else:
            # 确定模式：根据进度绘制
            progress = self._value / self._maximum if self._maximum > 0 else 0
            sweep = int(360 * progress)
            
            pen_fg = QPen(QColor(colors["progress_bar"]), self._stroke_width)
            pen_fg.setCapStyle(Qt.PenCapStyle.RoundCap)
            painter.setPen(pen_fg)
            
            painter.drawArc(rect, self._start_angle * 16, sweep * 16)
        
        # 中心文本
        if self._show_text and not self._indeterminate:
            painter.setPen(QColor(colors["text_primary"]))
            font = QFont(colors["font_family"])
            font.setPointSize(max(8, self._size // 5))
            font.setWeight(QFont.Weight.Medium)
            painter.setFont(font)
            
            text = f"{self._value}%" if self._maximum == 100 else f"{self._value}/{self._maximum}"
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
    
    def _apply_theme(self, theme=None):
        """应用主题 - 触发重绘"""
        self.update()
    
    @property
    def value(self) -> int:
        return self._value
    
    @value.setter
    def value(self, val: int):
        self._value = max(0, min(val, self._maximum))
        self.value_changed.emit(self._value)
        self.update()
    
    @property
    def maximum(self) -> int:
        return self._maximum
    
    @maximum.setter
    def maximum(self, val: int):
        self._maximum = max(1, val)
        self.update()
    
    def set_value(self, value: int):
        """设置值"""
        self.value = value
    
    def set_maximum(self, maximum: int):
        """设置最大值"""
        self.maximum = maximum
    
    def set_indeterminate(self, indeterminate: bool):
        """设置不确定模式"""
        if self._indeterminate != indeterminate:
            self._indeterminate = indeterminate
            if indeterminate:
                self._start_indeterminate_animation()
            elif self._animation:
                self._animation.stop()
                self._animation = None
            self.update()
    
    def set_size(self, size: int):
        """设置尺寸"""
        self._size = size
        self.setFixedSize(size, size)
        self.update()
    
    def set_stroke_width(self, width: int):
        """设置线宽"""
        self._stroke_width = width
        self.update()
    
    def increment(self, step: int = 1):
        """增加进度"""
        self.value = self._value + step
    
    def reset(self):
        """重置"""
        self.value = 0


class StepProgress(QWidget):
    """步骤进度条 - 显示多步骤流程进度"""
    
    step_changed = Signal(int)
    
    def __init__(self, parent: QWidget = None, steps: List[str] = None,
                 current_step: int = 0, orientation: Qt.Orientation = Qt.Orientation.Horizontal,
                 show_numbers: bool = True, clickable: bool = False):
        super().__init__(parent)
        self._theme_manager = get_theme_manager()
        
        self._steps = steps or []
        self._current_step = current_step
        self._orientation = orientation
        self._show_numbers = show_numbers
        self._clickable = clickable
        self._step_widgets = []
        
        self._setup_ui()
        self._apply_theme()
        self._theme_manager.theme_changed.connect(self._apply_theme)
        
        if self._steps:
            self.set_steps(self._steps)
    
    def _setup_ui(self):
        """设置 UI"""
        if self._orientation == Qt.Orientation.Horizontal:
            self._layout = QHBoxLayout(self)
        else:
            self._layout = QVBoxLayout(self)
        
        self._layout.setContentsMargins(0, 0, 0, 0)
        self._layout.setSpacing(0)
    
    def set_steps(self, steps: List[str]):
        """设置步骤"""
        self._steps = steps
        self._rebuild()
    
    def _rebuild(self):
        """重建 UI"""
        # 清空现有
        for widget in self._step_widgets:
            widget.deleteLater()
        self._step_widgets.clear()
        
        # 重新创建
        for i, step_text in enumerate(self._steps):
            step_widget = self._create_step_widget(i, step_text)
            self._step_widgets.append(step_widget)
            
            if self._orientation == Qt.Orientation.Horizontal:
                self._layout.addWidget(step_widget, 1)
            else:
                self._layout.addWidget(step_widget)
            
            # 添加连接线（除了最后一个）
            if i < len(self._steps) - 1:
                line = self._create_line()
                self._layout.addWidget(line)
    
    def _create_step_widget(self, index: int, text: str) -> QWidget:
        """创建步骤组件"""
        widget = QWidget()
        widget.setCursor(Qt.CursorShape.PointingHandCursor if self._clickable else Qt.CursorShape.ArrowCursor)
        
        if self._orientation == Qt.Orientation.Horizontal:
            layout = QVBoxLayout(widget)
        else:
            layout = QHBoxLayout(widget)
        
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)
        
        # 圆圈
        circle = QLabel()
        circle.setFixedSize(28, 28)
        circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
        circle.setProperty("stepIndex", index)
        circle.setProperty("stepState", self._get_step_state(index))
        
        if self._show_numbers:
            circle.setText(str(index + 1))
        else:
            circle.setText("●")
        
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(12)
        font.setWeight(QFont.Weight.Medium)
        circle.setFont(font)
        
        layout.addWidget(circle, 0, Qt.AlignmentFlag.AlignCenter if self._orientation == Qt.Orientation.Horizontal else Qt.AlignmentFlag.AlignLeft)
        
        # 标签
        label = QLabel(text)
        label.setWordWrap(True)
        label.setAlignment(Qt.AlignmentFlag.AlignCenter if self._orientation == Qt.Orientation.Horizontal else Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        label.setProperty("stepIndex", index)
        label.setProperty("stepState", self._get_step_state(index))
        
        font = QFont(self._theme_manager.get_color("font_family"))
        font.setPointSize(int(self._theme_manager.get_color("font_sm").replace("px", "")))
        label.setFont(font)
        
        layout.addWidget(label)
        
        if self._clickable:
            widget.mousePressEvent = lambda e, idx=index: self._on_step_clicked(idx)
        
        return widget
    
    def _create_line(self) -> QWidget:
        """创建连接线"""
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine if self._orientation == Qt.Orientation.Horizontal else QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Plain)
        line.setFixedWidth(2) if self._orientation == Qt.Orientation.Horizontal else line.setFixedHeight(2)
        line.setProperty("stepLine", True)
        return line
    
    def _get_step_state(self, index: int) -> str:
        """获取步骤状态"""
        if index < self._current_step:
            return "completed"
        elif index == self._current_step:
            return "active"
        else:
            return "pending"
    
    def _on_step_clicked(self, index: int):
        """步骤点击"""
        if index <= self._current_step + 1:  # 只能点击当前或下一步
            self.set_current_step(index)
    
    def _apply_theme(self, theme=None):
        """应用主题"""
        tm = self._theme_manager
        colors = tm.colors
        
        # 步骤圆圈样式
        self.setStyleSheet(f"""
            QLabel[stepState="pending"] {{
                color: {colors["text_tertiary"]};
                border: 2px solid {colors["border_primary"]};
                border-radius: 14px;
                background-color: {colors["bg_primary"]};
            }}
            QLabel[stepState="active"] {{
                color: {colors["primary_text"]};
                border: 2px solid {colors["primary"]};
                border-radius: 14px;
                background-color: {colors["primary"]};
            }}
            QLabel[stepState="completed"] {{
                color: {colors["primary_text"]};
                border: 2px solid {colors["success"]};
                border-radius: 14px;
                background-color: {colors["success"]};
            }}
            QLabel[stepIndex] {{
                font-family: {colors["font_family"]};
            }}
            QFrame[stepLine="true"] {{
                background-color: {colors["border_primary"]};
            }}
        """)
        
        # 更新每个步骤的状态
        for i, widget in enumerate(self._step_widgets):
            circle = widget.findChild(QLabel, "", Qt.FindChildOption.FindDirectChildrenOnly)
            if circle:
                circle.setProperty("stepState", self._get_step_state(i))
                circle.style().unpolish(circle)
                circle.style().polish(circle)
            
            for label in widget.findChildren(QLabel):
                if label.property("stepIndex") is not None and label != circle:
                    label.setProperty("stepState", self._get_step_state(i))
                    label.style().unpolish(label)
                    label.style().polish(label)
            
            for line in widget.findChildren(QFrame):
                if line.property("stepLine"):
                    if i < self._current_step:
                        line.setStyleSheet(f"background-color: {colors['success']};")
                    else:
                        line.setStyleSheet(f"background-color: {colors['border_primary']};")
    
    def set_current_step(self, step: int):
        """设置当前步骤"""
        if 0 <= step < len(self._steps):
            self._current_step = step
            self._apply_theme()
            self.step_changed.emit(step)
    
    def next_step(self):
        """下一步"""
        if self._current_step < len(self._steps) - 1:
            self.set_current_step(self._current_step + 1)
    
    def prev_step(self):
        """上一步"""
        if self._current_step > 0:
            self.set_current_step(self._current_step - 1)
    
    def complete(self):
        """完成所有步骤"""
        self.set_current_step(len(self._steps) - 1)
    
    def reset(self):
        """重置到第一步"""
        self.set_current_step(0)
    
    @property
    def current_step(self) -> int:
        return self._current_step
    
    @property
    def total_steps(self) -> int:
        return len(self._steps)


class ProgressRing(QWidget):
    """进度环 - 紧凑型圆形进度，用于卡片、列表项等"""
    
    def __init__(self, parent: QWidget = None, value: int = 0, maximum: int = 100,
                 size: int = 32, stroke_width: int = 3, 
                 show_percentage: bool = False):
        super().__init__(parent)
        self._theme_manager = get_theme_manager()
        
        self._value = value
        self._maximum = maximum
        self._size = size
        self._stroke_width = stroke_width
        self._show_percentage = show_percentage
        
        self.setFixedSize(size, size)
        
        self._apply_theme()
        self._theme_manager.theme_changed.connect(self._apply_theme)
    
    def _apply_theme(self, theme=None):
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        colors = self._theme_manager.colors
        rect = self.rect().adjusted(self._stroke_width // 2, self._stroke_width // 2,
                                     -self._stroke_width // 2, -self._stroke_width // 2)
        
        # 背景
        pen_bg = QPen(QColor(colors["progress_bg"]), self._stroke_width)
        pen_bg.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_bg)
        painter.drawEllipse(rect)
        
        # 进度
        progress = self._value / self._maximum if self._maximum > 0 else 0
        sweep = int(360 * progress)
        
        pen_fg = QPen(QColor(colors["progress_bar"]), self._stroke_width)
        pen_fg.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen_fg)
        
        painter.drawArc(rect, -90 * 16, sweep * 16)
        
        # 百分比文本
        if self._show_percentage:
            painter.setPen(QColor(colors["text_primary"]))
            font = QFont(colors["font_family"])
            font.setPointSize(max(7, self._size // 5))
            font.setWeight(QFont.Weight.Medium)
            painter.setFont(font)
            
            text = f"{int(progress * 100)}%"
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
    
    def set_value(self, value: int):
        self._value = max(0, min(value, self._maximum))
        self.update()
    
    def set_maximum(self, maximum: int):
        self._maximum = max(1, maximum)
        self.update()
    
    @property
    def value(self) -> int:
        return self._value
    
    @property
    def maximum(self) -> int:
        return self._maximum


# 导入缺失的类型
from typing import List