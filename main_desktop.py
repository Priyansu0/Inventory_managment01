#!/usr/bin/env python3
"""
Inventory and Purchase Management System

A comprehensive desktop application for small businesses to manage inventory,
suppliers, and purchase orders with QR code integration and reporting features.

This file also includes a Flask web application import to allow a dual interface approach.
"""

import sys
import os
import logging
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

# Import the Flask app for Gunicorn
try:
    from app import app
except ImportError:
    logger.warning("Flask web application (app.py) not found")
    app = None

def check_gui_available():
    """Check if GUI can be used in current environment."""
    # Check for DISPLAY environment variable (Linux/Unix)
    if os.environ.get('DISPLAY') is None and sys.platform.startswith('linux'):
        return False
    
    # Check if running in a headless environment
    if os.environ.get('HEADLESS') == '1':
        return False
    
    return True

def main():
    """Initialize and run the application."""
    try:
        # Create database and tables if they don't exist
        init_db()
        
        # Check if GUI is available
        if check_gui_available():
            # Import PyQt5 components only if GUI is available
            try:
                from PyQt5.QtWidgets import QApplication
                from PyQt5.QtCore import Qt
                from gui.main_window import MainWindow
                
                # Initialize Qt Application with platform plugin specification
                os.environ['QT_QPA_PLATFORM'] = 'offscreen'  # Use offscreen as fallback
                QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
                QApplication.setApplicationName("Inventory Manager")
                app = QApplication(sys.argv)
                
                # Create and show the main window
                window = MainWindow()
                window.show()
                
                # Execute the application
                sys.exit(app.exec_())
            except Exception as e:
                logger.error(f"Failed to start GUI: {str(e)}", exc_info=True)
                print(f"Could not start GUI application: {str(e)}")
                print("Try running with environment variable QT_QPA_PLATFORM=offscreen")
        else:
            logger.info("Running in headless mode, GUI disabled")
            print("GUI disabled (running in headless mode)")
            print("Web interface should be available at http://localhost:5000")
            
            # Keep the script running to maintain the web server
            if app is not None:
                # This shouldn't be reached in normal circumstances as gunicorn
                # would be managing the Flask app separately
                from app import app as flask_app
                flask_app.run(host='0.0.0.0', port=5000)
            else:
                # Just keep the process alive
                import time
                while True:
                    time.sleep(60)
        
    except Exception as e:
        logger.error(f"Application error: {str(e)}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
