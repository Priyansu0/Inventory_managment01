"""
Initialize SQLite database for development and testing.
This script will create all necessary tables in SQLite regardless of PostgreSQL configuration.
"""

import os
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

def initialize_sqlite():
    """Initialize SQLite database and create all tables."""
    try:
        # Save original DATABASE_URL if it exists
        original_db_url = None
        if 'DATABASE_URL' in os.environ:
            original_db_url = os.environ.pop('DATABASE_URL')
            logger.info("Temporarily removed PostgreSQL connection for SQLite initialization")
        
        # Set SQLite path
        sqlite_path = Path(__file__).parent / 'inventory.db'
        logger.info(f"Using SQLite database at {sqlite_path}")
        
        # Import necessary modules
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        # Import models
        from models import Base, Product, Supplier, PurchaseOrder, PurchaseItem
        
        # Create SQLite engine
        engine = create_engine(f"sqlite:///{sqlite_path}", echo=True)
        
        # Create all tables
        logger.info("Creating database tables in SQLite...")
        Base.metadata.create_all(engine)
        
        # Create a session to verify tables
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Try a simple query to verify the database is working
        from sqlalchemy import text
        session.execute(text("SELECT 1"))
        session.close()
        
        logger.info("SQLite database initialized successfully")
        
        # Restore original DATABASE_URL if it was saved
        if original_db_url:
            os.environ['DATABASE_URL'] = original_db_url
            logger.info("Restored original PostgreSQL connection")
        
        return True
    except Exception as e:
        logger.error(f"Failed to initialize SQLite database: {str(e)}", exc_info=True)
        return False

def create_indexes():
    """Create database indexes for better performance."""
    try:
        # Import necessary modules
        from sqlalchemy import create_engine, text
        from sqlalchemy.orm import sessionmaker
        
        # Set SQLite path
        sqlite_path = Path(__file__).parent / 'inventory.db'
        
        # Create SQLite engine
        engine = create_engine(f"sqlite:///{sqlite_path}")
        
        # Create a session
        Session = sessionmaker(bind=engine)
        session = Session()
        
        # Create indexes
        logger.info("Creating database indexes...")
        
        # Index for product search by SKU
        session.execute(text('CREATE INDEX IF NOT EXISTS idx_products_sku ON products (sku)'))
        
        # Index for filtering products by category
        session.execute(text('CREATE INDEX IF NOT EXISTS idx_products_category ON products (category)'))
        
        # Index for finding products with low stock
        session.execute(text(
            'CREATE INDEX IF NOT EXISTS idx_products_stock_level ON products (quantity_in_stock, reorder_level)'
        ))
        
        # Index for filtering purchase orders by status
        session.execute(text('CREATE INDEX IF NOT EXISTS idx_purchase_orders_status ON purchase_orders (status)'))
        
        # Index for purchase order date range queries
        session.execute(text('CREATE INDEX IF NOT EXISTS idx_purchase_orders_date ON purchase_orders (order_date)'))
        
        # Commit the changes
        session.commit()
        session.close()
        
        logger.info("Database indexes created successfully")
        return True
    except Exception as e:
        logger.error(f"Failed to create database indexes: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    logger.info("Starting SQLite database initialization...")
    
    if initialize_sqlite():
        create_indexes()
        logger.info("SQLite database setup completed successfully.")
    else:
        logger.error("SQLite database initialization failed.")
