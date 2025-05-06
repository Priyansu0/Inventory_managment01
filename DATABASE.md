# PostgreSQL Integration Guide

## Overview

The Inventory and Purchase Management System supports both SQLite for development and PostgreSQL for production. This guide explains how to set up and manage the PostgreSQL database for the application.

## Configuration

### Environment Variables

When using PostgreSQL, the following environment variables should be configured:

- `DATABASE_URL`: The complete PostgreSQL connection string (required)
- `PGHOST`: PostgreSQL server host
- `PGPORT`: PostgreSQL server port (typically 5432)
- `PGUSER`: PostgreSQL username
- `PGPASSWORD`: PostgreSQL password
- `PGDATABASE`: PostgreSQL database name

### Example Connection String

A typical PostgreSQL connection string follows this format:

```
postgresql://username:password@hostname:port/database
```

## Database Setup

1. Create a PostgreSQL database on your server
2. Set the environment variables as described above
3. Run the database initialization script:

```bash
python init_db.py
```

## Database Maintenance

The system includes several utilities for database maintenance:

### Backup

To create a backup of the database:

```bash
python db_utils.py backup
```

This will create a timestamped backup in the `backups` directory.

### Restore

To restore the database from a backup:

```bash
python db_utils.py restore backups/inventory_backup_20250101_120000.sql
```

### Optimize

To optimize the database for performance:

```bash
python db_utils.py optimize
```

### Statistics

To view database statistics:

```bash
python db_utils.py stats
```

## Performance Considerations

### Connection Pooling

The application is configured to use SQLAlchemy's connection pooling with the following settings:

- `pool_size`: 10 (maximum number of connections to keep)
- `max_overflow`: 15 (maximum number of connections to create beyond pool_size)
- `pool_recycle`: 300 (connections are recycled after 5 minutes)
- `pool_pre_ping`: True (connections are tested before use)
- `pool_timeout`: 30 (timeout for obtaining a connection)

### Indexes

The following indexes are created for performance optimization:

- `idx_products_sku`: Index for product SKU lookups
- `idx_products_category`: Index for filtering products by category
- `idx_products_stock_level`: Index for finding products with low stock
- `idx_purchase_orders_status`: Index for filtering purchase orders by status
- `idx_purchase_orders_date`: Index for filtering purchase orders by date

## Troubleshooting

### Connection Issues

If you experience database connection issues:

1. Verify the environment variables are set correctly
2. Check if the PostgreSQL server is running and accessible
3. Ensure the database user has sufficient privileges
4. Run the connection test: `python -c "from init_db import test_connection; test_connection()"`

### Migration Issues

If you need to modify the database schema:

1. Create a backup of the database
2. Update the models in `models.py`
3. Run the initialization script with the updated models: `python init_db.py`

## Deployment Considerations

When deploying to production:

1. Use a dedicated PostgreSQL database
2. Set all required environment variables
3. Schedule regular backups using `db_utils.py backup`
4. Consider using a PostgreSQL-specific monitoring tool
5. Review and adjust connection pool settings based on traffic
