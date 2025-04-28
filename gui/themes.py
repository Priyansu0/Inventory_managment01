"""
Theme management for the Inventory Management System.
"""

import os
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import QFile, QTextStream

logger = logging.getLogger(__name__)


class ThemeManager:
    """Manages application themes (light and dark modes)."""
    
    def __init__(self, parent=None):
        self.parent = parent
        self.current_theme = "light"
        
        # Ensure styles directory exists
        self.styles_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
                                    "resources", "styles")
        os.makedirs(self.styles_dir, exist_ok=True)
    
    def get_theme_path(self, theme_name):
        """Get the path to the theme's stylesheet file."""
        return os.path.join(self.styles_dir, f"{theme_name}.qss")
    
    def apply_theme(self, theme_name):
        """Apply the specified theme to the application."""
        theme_path = self.get_theme_path(theme_name)
        
        try:
            if not os.path.exists(theme_path):
                # If theme file doesn't exist, create default
                self.create_default_theme(theme_name)
            
            # Load and apply stylesheet
            style_file = QFile(theme_path)
            if style_file.open(QFile.ReadOnly | QFile.Text):
                stream = QTextStream(style_file)
                stylesheet = stream.readAll()
                QApplication.instance().setStyleSheet(stylesheet)
                self.current_theme = theme_name
                logger.info(f"Applied {theme_name} theme")
            else:
                logger.error(f"Failed to open stylesheet file: {theme_path}")
        
        except Exception as e:
            logger.error(f"Error applying theme {theme_name}: {str(e)}")
    
    def create_default_theme(self, theme_name):
        """Create a default theme stylesheet if one doesn't exist."""
        theme_path = self.get_theme_path(theme_name)
        
        try:
            # Ensure directory exists
            os.makedirs(os.path.dirname(theme_path), exist_ok=True)
            
            # Create basic stylesheet based on theme type
            if theme_name == "dark":
                stylesheet = self.get_default_dark_stylesheet()
            else:  # light theme
                stylesheet = self.get_default_light_stylesheet()
            
            # Write stylesheet to file
            with open(theme_path, 'w') as f:
                f.write(stylesheet)
            
            logger.info(f"Created default {theme_name} theme")
        
        except Exception as e:
            logger.error(f"Error creating default theme {theme_name}: {str(e)}")
    
    def get_default_light_stylesheet(self):
        """Get the default light stylesheet content."""
        return """/* Light Theme */

QMainWindow, QDialog, QWidget {
    background-color: #f5f5f5;
    color: #333333;
}

QTabWidget::pane {
    border: 1px solid #cccccc;
    background-color: #ffffff;
}

QTabBar::tab {
    background-color: #e0e0e0;
    border: 1px solid #cccccc;
    padding: 6px 12px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #ffffff;
    border-bottom-color: #ffffff;
}

QTableWidget {
    gridline-color: #d0d0d0;
    selection-background-color: #b5d3ff;
    selection-color: #000000;
    alternate-background-color: #f0f0f0;
}

QTableWidget::item:selected {
    background-color: #b5d3ff;
}

QHeaderView::section {
    background-color: #e0e0e0;
    padding: 4px;
    border: 1px solid #cccccc;
    font-weight: bold;
}

QPushButton {
    background-color: #e0e0e0;
    border: 1px solid #bbbbbb;
    padding: 5px 10px;
    border-radius: 3px;
}

QPushButton:hover {
    background-color: #d0d0d0;
}

QPushButton:pressed {
    background-color: #c0c0c0;
}

QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #ffffff;
    border: 1px solid #cccccc;
    padding: 3px;
    border-radius: 2px;
}

QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #85b7e8;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 15px;
    border-left: 1px solid #cccccc;
}

QGroupBox {
    border: 1px solid #cccccc;
    border-radius: 3px;
    margin-top: 1ex;
    padding-top: 10px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    padding: 0 3px;
}

QStatusBar {
    background-color: #e0e0e0;
    color: #333333;
}

QToolBar {
    background-color: #e0e0e0;
    border-bottom: 1px solid #cccccc;
}

QToolBar::separator {
    background-color: #cccccc;
    width: 1px;
    height: 20px;
    margin: 0 5px;
}

QLabel[objectName="status_label"] {
    padding: 5px;
    font-weight: bold;
}
"""
    
    def get_default_dark_stylesheet(self):
        """Get the default dark stylesheet content."""
        return """/* Dark Theme */

QMainWindow, QDialog, QWidget {
    background-color: #2d2d2d;
    color: #dddddd;
}

QTabWidget::pane {
    border: 1px solid #555555;
    background-color: #363636;
}

QTabBar::tab {
    background-color: #444444;
    border: 1px solid #555555;
    padding: 6px 12px;
    margin-right: 2px;
}

QTabBar::tab:selected {
    background-color: #363636;
    border-bottom-color: #363636;
}

QTableWidget {
    gridline-color: #555555;
    selection-background-color: #2a5285;
    selection-color: #ffffff;
    alternate-background-color: #3a3a3a;
    color: #dddddd;
}

QTableWidget::item:selected {
    background-color: #2a5285;
}

QHeaderView::section {
    background-color: #444444;
    padding: 4px;
    border: 1px solid #555555;
    font-weight: bold;
}

QPushButton {
    background-color: #444444;
    border: 1px solid #555555;
    padding: 5px 10px;
    border-radius: 3px;
    color: #dddddd;
}

QPushButton:hover {
    background-color: #505050;
}

QPushButton:pressed {
    background-color: #606060;
}

QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox {
    background-color: #424242;
    border: 1px solid #555555;
    padding: 3px;
    border-radius: 2px;
    color: #dddddd;
}

QLineEdit:focus, QTextEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus {
    border: 1px solid #2a5285;
}

QComboBox::drop-down {
    subcontrol-origin: padding;
    subcontrol-position: top right;
    width: 15px;
    border-left: 1px solid #555555;
}

QComboBox::item {
    background-color: #424242;
    color: #dddddd;
}

QComboBox::item:selected {
    background-color: #2a5285;
}

QGroupBox {
    border: 1px solid #555555;
    border-radius: 3px;
    margin-top: 1ex;
    padding-top: 10px;
}

QGroupBox::title {
    subcontrol-origin: margin;
    padding: 0 3px;
    color: #dddddd;
}

QStatusBar {
    background-color: #444444;
    color: #dddddd;
}

QToolBar {
    background-color: #444444;
    border-bottom: 1px solid #555555;
}

QToolBar::separator {
    background-color: #555555;
    width: 1px;
    height: 20px;
    margin: 0 5px;
}

QMenu {
    background-color: #424242;
    color: #dddddd;
}

QMenu::item:selected {
    background-color: #2a5285;
}

QLabel[objectName="status_label"] {
    padding: 5px;
    font-weight: bold;
}

QCheckBox {
    color: #dddddd;
}

QCheckBox::indicator {
    background-color: #424242;
    border: 1px solid #555555;
    width: 13px;
    height: 13px;
}

QCheckBox::indicator:checked {
    background-color: #2a5285;
}

QDateEdit {
    background-color: #424242;
    border: 1px solid #555555;
    color: #dddddd;
    border-radius: 2px;
    padding: 3px;
}

QCalendarWidget {
    background-color: #424242;
    color: #dddddd;
}

QCalendarWidget QToolButton {
    color: #dddddd;
    background-color: #444444;
}

QCalendarWidget QMenu {
    background-color: #424242;
    color: #dddddd;
}

QCalendarWidget QSpinBox {
    background-color: #424242;
    color: #dddddd;
    border: 1px solid #555555;
}

QMessageBox {
    background-color: #2d2d2d;
    color: #dddddd;
}

QMessageBox QPushButton {
    min-width: 70px;
}
"""
