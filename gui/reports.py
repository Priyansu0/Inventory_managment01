"""
Reporting functionality for the Inventory Management System.
"""

import logging
import os
import datetime
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, 
                           QPushButton, QDateEdit, QFileDialog, QMessageBox, QGroupBox,
                           QFormLayout, QCheckBox, QWidget, QSpacerItem, QSizePolicy)
from PyQt5.QtCore import Qt, QDate

from sqlalchemy import func, desc, case, extract
from sqlalchemy.exc import SQLAlchemyError
from database import get_session
from models import Product, PurchaseOrder, PurchaseItem, Supplier
from utils.export_utils import export_to_excel
from utils.chart_utils import create_report_chart

logger = logging.getLogger(__name__)


class ReportDialog(QDialog):
    """Dialog for generating system reports."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the report dialog UI."""
        self.setWindowTitle("Generate Reports")
        self.setMinimumWidth(600)
        self.setMinimumHeight(400)
        
        main_layout = QVBoxLayout(self)
        
        # Report type selection
        report_type_group = QGroupBox("Report Type")
        report_type_layout = QFormLayout(report_type_group)
        
        self.report_type_combo = QComboBox()
        self.report_type_combo.addItems([
            "Inventory Valuation",
            "Low Stock Items",
            "Purchase Order History",
            "Supplier Performance",
            "Category Analysis",
            "Monthly Purchases"
        ])
        self.report_type_combo.currentIndexChanged.connect(self.on_report_type_changed)
        report_type_layout.addRow("Select Report:", self.report_type_combo)
        
        main_layout.addWidget(report_type_group)
        
        # Filter options group
        filter_group = QGroupBox("Filter Options")
        self.filter_layout = QFormLayout(filter_group)
        
        # Date range widgets
        self.date_from = QDateEdit()
        self.date_from.setCalendarPopup(True)
        self.date_from.setDate(QDate.currentDate().addMonths(-3))
        
        self.date_to = QDateEdit()
        self.date_to.setCalendarPopup(True)
        self.date_to.setDate(QDate.currentDate())
        
        # Category filter
        self.category_combo = QComboBox()
        self.category_combo.addItem("All Categories")
        
        # Supplier filter
        self.supplier_combo = QComboBox()
        self.supplier_combo.addItem("All Suppliers")
        
        # Include charts checkbox
        self.include_charts = QCheckBox("Include charts")
        self.include_charts.setChecked(True)
        
        # Add widgets to layout
        self.filter_layout.addRow("From:", self.date_from)
        self.filter_layout.addRow("To:", self.date_to)
        
        main_layout.addWidget(filter_group)
        
        # Preview/chart area
        self.preview_group = QGroupBox("Preview")
        preview_layout = QVBoxLayout(self.preview_group)
        
        self.preview_label = QLabel("Select a report type to preview")
        self.preview_label.setAlignment(Qt.AlignCenter)
        preview_layout.addWidget(self.preview_label)
        
        self.chart_widget = QWidget()
        self.chart_widget.setMinimumHeight(200)
        preview_layout.addWidget(self.chart_widget)
        
        main_layout.addWidget(self.preview_group)
        
        # Buttons layout
        buttons_layout = QHBoxLayout()
        
        self.generate_btn = QPushButton("Generate Report")
        self.generate_btn.clicked.connect(self.generate_report)
        
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.generate_btn)
        buttons_layout.addWidget(self.cancel_btn)
        
        main_layout.addLayout(buttons_layout)
        
        # Load data for filters
        self.load_filter_data()
        
        # Initial report type setup
        self.on_report_type_changed(0)
    
    def load_filter_data(self):
        """Load data for filter combos."""
        try:
            session = get_session()
            
            # Load categories
            categories = session.query(Product.category).distinct().all()
            for category in categories:
                if category[0]:  # Skip None values
                    self.category_combo.addItem(category[0])
            
            # Load suppliers
            suppliers = session.query(Supplier).filter_by(active=True).order_by(Supplier.name).all()
            for supplier in suppliers:
                self.supplier_combo.addItem(supplier.name, supplier.id)
            
        except SQLAlchemyError as e:
            logger.error(f"Error loading filter data: {str(e)}")
        finally:
            session.close()
    
    def on_report_type_changed(self, index):
        """Handle report type selection change."""
        # Clear filter layout except date fields
        for i in reversed(range(self.filter_layout.count())):
            item = self.filter_layout.itemAt(i)
            if item.widget() not in [self.date_from, self.date_to] and item.widget() is not None:
                item.widget().setParent(None)
        
        # Reset default filters
        self.filter_layout.addRow("From:", self.date_from)
        self.filter_layout.addRow("To:", self.date_to)
        
        # Add specific filters based on report type
        report_type = self.report_type_combo.currentText()
        
        if report_type in ["Inventory Valuation", "Low Stock Items", "Category Analysis"]:
            self.filter_layout.addRow("Category:", self.category_combo)
            # No date needed for inventory reports
            self.date_from.setEnabled(False)
            self.date_to.setEnabled(False)
        else:
            # Enable date filters for time-based reports
            self.date_from.setEnabled(True)
            self.date_to.setEnabled(True)
        
        if report_type in ["Purchase Order History", "Supplier Performance"]:
            self.filter_layout.addRow("Supplier:", self.supplier_combo)
        
        # Always add chart option
        self.filter_layout.addRow("", self.include_charts)
        
        # Update preview
        self.update_preview()
    
    def update_preview(self):
        """Update the preview area with report info and sample chart."""
        report_type = self.report_type_combo.currentText()
        
        # Update preview label
        if report_type == "Inventory Valuation":
            description = "Shows the current value of inventory items, grouped by category."
        elif report_type == "Low Stock Items":
            description = "Lists all products that are at or below their reorder levels."
        elif report_type == "Purchase Order History":
            description = "Provides details of purchase orders within the selected time period."
        elif report_type == "Supplier Performance":
            description = "Analyzes supplier performance based on order history and delivery times."
        elif report_type == "Category Analysis":
            description = "Breaks down inventory by product categories."
        elif report_type == "Monthly Purchases":
            description = "Shows purchase trends over months in the selected period."
        else:
            description = "Select a report type to preview"
        
        self.preview_label.setText(description)
        
        # Try to generate a preview chart
        try:
            session = get_session()
            create_report_chart(session, report_type, self.chart_widget)
        except Exception as e:
            logger.error(f"Error creating preview chart: {str(e)}")
        finally:
            session.close()
    
    def generate_report(self):
        """Generate and export the selected report."""
        report_type = self.report_type_combo.currentText()
        
        # Get file path for export
        options = QFileDialog.Options()
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Report",
            f"{report_type.replace(' ', '_')}_{datetime.datetime.now().strftime('%Y%m%d')}.xlsx",
            "Excel Files (*.xlsx)",
            options=options
        )
        
        if not file_path:
            return
        
        # Add extension if not provided
        if not file_path.endswith('.xlsx'):
            file_path += '.xlsx'
        
        try:
            session = get_session()
            
            # Process based on report type
            if report_type == "Inventory Valuation":
                self.generate_inventory_valuation(session, file_path)
            elif report_type == "Low Stock Items":
                self.generate_low_stock_report(session, file_path)
            elif report_type == "Purchase Order History":
                self.generate_purchase_history(session, file_path)
            elif report_type == "Supplier Performance":
                self.generate_supplier_performance(session, file_path)
            elif report_type == "Category Analysis":
                self.generate_category_analysis(session, file_path)
            elif report_type == "Monthly Purchases":
                self.generate_monthly_purchases(session, file_path)
            
            QMessageBox.information(self, "Report Generated", 
                                  f"Report has been successfully saved to:\n{file_path}")
            
        except Exception as e:
            logger.error(f"Error generating report: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to generate report: {str(e)}")
        finally:
            session.close()
    
    def generate_inventory_valuation(self, session, file_path):
        """Generate inventory valuation report."""
        # Get selected category filter
        category = self.category_combo.currentText()
        if category == "All Categories":
            category = None
        
        # Build query
        query = session.query(
            Product.category,
            func.count(Product.id).label('item_count'),
            func.sum(Product.quantity_in_stock).label('total_units'),
            func.sum(Product.quantity_in_stock * Product.unit_price).label('total_value')
        ).group_by(Product.category)
        
        if category:
            query = query.filter(Product.category == category)
        
        results = query.all()
        
        # Prepare data for export
        summary_data = []
        for result in results:
            summary_data.append([
                result.category or "Uncategorized",
                result.item_count,
                result.total_units,
                result.total_value
            ])
        
        # Get detailed product data
        products_query = session.query(Product)
        if category:
            products_query = products_query.filter(Product.category == category)
        
        products = products_query.order_by(Product.category, Product.name).all()
        
        product_data = []
        for product in products:
            supplier_name = product.supplier.name if product.supplier else "N/A"
            product_data.append([
                product.sku,
                product.name,
                product.category or "Uncategorized",
                product.unit_price,
                product.quantity_in_stock,
                product.quantity_in_stock * product.unit_price,
                supplier_name
            ])
        
        # Export to Excel with multiple sheets
        workbook_data = {
            "Summary": {
                "headers": ["Category", "Number of Items", "Total Units", "Total Value ($)"],
                "data": summary_data
            },
            "Product Details": {
                "headers": ["SKU", "Product", "Category", "Unit Price ($)", "Quantity", "Value ($)", "Supplier"],
                "data": product_data
            }
        }
        
        # Add chart if requested
        if self.include_charts:
            chart_path = self.create_temp_chart(session, "Inventory Valuation")
            if chart_path:
                workbook_data["chart_path"] = chart_path
        
        export_to_excel(file_path, workbook_data)
    
    def generate_low_stock_report(self, session, file_path):
        """Generate low stock items report."""
        # Get selected category filter
        category = self.category_combo.currentText()
        if category == "All Categories":
            category = None
        
        # Build query for low stock items
        query = session.query(Product).filter(
            Product.quantity_in_stock <= Product.reorder_level
        )
        
        if category:
            query = query.filter(Product.category == category)
        
        products = query.order_by(
            (Product.reorder_level - Product.quantity_in_stock).desc(),
            Product.category, 
            Product.name
        ).all()
        
        # Prepare data for export
        data = []
        for product in products:
            supplier_name = product.supplier.name if product.supplier else "N/A"
            status = "Out of Stock" if product.quantity_in_stock == 0 else "Low Stock"
            
            data.append([
                product.sku,
                product.name,
                product.category or "Uncategorized",
                product.quantity_in_stock,
                product.reorder_level,
                product.reorder_quantity,
                supplier_name,
                status
            ])
        
        # Export to Excel
        workbook_data = {
            "Low Stock Items": {
                "headers": ["SKU", "Product", "Category", "Current Stock", "Reorder Level", 
                          "Suggested Order Qty", "Supplier", "Status"],
                "data": data
            }
        }
        
        # Add chart if requested
        if self.include_charts:
            chart_path = self.create_temp_chart(session, "Low Stock Items")
            if chart_path:
                workbook_data["chart_path"] = chart_path
        
        export_to_excel(file_path, workbook_data)
    
    def generate_purchase_history(self, session, file_path):
        """Generate purchase order history report."""
        # Get date range
        date_from = self.date_from.date().toPyDate()
        date_to = self.date_to.date().toPyDate()
        
        # Get supplier filter
        supplier_id = self.supplier_combo.currentData()
        if self.supplier_combo.currentText() == "All Suppliers":
            supplier_id = None
        
        # Build query
        query = session.query(PurchaseOrder).filter(
            PurchaseOrder.order_date.between(date_from, date_to)
        )
        
        if supplier_id:
            query = query.filter(PurchaseOrder.supplier_id == supplier_id)
        
        orders = query.order_by(PurchaseOrder.order_date.desc()).all()
        
        # Prepare summary data
        status_counts = {
            "pending": 0,
            "delivered": 0,
            "cancelled": 0
        }
        
        total_value = 0
        
        for order in orders:
            status_counts[order.status] += 1
            if order.status != "cancelled":
                total_value += order.total_amount
        
        summary_data = [
            ["Total Orders", len(orders)],
            ["Pending Orders", status_counts["pending"]],
            ["Delivered Orders", status_counts["delivered"]],
            ["Cancelled Orders", status_counts["cancelled"]],
            ["Total Value", f"${total_value:.2f}"]
        ]
        
        # Prepare order details
        order_data = []
        for order in orders:
            supplier_name = order.supplier.name if order.supplier else "N/A"
            order_date = order.order_date.strftime('%Y-%m-%d') if order.order_date else "N/A"
            expected_date = order.expected_delivery.strftime('%Y-%m-%d') if order.expected_delivery else "N/A"
            
            order_data.append([
                order.order_number,
                order_date,
                supplier_name,
                order.status,
                expected_date,
                order.total_amount
            ])
        
        # Export to Excel
        workbook_data = {
            "Summary": {
                "headers": ["Metric", "Value"],
                "data": summary_data
            },
            "Purchase Orders": {
                "headers": ["Order Number", "Date", "Supplier", "Status", "Expected Delivery", "Amount ($)"],
                "data": order_data
            }
        }
        
        # Add order items if there are orders
        if orders:
            items_data = []
            for order in orders:
                for item in order.items:
                    product_name = item.product.name if item.product else f"Product #{item.product_id}"
                    items_data.append([
                        order.order_number,
                        order.order_date.strftime('%Y-%m-%d') if order.order_date else "N/A",
                        product_name,
                        item.quantity,
                        item.unit_price,
                        item.total_price
                    ])
            
            workbook_data["Order Items"] = {
                "headers": ["Order Number", "Date", "Product", "Quantity", "Unit Price ($)", "Total Price ($)"],
                "data": items_data
            }
        
        # Add chart if requested
        if self.include_charts:
            chart_path = self.create_temp_chart(session, "Purchase Order History")
            if chart_path:
                workbook_data["chart_path"] = chart_path
        
        export_to_excel(file_path, workbook_data)
    
    def generate_supplier_performance(self, session, file_path):
        """Generate supplier performance report."""
        # Get date range
        date_from = self.date_from.date().toPyDate()
        date_to = self.date_to.date().toPyDate()
        
        # Get supplier filter
        supplier_id = self.supplier_combo.currentData()
        if self.supplier_combo.currentText() == "All Suppliers":
            supplier_id = None
        
        # Build query for suppliers
        suppliers_query = session.query(Supplier)
        if supplier_id:
            suppliers_query = suppliers_query.filter(Supplier.id == supplier_id)
        
        suppliers = suppliers_query.filter(Supplier.active == True).all()
        
        # Process each supplier
        supplier_data = []
        order_data = []
        
        for supplier in suppliers:
            # Get orders for this supplier
            orders = session.query(PurchaseOrder).filter(
                PurchaseOrder.supplier_id == supplier.id,
                PurchaseOrder.order_date.between(date_from, date_to)
            ).all()
            
            total_orders = len(orders)
            if total_orders == 0:
                continue  # Skip suppliers with no orders in the period
            
            delivered_orders = sum(1 for o in orders if o.status == "delivered")
            cancelled_orders = sum(1 for o in orders if o.status == "cancelled")
            pending_orders = total_orders - delivered_orders - cancelled_orders
            
            total_value = sum(o.total_amount for o in orders if o.status != "cancelled")
            
            # Calculate average delivery time for delivered orders
            delivery_times = []
            for order in orders:
                if order.status == "delivered" and order.order_date and order.expected_delivery:
                    expected_days = (order.expected_delivery - order.order_date).days
                    delivery_times.append(expected_days)
            
            avg_delivery_time = sum(delivery_times) / len(delivery_times) if delivery_times else 0
            
            # Add to supplier data
            supplier_data.append([
                supplier.name,
                total_orders,
                delivered_orders,
                pending_orders,
                cancelled_orders,
                f"{(delivered_orders / total_orders * 100):.1f}%" if total_orders > 0 else "0%",
                f"{avg_delivery_time:.1f} days",
                f"${total_value:.2f}"
            ])
            
            # Add orders to order data
            for order in orders:
                order_date = order.order_date.strftime('%Y-%m-%d') if order.order_date else "N/A"
                expected_date = order.expected_delivery.strftime('%Y-%m-%d') if order.expected_delivery else "N/A"
                
                order_data.append([
                    supplier.name,
                    order.order_number,
                    order_date,
                    expected_date,
                    order.status,
                    order.total_amount
                ])
        
        # Export to Excel
        workbook_data = {
            "Supplier Performance": {
                "headers": ["Supplier", "Total Orders", "Delivered", "Pending", "Cancelled", 
                           "Fulfillment Rate", "Avg Delivery Time", "Total Value ($)"],
                "data": supplier_data
            },
            "Order Details": {
                "headers": ["Supplier", "Order Number", "Order Date", "Expected Delivery", "Status", "Amount ($)"],
                "data": order_data
            }
        }
        
        # Add chart if requested
        if self.include_charts:
            chart_path = self.create_temp_chart(session, "Supplier Performance")
            if chart_path:
                workbook_data["chart_path"] = chart_path
        
        export_to_excel(file_path, workbook_data)
    
    def generate_category_analysis(self, session, file_path):
        """Generate category analysis report."""
        # Get selected category filter
        category = self.category_combo.currentText()
        if category == "All Categories":
            category = None
        
        # Build query for category summary
        query = session.query(
            func.coalesce(Product.category, "Uncategorized").label('category'),
            func.count(Product.id).label('product_count'),
            func.sum(Product.quantity_in_stock).label('total_units'),
            func.sum(Product.quantity_in_stock * Product.unit_price).label('total_value'),
            func.avg(Product.unit_price).label('avg_price')
        ).group_by(func.coalesce(Product.category, "Uncategorized"))
        
        if category:
            query = query.filter(Product.category == category)
        
        results = query.all()
        
        # Prepare data for export
        summary_data = []
        for result in results:
            summary_data.append([
                result.category,
                result.product_count,
                result.total_units,
                result.total_value,
                result.avg_price
            ])
        
        # Get low stock counts by category
        low_stock_query = session.query(
            func.coalesce(Product.category, "Uncategorized").label('category'),
            func.count(Product.id).label('low_stock_count')
        ).filter(
            Product.quantity_in_stock <= Product.reorder_level
        ).group_by(func.coalesce(Product.category, "Uncategorized"))
        
        if category:
            low_stock_query = low_stock_query.filter(Product.category == category)
        
        low_stock_results = {r.category: r.low_stock_count for r in low_stock_query.all()}
        
        # Add low stock counts to summary data
        for row in summary_data:
            row.append(low_stock_results.get(row[0], 0))
        
        # Export to Excel
        workbook_data = {
            "Category Analysis": {
                "headers": ["Category", "Number of Products", "Total Units", 
                           "Total Value ($)", "Average Price ($)", "Low Stock Items"],
                "data": summary_data
            }
        }
        
        # Add detailed product list
        products_query = session.query(Product)
        if category:
            products_query = products_query.filter(Product.category == category)
        
        products = products_query.order_by(
            func.coalesce(Product.category, "Uncategorized"), 
            Product.name
        ).all()
        
        product_data = []
        for product in products:
            supplier_name = product.supplier.name if product.supplier else "N/A"
            product_data.append([
                product.sku,
                product.name,
                product.category or "Uncategorized",
                product.unit_price,
                product.quantity_in_stock,
                product.quantity_in_stock * product.unit_price,
                "Yes" if product.quantity_in_stock <= product.reorder_level else "No",
                supplier_name
            ])
        
        workbook_data["Product Details"] = {
            "headers": ["SKU", "Product", "Category", "Unit Price ($)", "Quantity", 
                      "Value ($)", "Low Stock", "Supplier"],
            "data": product_data
        }
        
        # Add chart if requested
        if self.include_charts:
            chart_path = self.create_temp_chart(session, "Category Analysis")
            if chart_path:
                workbook_data["chart_path"] = chart_path
        
        export_to_excel(file_path, workbook_data)
    
    def generate_monthly_purchases(self, session, file_path):
        """Generate monthly purchases report."""
        # Get date range
        date_from = self.date_from.date().toPyDate()
        date_to = self.date_to.date().toPyDate()
        
        # Create a series of all months in the range
        start_date = datetime.date(date_from.year, date_from.month, 1)
        end_date = datetime.date(date_to.year, date_to.month, 1)
        
        months = []
        current = start_date
        while current <= end_date:
            months.append((current.year, current.month))
            # Move to next month
            if current.month == 12:
                current = datetime.date(current.year + 1, 1, 1)
            else:
                current = datetime.date(current.year, current.month + 1, 1)
        
        # Build query for monthly order totals
        monthly_orders = session.query(
            extract('year', PurchaseOrder.order_date).label('year'),
            extract('month', PurchaseOrder.order_date).label('month'),
            func.count(PurchaseOrder.id).label('order_count'),
            func.sum(case([(PurchaseOrder.status != 'cancelled', PurchaseOrder.total_amount)], else_=0)).label('total_value')
        ).filter(
            PurchaseOrder.order_date.between(date_from, date_to)
        ).group_by(
            extract('year', PurchaseOrder.order_date),
            extract('month', PurchaseOrder.order_date)
        ).all()
        
        # Convert to dictionary for easy lookup
        monthly_data = {(int(mo.year), int(mo.month)): (mo.order_count, mo.total_value) for mo in monthly_orders}
        
        # Prepare data for all months in range
        summary_data = []
        chart_data = []
        
        for year, month in months:
            month_name = datetime.date(year, month, 1).strftime('%B %Y')
            order_count, total_value = monthly_data.get((year, month), (0, 0))
            
            summary_data.append([
                month_name,
                order_count,
                f"${total_value:.2f}" if total_value else "$0.00"
            ])
            
            # Add to chart data
            chart_data.append({
                'month': month_name,
                'orders': order_count,
                'value': float(total_value) if total_value else 0
            })
        
        # Export to Excel
        workbook_data = {
            "Monthly Summary": {
                "headers": ["Month", "Number of Orders", "Total Value"],
                "data": summary_data
            }
        }
        
        # Add order details
        orders = session.query(PurchaseOrder).filter(
            PurchaseOrder.order_date.between(date_from, date_to)
        ).order_by(PurchaseOrder.order_date).all()
        
        order_data = []
        for order in orders:
            supplier_name = order.supplier.name if order.supplier else "N/A"
            order_date = order.order_date.strftime('%Y-%m-%d') if order.order_date else "N/A"
            month_name = order.order_date.strftime('%B %Y') if order.order_date else "N/A"
            
            order_data.append([
                month_name,
                order.order_number,
                order_date,
                supplier_name,
                order.status,
                order.total_amount
            ])
        
        workbook_data["Order Details"] = {
            "headers": ["Month", "Order Number", "Date", "Supplier", "Status", "Amount ($)"],
            "data": order_data
        }
        
        # Add chart if requested
        if self.include_charts:
            chart_path = self.create_temp_chart(session, "Monthly Purchases", chart_data)
            if chart_path:
                workbook_data["chart_path"] = chart_path
        
        export_to_excel(file_path, workbook_data)
    
    def create_temp_chart(self, session, report_type, custom_data=None):
        """Create a temporary chart for inclusion in the report."""
        try:
            import tempfile
            chart_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            chart_file.close()
            
            create_report_chart(session, report_type, None, chart_file.name, custom_data)
            return chart_file.name
        except Exception as e:
            logger.error(f"Error creating chart for report: {str(e)}")
            return None
