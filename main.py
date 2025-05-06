#!/usr/bin/env python3
"""
Inventory and Purchase Management System

A dual-interface application with both a Qt-based desktop UI and a Flask-based web interface
for small businesses to manage inventory, suppliers, and purchase orders.
"""

# This file is intentionally simple to serve as an entry point for both
# the web application (via gunicorn) and the desktop application
import os
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

# Handle database configuration before importing app
# If there's an issue with the PostgreSQL connection, use SQLite instead
try:
    if os.environ.get("DATABASE_URL") and "postgres" in os.environ.get("DATABASE_URL"):
        # Try to make a simple connection to PostgreSQL to verify it's working
        import psycopg2
        conn_string = os.environ.get("DATABASE_URL")
        logger.info(f"Testing PostgreSQL connection...")
        conn = psycopg2.connect(conn_string)
        conn.close()
        logger.info("PostgreSQL connection successful")
    else:
        logger.info("No PostgreSQL connection specified, will use SQLite")
except Exception as e:
    # If PostgreSQL connection fails, use SQLite as fallback
    logger.error(f"PostgreSQL connection failed: {str(e)}")
    logger.info("Falling back to SQLite database")
    # Clear DATABASE_URL to force SQLite
    if "DATABASE_URL" in os.environ:
        del os.environ["DATABASE_URL"]

# Now import the Flask app for Gunicorn and other web servers
try:
    from app import app
    logger.info("Flask app imported successfully")
except Exception as e:
    logger.error(f"Error importing Flask app: {str(e)}")
    raise

# If running this file directly, launch the desktop application
if __name__ == "__main__":
    import main_desktop
    main_desktop.main()
