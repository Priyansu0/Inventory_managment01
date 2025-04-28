"""
Main application window for the Inventory Management System.
"""

import os
import logging
from PyQt5.QtWidgets import (QMainWindow, QTabWidget, QStatusBar, QToolBar, 
                            QAction, QMessageBox, QVBoxLayout, QWidget)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

from gui.inventory_tab import InventoryTab
from gui.purchase_tab import PurchaseTab
from gui.supplier_tab import SupplierTab
from gui.dashboard_tab import DashboardTab
from gui.themes import ThemeManager

logger = logging.getLogger(__name__)


class MainWindow(QMainWindow):
    """Main application window with tab navigation and toolbar."""
    
    def __init__(self):
        super().__init__()
        self.theme_manager = ThemeManager(self)
        
        self.setWindowTitle("Inventory & Purchase Management System")
        self.setGeometry(100, 100, 1200, 800)
        self.setMinimumSize(800, 600)
        
        # Set up the central widget and main layout
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)
        self.layout.setContentsMargins(5, 5, 5, 5)
        
        # Create the tab widget and set up tabs
        self.tabs = QTabWidget()
        self.tabs.setTabPosition(QTabWidget.North)
        self.tabs.setDocumentMode(True)
        
        # Create the main tabs
        self.dashboard_tab = DashboardTab()
        self.inventory_tab = InventoryTab()
        self.purchase_tab = PurchaseTab()
        self.supplier_tab = SupplierTab()
        
        # Add tabs to the tab widget
        self.tabs.addTab(self.dashboard_tab, "Dashboard")
        self.tabs.addTab(self.inventory_tab, "Inventory")
        self.tabs.addTab(self.purchase_tab, "Purchase Orders")
        self.tabs.addTab(self.supplier_tab, "Suppliers")
        
        # Add the tab widget to the main layout
        self.layout.addWidget(self.tabs)
        
        # Set up the status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")
        
        # Create toolbar
        self.create_toolbar()
        
        # Apply default theme
        self.theme_manager.apply_theme("light")
        
        logger.info("Main window initialized")

    def create_toolbar(self):
        """Create the main toolbar with actions."""
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)
        
        # Create actions
        theme_action = QAction("Toggle Theme", self)
        theme_action.setStatusTip("Switch between light and dark themes")
        theme_action.triggered.connect(self.toggle_theme)
        
        refresh_action = QAction("Refresh", self)
        refresh_action.setStatusTip("Refresh data")
        refresh_action.triggered.connect(self.refresh_data)
        
        export_action = QAction("Export", self)
        export_action.setStatusTip("Export data")
        export_action.triggered.connect(self.export_data)
        
        help_action = QAction("Help", self)
        help_action.setStatusTip("Show help")
        help_action.triggered.connect(self.show_help)
        
        # Add actions to toolbar
        toolbar.addAction(theme_action)
        toolbar.addAction(refresh_action)
        toolbar.addAction(export_action)
        toolbar.addAction(help_action)

    def toggle_theme(self):
        """Toggle between light and dark themes."""
        if self.theme_manager.current_theme == "light":
            self.theme_manager.apply_theme("dark")
        else:
            self.theme_manager.apply_theme("light")
        self.status_bar.showMessage(f"Theme changed to {self.theme_manager.current_theme}")

    def refresh_data(self):
        """Refresh all data in the current tab."""
        current_tab = self.tabs.currentWidget()
        if hasattr(current_tab, 'refresh_data'):
            current_tab.refresh_data()
        self.status_bar.showMessage("Data refreshed")

    def export_data(self):
        """Export data from the current tab."""
        current_tab = self.tabs.currentWidget()
        if hasattr(current_tab, 'export_data'):
            current_tab.export_data()
        else:
            self.status_bar.showMessage("Export not available for this section")

    def show_help(self):
        """Show help information."""
        help_text = """
        <h2>Inventory & Purchase Management System Help</h2>
        
        <h3>Dashboard</h3>
        <p>View overall business metrics and alerts.</p>
        
        <h3>Inventory</h3>
        <p>Add, edit, and delete products. Monitor stock levels and set reorder points.</p>
        
        <h3>Purchase Orders</h3>
        <p>Create purchase orders, manage orders, and update inventory upon receipt.</p>
        
        <h3>Suppliers</h3>
        <p>Manage supplier information and link suppliers to products.</p>
        
        <h3>QR Codes</h3>
        <p>Generate and scan QR codes for quick product and order lookup.</p>
        
        <h3>Export</h3>
        <p>Export data to Excel or CSV formats for external use.</p>
        """
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Help")
        msg_box.setTextFormat(Qt.RichText)
        msg_box.setText(help_text)
        msg_box.setIcon(QMessageBox.Information)
        msg_box.exec_()
        
    def closeEvent(self, event):
        """Handle the window close event."""
        reply = QMessageBox.question(
            self, 
            "Confirm Exit",
            "Are you sure you want to exit?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            logger.info("Application closed by user")
            event.accept()
        else:
            event.ignore()
