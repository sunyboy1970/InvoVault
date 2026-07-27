"""
Modern UI Component Library for Invoice Extractor GUI
基于 PySide6 的现代化组件库，支持浅色/深色主题切换
"""

from .theme import ThemeManager, Theme, LIGHT_THEME, DARK_THEME, apply_theme
from .buttons import PrimaryButton, SecondaryButton, IconButton, TextButton, ButtonGroup
from .cards import Card, ElevatedCard, CardGrid, CardGroup
from .inputs import LineEdit, SearchBox, TextArea, NumberInput
from .selectors import ComboBox, CheckBox, RadioGroup, CheckBoxGroup, RadioButton, Switch
from .progress import ProgressBar, CircularProgress, StepProgress, ProgressRing
from .notifications import Toast, Notification, ToastContainer, NotificationPanel, ToastType, ToastPosition, show_toast, show_notification
from .file_drop_zone import FileDropZone, FileItem, FileList
from .settings_panel import SettingsPanel, SettingsDialog
from .misc import Divider, Badge, Tooltip, Avatar, Skeleton, EmptyState

__all__ = [
    # Theme
    "ThemeManager",
    "Theme",
    "LIGHT_THEME",
    "DARK_THEME",
    "apply_theme",
    # Buttons
    "PrimaryButton",
    "SecondaryButton",
    "IconButton",
    "TextButton",
    "ButtonGroup",
    # Cards
    "Card",
    "ElevatedCard",
    "CardGrid",
    "CardGroup",
    # Inputs
    "LineEdit",
    "SearchBox",
    "TextArea",
    "NumberInput",
    # Selectors
    "ComboBox",
    "CheckBox",
    "RadioGroup",
    "CheckBoxGroup",
    "RadioButton",
    "Switch",
    # Progress
    "ProgressBar",
    "CircularProgress",
    "StepProgress",
    "ProgressRing",
    # Notifications
    "Toast",
    "Notification",
    "ToastContainer",
    "NotificationPanel",
    "ToastType",
    "ToastPosition",
    "show_toast",
    "show_notification",
    # File Drop
    "FileDropZone",
    "FileItem",
    "FileList",
    # Settings
    "SettingsPanel",
    "SettingsDialog",
    # Misc
    "Divider",
    "Badge",
    "Tooltip",
    "Avatar",
    "Skeleton",
    "EmptyState",
]

__version__ = "1.0.0"