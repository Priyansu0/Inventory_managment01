#!/usr/bin/env python3
"""
Inventory and Purchase Management System

A dual-interface application with both a Qt-based desktop UI and a Flask-based web interface
for small businesses to manage inventory, suppliers, and purchase orders.
"""

# This file is intentionally simple to serve as an entry point for both
# the web application (via gunicorn) and the desktop application

# Import the Flask app for Gunicorn and other web servers
from app import app

# If running this file directly, launch the desktop application
if __name__ == "__main__":
    import main_desktop
    main_desktop.main()
