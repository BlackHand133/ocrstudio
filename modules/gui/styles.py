# modules/gui/styles.py
"""
Centralized styles and themes for OCR Tools Studio
"""

# Color palette
COLORS = {
    'primary': '#2196F3',        # Blue
    'primary_dark': '#1976D2',
    'primary_light': '#BBDEFB',
    'secondary': '#4CAF50',      # Green
    'secondary_dark': '#388E3C',
    'accent': '#FF9800',         # Orange
    'danger': '#F44336',         # Red
    'warning': '#FFC107',        # Yellow
    'background': '#FAFAFA',
    'surface': '#FFFFFF',
    'text_primary': '#212121',
    'text_secondary': '#757575',
    'border': '#E0E0E0',
    'divider': '#BDBDBD',
}

# Main window style
MAIN_WINDOW_STYLE = """
QMainWindow {
    background-color: #F5F5F5;
}

QMenuBar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E0E0E0;
    padding: 2px;
}

QMenuBar::item {
    padding: 6px 12px;
    background: transparent;
    border-radius: 4px;
}

QMenuBar::item:selected {
    background-color: #E3F2FD;
}

QMenu {
    background-color: #FFFFFF;
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    padding: 4px;
}

QMenu::item {
    padding: 8px 32px 8px 24px;
    border-radius: 4px;
}

QMenu::item:selected {
    background-color: #E3F2FD;
}

QMenu::separator {
    height: 1px;
    background-color: #E0E0E0;
    margin: 4px 8px;
}

QToolBar {
    background-color: #FFFFFF;
    border-bottom: 1px solid #E0E0E0;
    spacing: 4px;
    padding: 4px 8px;
}

QToolBar::separator {
    width: 1px;
    background-color: #E0E0E0;
    margin: 4px 8px;
}

QStatusBar {
    background-color: #FFFFFF;
    border-top: 1px solid #E0E0E0;
    padding: 4px;
}
"""

# Toolbar button styles
TOOLBAR_BUTTON_STYLE = """
QToolButton {
    background-color: transparent;
    border: none;
    border-radius: 4px;
    padding: 6px 12px;
    font-size: 13px;
    color: #424242;
}

QToolButton:hover {
    background-color: #E3F2FD;
}

QToolButton:pressed {
    background-color: #BBDEFB;
}

QToolButton::menu-indicator {
    image: none;
}
"""

# Primary action button (Save, etc.)
PRIMARY_BUTTON_STYLE = """
QPushButton {
    background-color: #2196F3;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #1976D2;
}

QPushButton:pressed {
    background-color: #1565C0;
}

QPushButton:disabled {
    background-color: #BDBDBD;
    color: #757575;
}
"""

# Secondary button style
SECONDARY_BUTTON_STYLE = """
QPushButton {
    background-color: #FFFFFF;
    color: #424242;
    border: 1px solid #E0E0E0;
    padding: 6px 12px;
    border-radius: 4px;
    font-size: 12px;
}

QPushButton:hover {
    background-color: #F5F5F5;
    border-color: #BDBDBD;
}

QPushButton:pressed {
    background-color: #EEEEEE;
}
"""

# Success button (for Save confirmation)
SUCCESS_BUTTON_STYLE = """
QPushButton {
    background-color: #4CAF50;
    color: white;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    font-weight: bold;
    font-size: 13px;
}

QPushButton:hover {
    background-color: #388E3C;
}

QPushButton:pressed {
    background-color: #2E7D32;
}
"""

# Dock widget style
DOCK_WIDGET_STYLE = """
QDockWidget {
    font-weight: bold;
    titlebar-close-icon: none;
    titlebar-normal-icon: none;
}

QDockWidget::title {
    background-color: #FAFAFA;
    padding: 8px;
    border-bottom: 1px solid #E0E0E0;
}
"""

# List widget style
LIST_WIDGET_STYLE = """
QListWidget {
    background-color: #FFFFFF;
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    padding: 4px;
    outline: none;
}

QListWidget::item {
    padding: 8px;
    border-radius: 4px;
    margin: 2px;
}

QListWidget::item:selected {
    background-color: #E3F2FD;
    color: #1976D2;
}

QListWidget::item:hover {
    background-color: #F5F5F5;
}
"""

