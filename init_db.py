"""
Database initialization script.
Run this script to initialize the database and create all necessary tables.
"""

import os
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

def init_database():
    """Initialize the database and create tables."""
    try:
        # Import the Flask app
        import os
        
        # Force SQLite for initialization
        if 'DATABASE_URL' in os.environ:
            db_url = os.environ.pop('DATABASE_URL')
            logger.info(f"Temporarily using SQLite instead of PostgreSQL for initialization")
        else:
            db_url = None
        
        # Import the Flask app with SQLite configuration
        from app import app, db
        
        # Import all models to ensure they're registered with SQLAlchemy
        from models import Product, Supplier, PurchaseOrder, PurchaseItem
        
        # Create database tables
        with app.app_context():
            logger.info(f"Creating database tables in {app.config['SQLALCHEMY_DATABASE_URI']}")
            db.create_all()
            logger.info("Database tables created successfully")
        
        # Restore PostgreSQL connection if it was removed
        if db_url:
            os.environ['DATABASE_URL'] = db_url
        
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {str(e)}", exc_info=True)
        return False

def create_indexes():
    """Create database indexes for performance optimization."""
    try:
        # Import Flask app and run commands within app context
        from app import app, db
        
        with app.app_context():
            # Execute raw SQL commands using SQLAlchemy engine
            logger.info("Creating database indexes")
            
            # Index for product search by SKU (frequently used for lookups)
            db.session.execute(db.text('CREATE INDEX IF NOT EXISTS idx_products_sku ON products (sku)'))
            
            # Index for filtering products by category
            db.session.execute(db.text('CREATE INDEX IF NOT EXISTS idx_products_category ON products (category)'))
            
            # Index for finding products with low stock
            db.session.execute(db.text(
                'CREATE INDEX IF NOT EXISTS idx_products_stock_level ON products (quantity_in_stock, reorder_level)'
            ))
            
            # Index for filtering purchase orders by status
            db.session.execute(db.text('CREATE INDEX IF NOT EXISTS idx_purchase_orders_status ON purchase_orders (status)'))
            
            # Index for purchase order date range queries
            db.session.execute(db.text('CREATE INDEX IF NOT EXISTS idx_purchase_orders_date ON purchase_orders (order_date)'))
            
            # Commit the changes
            db.session.commit()
            logger.info("Database indexes created successfully")
            
        return True
    except Exception as e:
        logger.error(f"Failed to create database indexes: {str(e)}", exc_info=True)
        return False

def test_connection():
    """Test database connection."""
    try:
        # Import Flask app and run commands within app context
        from app import app, db
        
        with app.app_context():
            # Execute a simple query to test the connection
            db.session.execute(db.text('SELECT 1'))
            logger.info("Database connection test successful")
        
        return True
    except Exception as e:
        logger.error(f"Database connection test failed: {str(e)}", exc_info=True)
        return False

if __name__ == "__main__":
    # Run initialization
    logger.info("Starting database initialization")
    
    if test_connection():
        init_successful = init_database()
        
        if init_successful:
            # Create indexes for performance optimization
            create_indexes()
            logger.info("Database initialization completed successfully")
        else:
            logger.error("Database initialization failed")
    else:
        logger.error("Database connection test failed. Cannot initialize database.")
