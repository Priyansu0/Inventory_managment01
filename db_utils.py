"""
Database utilities for the Inventory Management System.
Provides functions for common database operations and maintenance.
"""

import os
import logging
import datetime

# Configure logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

def backup_database():
    """Create a backup of the database.
    For PostgreSQL, this requires pg_dump to be installed and the DATABASE_URL to be correctly set.
    """
    try:
        # Check if we're using PostgreSQL
        if os.environ.get("DATABASE_URL") and "postgres" in os.environ.get("DATABASE_URL"):
            # Create backups directory if it doesn't exist
            backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
            os.makedirs(backup_dir, exist_ok=True)
            
            # Create a timestamped filename for the backup
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_file = os.path.join(backup_dir, f"inventory_backup_{timestamp}.sql")
            
            # Get PostgreSQL connection details from environment variables
            pg_host = os.environ.get("PGHOST")
            pg_port = os.environ.get("PGPORT")
            pg_user = os.environ.get("PGUSER")
            pg_db = os.environ.get("PGDATABASE")
            
            # Build the pg_dump command
            cmd = f"PGPASSWORD='{os.environ.get('PGPASSWORD')}' pg_dump -h {pg_host} -p {pg_port} "
            cmd += f"-U {pg_user} -d {pg_db} -F p -f {backup_file}"
            
            # Execute the backup command
            logger.info(f"Backing up PostgreSQL database to {backup_file}")
            os.system(cmd)
            
            # Check if the backup file was created and has content
            if os.path.exists(backup_file) and os.path.getsize(backup_file) > 0:
                logger.info("Database backup completed successfully")
                return backup_file
            else:
                logger.error("Database backup failed: backup file is empty or does not exist")
                return None
                
        else:
            # For SQLite, simply copy the database file
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory.db')
            if os.path.exists(db_path):
                # Create backups directory if it doesn't exist
                backup_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'backups')
                os.makedirs(backup_dir, exist_ok=True)
                
                # Create a timestamped filename for the backup
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                backup_file = os.path.join(backup_dir, f"inventory_backup_{timestamp}.db")
                
                # Copy the database file
                import shutil
                shutil.copy2(db_path, backup_file)
                
                logger.info(f"SQLite database backup completed: {backup_file}")
                return backup_file
            else:
                logger.error(f"SQLite database file not found at {db_path}")
                return None
    except Exception as e:
        logger.error(f"Database backup failed: {str(e)}", exc_info=True)
        return None

def restore_database(backup_file):
    """Restore database from a backup file."""
    try:
        # Check if we're using PostgreSQL
        if os.environ.get("DATABASE_URL") and "postgres" in os.environ.get("DATABASE_URL"):
            # Verify the backup file exists
            if not os.path.exists(backup_file):
                logger.error(f"Backup file not found: {backup_file}")
                return False
                
            # Get PostgreSQL connection details from environment variables
            pg_host = os.environ.get("PGHOST")
            pg_port = os.environ.get("PGPORT")
            pg_user = os.environ.get("PGUSER")
            pg_db = os.environ.get("PGDATABASE")
            
            # Build the psql command to restore the database
            cmd = f"PGPASSWORD='{os.environ.get('PGPASSWORD')}' psql -h {pg_host} -p {pg_port} "
            cmd += f"-U {pg_user} -d {pg_db} -f {backup_file}"
            
            # Execute the restore command
            logger.info(f"Restoring PostgreSQL database from {backup_file}")
            os.system(cmd)
            logger.info("Database restore completed")
            
            return True
                
        else:
            # For SQLite, simply copy the backup file over the database file
            db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory.db')
            
            # Verify the backup file exists
            if not os.path.exists(backup_file):
                logger.error(f"Backup file not found: {backup_file}")
                return False
                
            # Copy the backup file to the database location
            import shutil
            shutil.copy2(backup_file, db_path)
            
            logger.info(f"SQLite database restored from {backup_file}")
            return True
    except Exception as e:
        logger.error(f"Database restore failed: {str(e)}", exc_info=True)
        return False

def optimize_database():
    """Optimize the database for performance."""
    try:
        # Import Flask app and run commands within app context
        from app import app, db
        
        with app.app_context():
            # Check if we're using PostgreSQL
            if "postgres" in app.config["SQLALCHEMY_DATABASE_URI"]:
                # Run VACUUM ANALYZE to update statistics and reclaim space
                logger.info("Optimizing PostgreSQL database with VACUUM ANALYZE")
                db.session.execute(db.text('VACUUM ANALYZE'))
                logger.info("Database optimization completed")
                
            else:
                # For SQLite, run VACUUM and ANALYZE
                logger.info("Optimizing SQLite database")
                db.session.execute(db.text('VACUUM'))
                db.session.execute(db.text('ANALYZE'))
                logger.info("Database optimization completed")
                
            return True
    except Exception as e:
        logger.error(f"Database optimization failed: {str(e)}", exc_info=True)
        return False