# Table widget style
TABLE_WIDGET_STYLE = """
QTableWidget {
    background-color: #FFFFFF;
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    gridline-color: #F0F0F0;
    outline: none;
    font-size: 13px;
}

QTableWidget::item {
    padding: 8px 12px;
    min-height: 32px;
}

QTableWidget::item:selected {
    background-color: #E3F2FD;
    color: #1976D2;
}

QTableWidget::item:focus {
    background-color: #FFFFFF;
    border: 2px solid #2196F3;
}

QHeaderView::section {
    background-color: #FAFAFA;
    padding: 10px 8px;
    border: none;
    border-bottom: 2px solid #E0E0E0;
    font-weight: bold;
    font-size: 12px;
}

QTableWidget QLineEdit {
    background-color: #FFFFFF;
    border: 2px solid #2196F3;
    border-radius: 2px;
    padding: 6px 8px;
    font-size: 13px;
    min-height: 24px;
    selection-background-color: #BBDEFB;
}
"""

# Input field style
INPUT_STYLE = """
QLineEdit {
    background-color: #FFFFFF;
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    padding: 8px 12px;
    font-size: 13px;
}

QLineEdit:focus {
    border-color: #2196F3;
}

QLineEdit:disabled {
    background-color: #F5F5F5;
    color: #9E9E9E;
}
"""

# Combo box style
COMBO_BOX_STYLE = """
QComboBox {
    background-color: #FFFFFF;
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    padding: 6px 12px;
    min-width: 80px;
}

QComboBox:hover {
    border-color: #BDBDBD;
}

QComboBox:focus {
    border-color: #2196F3;
}

QComboBox::drop-down {
    border: none;
    width: 24px;
}

QComboBox QAbstractItemView {
    background-color: #FFFFFF;
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    selection-background-color: #E3F2FD;
}
"""

# Filter button style
FILTER_BUTTON_STYLE = """
QToolButton {
    background-color: #FFFFFF;
    border: 1px solid #E0E0E0;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 11px;
}

QToolButton:hover {
    background-color: #F5F5F5;
}

QToolButton:checked {
    background-color: #E3F2FD;
    border-color: #2196F3;
    color: #1976D2;
}
"""

# Mode indicator label style
MODE_INDICATOR_STYLE = """
QLabel {
    background-color: #E8F5E9;
    color: #2E7D32;
    padding: 4px 8px;
    border-radius: 4px;
    font-weight: bold;
    font-size: 11px;
}
"""

# Warning/Modified indicator
MODIFIED_INDICATOR_STYLE = """
QLabel {
    background-color: #FFF3E0;
    color: #E65100;
    padding: 4px 8px;
    border-radius: 4px;
    font-weight: bold;
    font-size: 11px;
}
"""

# Workspace info style
WORKSPACE_INFO_STYLE = """
QLabel {
    color: #616161;
    padding: 4px 8px;
    font-size: 12px;
}
"""

# Section header style
SECTION_HEADER_STYLE = """
QLabel {
    color: #757575;
    font-size: 11px;
    font-weight: bold;
    padding: 8px 4px 4px 4px;
    text-transform: uppercase;
}
"""

# Scrollbar style
SCROLLBAR_STYLE = """
QScrollBar:vertical {
    background-color: #F5F5F5;
    width: 8px;
    margin: 0;
}

QScrollBar::handle:vertical {
    background-color: #BDBDBD;
    border-radius: 4px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background-color: #9E9E9E;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}

QScrollBar:horizontal {
    background-color: #F5F5F5;
    height: 8px;
    margin: 0;
}

QScrollBar::handle:horizontal {
    background-color: #BDBDBD;
    border-radius: 4px;
    min-width: 20px;
}

QScrollBar::handle:horizontal:hover {
    background-color: #9E9E9E;
}

QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}
"""

def get_full_stylesheet():
    """Get complete stylesheet for the application"""
    return (
        MAIN_WINDOW_STYLE +
        DOCK_WIDGET_STYLE +
        LIST_WIDGET_STYLE +
        TABLE_WIDGET_STYLE +
        INPUT_STYLE +
        COMBO_BOX_STYLE +
        SCROLLBAR_STYLE
    )
