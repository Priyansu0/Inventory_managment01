"""
Database configuration and connection management for the Inventory System.
"""

import os
import logging
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session

logger = logging.getLogger(__name__)

# Database configuration
# Check if PostgreSQL connection is available, otherwise fall back to SQLite
if os.environ.get('DATABASE_URL'):
    # PostgreSQL connection
    DB_URL = os.environ.get('DATABASE_URL')
    logger.info("Using PostgreSQL database")
    
    # Configure connection pool for PostgreSQL
    engine_args = {
        "pool_pre_ping": True,  # Check connection before using it
        "pool_recycle": 300,    # Recycle connections after 5 minutes
        "pool_size": 10,        # Maximum number of connections to keep
        "max_overflow": 15,     # Maximum number of connections to create beyond pool_size
        "pool_timeout": 30,     # Seconds to wait before giving up on getting a connection
        "echo": False           # Set to True for debug logging
    }
else:
    # SQLite fallback for local development
    DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory.db')
    DB_URL = f"sqlite:///{DB_PATH}"
    logger.info(f"Using SQLite database at {DB_PATH}")
    engine_args = {"connect_args": {"check_same_thread": False}}

# Create the base class for declarative models
Base = declarative_base()

# Create engine and session
engine = create_engine(DB_URL, **engine_args)
session_factory = sessionmaker(bind=engine)
Session = scoped_session(session_factory)


def init_db():
    """Initialize the database, creating tables if they don't exist."""
    try:
        # Import models to ensure they're registered with the Base
        import models
        
        # Create all tables
        Base.metadata.create_all(engine)
        logger.info("Database initialization successful")
    except Exception as e:
        logger.error(f"Database initialization error: {str(e)}", exc_info=True)
        raise


def get_session():
    """Get a database session."""
    session = Session()
    try:
        return session
    except Exception:
        session.rollback()
        raise
    finally:
        Session.remove()