def get_database_stats():
    """Get statistics about the database."""
    try:
        # Import Flask app and run commands within app context
        from app import app, db
        from models import Product, Supplier, PurchaseOrder, PurchaseItem
        
        stats = {}
        
        with app.app_context():
            # Get table counts
            stats['product_count'] = db.session.query(db.func.count(Product.id)).scalar()
            stats['supplier_count'] = db.session.query(db.func.count(Supplier.id)).scalar()
            stats['order_count'] = db.session.query(db.func.count(PurchaseOrder.id)).scalar()
            stats['item_count'] = db.session.query(db.func.count(PurchaseItem.id)).scalar()
            
            # Get total inventory value
            stats['inventory_value'] = db.session.query(
                db.func.sum(Product.unit_price * Product.quantity_in_stock)
            ).scalar() or 0
            
            # Get low stock products count
            stats['low_stock_count'] = db.session.query(db.func.count(Product.id)).filter(
                Product.quantity_in_stock <= Product.reorder_level
            ).scalar()
            
            # Get database type
            if "postgres" in app.config["SQLALCHEMY_DATABASE_URI"]:
                stats['database_type'] = "PostgreSQL"
                
                # Get PostgreSQL specific stats
                try:
                    # Get database size
                    result = db.session.execute(db.text(
                        "SELECT pg_size_pretty(pg_database_size(current_database()))"
                    )).scalar()
                    stats['database_size'] = result
                    
                    # Get table sizes
                    result = db.session.execute(db.text("""
                        SELECT relname as table_name, 
                               pg_size_pretty(pg_total_relation_size(relid)) as total_size
                        FROM pg_catalog.pg_statio_user_tables
                        ORDER BY pg_total_relation_size(relid) DESC
                    """)).all()
                    stats['table_sizes'] = {row[0]: row[1] for row in result}
                    
                except Exception as e:
                    logger.warning(f"Could not get PostgreSQL specific stats: {str(e)}")
            else:
                stats['database_type'] = "SQLite"
                
                # Get SQLite database file size
                db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'inventory.db')
                if os.path.exists(db_path):
                    stats['database_size'] = f"{os.path.getsize(db_path) / (1024*1024):.2f} MB"
                else:
                    stats['database_size'] = "Unknown"
            
            logger.info(f"Retrieved database statistics: {stats}")
            return stats
    except Exception as e:
        logger.error(f"Failed to get database statistics: {str(e)}", exc_info=True)
        return {}

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python db_utils.py [backup|restore|optimize|stats]")
        sys.exit(1)
        
    command = sys.argv[1].lower()
    
    if command == "backup":
        backup_file = backup_database()
        if backup_file:
            print(f"Database backed up to: {backup_file}")
            sys.exit(0)
        else:
            print("Database backup failed")
            sys.exit(1)
            
    elif command == "restore":
        if len(sys.argv) < 3:
            print("Usage: python db_utils.py restore <backup_file>")
            sys.exit(1)
            
        backup_file = sys.argv[2]
        if restore_database(backup_file):
            print(f"Database restored from: {backup_file}")
            sys.exit(0)
        else:
            print("Database restore failed")
            sys.exit(1)
            
    elif command == "optimize":
        if optimize_database():
            print("Database optimization completed")
            sys.exit(0)
        else:
            print("Database optimization failed")
            sys.exit(1)
            
    elif command == "stats":
        stats = get_database_stats()
        if stats:
            print("\nDatabase Statistics:")
            print("====================")
            print(f"Database Type: {stats.get('database_type', 'Unknown')}")
            print(f"Database Size: {stats.get('database_size', 'Unknown')}")
            print("\nTable Counts:")
            print(f"  Products: {stats.get('product_count', 0)}")
            print(f"  Suppliers: {stats.get('supplier_count', 0)}")
            print(f"  Purchase Orders: {stats.get('order_count', 0)}")
            print(f"  Purchase Items: {stats.get('item_count', 0)}")
            print(f"\nInventory Value: ${stats.get('inventory_value', 0):.2f}")
            print(f"Low Stock Products: {stats.get('low_stock_count', 0)}")
            
            if 'table_sizes' in stats:
                print("\nTable Sizes:")
                for table, size in stats['table_sizes'].items():
                    print(f"  {table}: {size}")
                    
            sys.exit(0)
        else:
            print("Failed to get database statistics")
            sys.exit(1)
            
    else:
        print(f"Unknown command: {command}")
        print("Usage: python db_utils.py [backup|restore|optimize|stats]")
        sys.exit(1)
