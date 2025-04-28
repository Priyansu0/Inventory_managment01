"""
Dashboard tab for displaying overview and metrics.
"""

import logging
import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, 
                           QTableWidget, QTableWidgetItem, QHeaderView,
                           QPushButton, QGroupBox, QGridLayout, QFrame)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QColor, QFont

from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from database import get_session
from models import Product, PurchaseOrder, Supplier
from utils.chart_utils import create_inventory_value_chart, create_orders_trend_chart

logger = logging.getLogger(__name__)


class DashboardTab(QWidget):
    """Dashboard tab displaying system overview and metrics."""
    
    def __init__(self):
        super().__init__()
        self.initUI()
        
        # Set up timer for auto-refresh
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_data)
        self.refresh_timer.start(60000)  # Refresh every minute
    
    def initUI(self):
        """Initialize the user interface."""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel("Dashboard")
        title_label.setAlignment(Qt.AlignCenter)
        title_font = QFont()
        title_font.setPointSize(16)
        title_font.setBold(True)
        title_label.setFont(title_font)
        main_layout.addWidget(title_label)
        
        # Date and time
        self.datetime_label = QLabel()
        self.datetime_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.datetime_label)
        self.update_datetime()
        
        # Set up timer for updating date/time
        self.datetime_timer = QTimer(self)
        self.datetime_timer.timeout.connect(self.update_datetime)
        self.datetime_timer.start(1000)  # Update every second
        
        # Main metrics section
        metrics_layout = QHBoxLayout()
        
        # Left side - Key metrics
        metrics_group = QGroupBox("Key Metrics")
        metrics_grid = QGridLayout(metrics_group)
        
        # Total products
        self.total_products_label = QLabel("Loading...")
        metrics_grid.addWidget(QLabel("Total Products:"), 0, 0)
        metrics_grid.addWidget(self.total_products_label, 0, 1)
        
        # Low stock products
        self.low_stock_label = QLabel("Loading...")
        metrics_grid.addWidget(QLabel("Low Stock Items:"), 1, 0)
        metrics_grid.addWidget(self.low_stock_label, 1, 1)
        
        # Total suppliers
        self.total_suppliers_label = QLabel("Loading...")
        metrics_grid.addWidget(QLabel("Active Suppliers:"), 2, 0)
        metrics_grid.addWidget(self.total_suppliers_label, 2, 1)
        
        # Pending orders
        self.pending_orders_label = QLabel("Loading...")
        metrics_grid.addWidget(QLabel("Pending Orders:"), 3, 0)
        metrics_grid.addWidget(self.pending_orders_label, 3, 1)
        
        # Total inventory value
        self.inventory_value_label = QLabel("Loading...")
        metrics_grid.addWidget(QLabel("Inventory Value:"), 4, 0)
        metrics_grid.addWidget(self.inventory_value_label, 4, 1)
        
        metrics_layout.addWidget(metrics_group)
        
        # Right side - Recent activity
        activity_group = QGroupBox("Recent Activity")
        activity_layout = QVBoxLayout(activity_group)
        
        self.activity_table = QTableWidget()
        self.activity_table.setColumnCount(3)
        self.activity_table.setHorizontalHeaderLabels(["Date", "Type", "Details"])
        self.activity_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.activity_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.activity_table.setAlternatingRowColors(True)
        self.activity_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        activity_layout.addWidget(self.activity_table)
        metrics_layout.addWidget(activity_group)
        
        main_layout.addLayout(metrics_layout)
        
        # Charts section
        charts_layout = QHBoxLayout()
        
        # Left chart - Inventory Value
        inventory_chart_group = QGroupBox("Inventory Value by Category")
        inventory_chart_layout = QVBoxLayout(inventory_chart_group)
        self.inventory_chart_widget = QWidget()
        inventory_chart_layout.addWidget(self.inventory_chart_widget)
        charts_layout.addWidget(inventory_chart_group)
        
        # Right chart - Purchase Order Trends
        orders_chart_group = QGroupBox("Purchase Order Trends")
        orders_chart_layout = QVBoxLayout(orders_chart_group)
        self.orders_chart_widget = QWidget()
        orders_chart_layout.addWidget(self.orders_chart_widget)
        charts_layout.addWidget(orders_chart_group)
        
        main_layout.addLayout(charts_layout)
        
        # Low stock alerts section
        alerts_group = QGroupBox("Low Stock Alerts")
        alerts_layout = QVBoxLayout(alerts_group)
        
        self.alerts_table = QTableWidget()
        self.alerts_table.setColumnCount(5)
        self.alerts_table.setHorizontalHeaderLabels([
            "Product", "SKU", "Current Stock", "Reorder Level", "Supplier"
        ])
        self.alerts_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.alerts_table.setAlternatingRowColors(True)
        self.alerts_table.setEditTriggers(QTableWidget.NoEditTriggers)
        
        alerts_layout.addWidget(self.alerts_table)
        main_layout.addWidget(alerts_group)
        
        # Refresh button
        refresh_button = QPushButton("Refresh Dashboard")
        refresh_button.clicked.connect(self.refresh_data)
        main_layout.addWidget(refresh_button)
        
        # Load initial data
        self.load_data()
    
    def update_datetime(self):
        """Update the date and time display."""
        now = datetime.datetime.now()
        self.datetime_label.setText(now.strftime("%A, %B %d, %Y %H:%M:%S"))
    
    def load_data(self):
        """Load all dashboard data."""
        try:
            session = get_session()
            
            # Load key metrics
            self.load_key_metrics(session)
            
            # Load recent activity
            self.load_recent_activity(session)
            
            # Load charts
            self.load_charts(session)
            
            # Load low stock alerts
            self.load_low_stock_alerts(session)
            
        except SQLAlchemyError as e:
            logger.error(f"Error loading dashboard data: {str(e)}")
        finally:
            session.close()
    
    def load_key_metrics(self, session):
        """Load key metrics data."""
        try:
            # Total products
            total_products = session.query(func.count(Product.id)).scalar()
            self.total_products_label.setText(str(total_products))
            
            # Low stock products
            low_stock_count = session.query(func.count(Product.id))\
                .filter(Product.quantity_in_stock <= Product.reorder_level).scalar()
            self.low_stock_label.setText(f"{low_stock_count}")
            
            # Highlight if there are low stock items
            if low_stock_count > 0:
                self.low_stock_label.setStyleSheet("color: red; font-weight: bold;")
            else:
                self.low_stock_label.setStyleSheet("")
            
            # Total active suppliers
            total_suppliers = session.query(func.count(Supplier.id))\
                .filter(Supplier.active == True).scalar()
            self.total_suppliers_label.setText(str(total_suppliers))
            
            # Pending orders
            pending_orders = session.query(func.count(PurchaseOrder.id))\
                .filter(PurchaseOrder.status == 'pending').scalar()
            self.pending_orders_label.setText(str(pending_orders))
            
            # Total inventory value
            inventory_value = session.query(func.sum(Product.quantity_in_stock * Product.unit_price)).scalar()
            if inventory_value is None:
                inventory_value = 0
            self.inventory_value_label.setText(f"${inventory_value:.2f}")
            
        except SQLAlchemyError as e:
            logger.error(f"Error loading key metrics: {str(e)}")
    
    def load_recent_activity(self, session):
        """Load recent activity data."""
        try:
            # Clear the table
            self.activity_table.setRowCount(0)
            
            # Get recent purchase orders (last 10)
            recent_orders = session.query(PurchaseOrder)\
                .order_by(PurchaseOrder.created_at.desc())\
                .limit(5).all()
            
            # Add rows for each activity
            for row, order in enumerate(recent_orders):
                self.activity_table.insertRow(row)
                
                date_str = order.created_at.strftime("%Y-%m-%d %H:%M") if order.created_at else "N/A"
                supplier_name = order.supplier.name if order.supplier else "N/A"
                
                self.activity_table.setItem(row, 0, QTableWidgetItem(date_str))
                self.activity_table.setItem(row, 1, QTableWidgetItem("Purchase Order"))
                self.activity_table.setItem(row, 2, QTableWidgetItem(
                    f"Order #{order.order_number} to {supplier_name} - ${order.total_amount:.2f}"
                ))
                
            # TODO: Add other activity types (product changes, etc.)
            
        except SQLAlchemyError as e:
            logger.error(f"Error loading recent activity: {str(e)}")
    
    def load_charts(self, session):
        """Load chart data."""
        try:
            # Inventory value by category chart
            create_inventory_value_chart(session, self.inventory_chart_widget)
            
            # Orders trend chart
            create_orders_trend_chart(session, self.orders_chart_widget)
            
        except Exception as e:
            logger.error(f"Error creating charts: {str(e)}")
    
    def load_low_stock_alerts(self, session):
        """Load low stock alerts data."""
        try:
            # Get products with stock below or at reorder level
            low_stock_products = session.query(Product)\
                .filter(Product.quantity_in_stock <= Product.reorder_level)\
                .order_by((Product.reorder_level - Product.quantity_in_stock).desc())\
                .all()
            
            # Clear the table
            self.alerts_table.setRowCount(0)
            
            # Add rows for each low stock product
            for row, product in enumerate(low_stock_products):
                self.alerts_table.insertRow(row)
                
                supplier_name = product.supplier.name if product.supplier else "N/A"
                
                self.alerts_table.setItem(row, 0, QTableWidgetItem(product.name))
                self.alerts_table.setItem(row, 1, QTableWidgetItem(product.sku))
                
                # Highlight critical stock levels
                stock_item = QTableWidgetItem(str(product.quantity_in_stock))
                if product.quantity_in_stock == 0:
                    stock_item.setBackground(QColor(255, 150, 150))  # Darker red for out of stock
                elif product.quantity_in_stock < product.reorder_level:
                    stock_item.setBackground(QColor(255, 200, 200))  # Red for below reorder
                else:
                    stock_item.setBackground(QColor(255, 255, 200))  # Yellow for at reorder level
                
                self.alerts_table.setItem(row, 2, stock_item)
                self.alerts_table.setItem(row, 3, QTableWidgetItem(str(product.reorder_level)))
                self.alerts_table.setItem(row, 4, QTableWidgetItem(supplier_name))
            
        except SQLAlchemyError as e:
            logger.error(f"Error loading low stock alerts: {str(e)}")
    
    def refresh_data(self):
        """Refresh all dashboard data."""
        self.load_data()
