#!/usr/bin/env python3
"""
Inventory and Purchase Management System

A comprehensive desktop application for small businesses to manage inventory,
suppliers, and purchase orders with QR code integration and reporting features.
"""

import sys
import os
import logging
from PyQt5.QtWidgets import QApplication
from PyQt5.QtCore import Qt
from gui.main_window import MainWindow
from database import init_db

# Set up logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("inventory_system.log"),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Initialize and run the application."""
    try:
        # Create database and tables if they don't exist
        init_db()
        
        # Initialize Qt Application
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setApplicationName("Inventory Manager")
        app = QApplication(sys.argv)
        
        # Create and show the main window
        window = MainWindow()
        window.show()
        
        # Execute the application
        sys.exit(app.exec_())
        
    except Exception as e:
        logger.error(f"Application error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
