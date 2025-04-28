"""
Inventory management tab for handling products and stock levels.
"""

import logging
import os
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                           QTableWidgetItem, QPushButton, QLabel, QLineEdit, 
                           QHeaderView, QMessageBox, QFormLayout, QSpinBox, 
                           QDoubleSpinBox, QTextEdit, QComboBox, QFileDialog)
from PyQt5.QtCore import Qt, pyqtSignal, QTimer
from PyQt5.QtGui import QColor, QIcon

from sqlalchemy.exc import SQLAlchemyError
from database import get_session
from models import Product, Supplier
from gui.dialogs import ProductDialog
from utils.export_utils import export_to_excel, export_to_csv
from utils.qr_utils import generate_product_qr_code

logger = logging.getLogger(__name__)


class InventoryTab(QWidget):
    """Tab for managing inventory and products."""
    
    refresh_required = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        """Initialize the user interface."""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Search and filter section
        filter_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search products...")
        self.search_input.textChanged.connect(self.filter_products)
        
        self.category_filter = QComboBox()
        self.category_filter.addItem("All Categories")
        self.category_filter.currentTextChanged.connect(self.filter_products)
        
        self.low_stock_filter = QPushButton("Show Low Stock Only")
        self.low_stock_filter.setCheckable(True)
        self.low_stock_filter.toggled.connect(self.filter_products)
        
        filter_layout.addWidget(QLabel("Search:"))
        filter_layout.addWidget(self.search_input, 3)
        filter_layout.addWidget(QLabel("Category:"))
        filter_layout.addWidget(self.category_filter, 1)
        filter_layout.addWidget(self.low_stock_filter)
        
        main_layout.addLayout(filter_layout)
        
        # Products table
        self.products_table = QTableWidget()
        self.products_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.products_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.products_table.setColumnCount(8)
        self.products_table.setHorizontalHeaderLabels([
            "ID", "SKU", "Name", "Category", "Supplier", 
            "Unit Price", "Quantity", "Reorder Level"
        ])
        self.products_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.products_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.products_table.verticalHeader().setVisible(False)
        self.products_table.setAlternatingRowColors(True)
        self.products_table.doubleClicked.connect(self.edit_product)
        
        main_layout.addWidget(self.products_table, 1)
        
        # Buttons layout
        buttons_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("Add Product")
        self.add_btn.clicked.connect(self.add_product)
        
        self.edit_btn = QPushButton("Edit Selected")
        self.edit_btn.clicked.connect(self.edit_product)
        
        self.delete_btn = QPushButton("Delete Selected")
        self.delete_btn.clicked.connect(self.delete_product)
        
        self.generate_qr_btn = QPushButton("Generate QR Code")
        self.generate_qr_btn.clicked.connect(self.generate_qr)
        
        self.export_btn = QPushButton("Export Data")
        self.export_btn.clicked.connect(self.export_data)
        
        buttons_layout.addWidget(self.add_btn)
        buttons_layout.addWidget(self.edit_btn)
        buttons_layout.addWidget(self.delete_btn)
        buttons_layout.addWidget(self.generate_qr_btn)
        buttons_layout.addWidget(self.export_btn)
        
        main_layout.addLayout(buttons_layout)
        
        # Status message
        self.status_label = QLabel("")
        main_layout.addWidget(self.status_label)
        
        # Load initial data
        self.load_data()
        
        # Connect refresh signal
        self.refresh_required.connect(self.load_data)
    
    def load_data(self):
        """Load product data from the database."""
        try:
            session = get_session()
            products = session.query(Product).all()
            
            # Update category filter
            self.category_filter.clear()
            self.category_filter.addItem("All Categories")
            categories = set(p.category for p in products if p.category)
            for category in sorted(categories):
                self.category_filter.addItem(category)
            
            # Populate table
            self.display_products(products)
            
            self.status_label.setText(f"Loaded {len(products)} products")
            logger.debug(f"Loaded {len(products)} products")
            
        except SQLAlchemyError as e:
            self.status_label.setText(f"Database error: {str(e)}")
            logger.error(f"Database error when loading products: {str(e)}")
        finally:
            session.close()
    
    def display_products(self, products):
        """Display products in the table widget."""
        self.products_table.setRowCount(0)
        
        for row, product in enumerate(products):
            self.products_table.insertRow(row)
            
            supplier_name = product.supplier.name if product.supplier else "N/A"
            
            # Set data in cells
            self.products_table.setItem(row, 0, QTableWidgetItem(str(product.id)))
            self.products_table.setItem(row, 1, QTableWidgetItem(product.sku))
            self.products_table.setItem(row, 2, QTableWidgetItem(product.name))
            self.products_table.setItem(row, 3, QTableWidgetItem(product.category or "Uncategorized"))
            self.products_table.setItem(row, 4, QTableWidgetItem(supplier_name))
            self.products_table.setItem(row, 5, QTableWidgetItem(f"${product.unit_price:.2f}"))
            
            qty_item = QTableWidgetItem(str(product.quantity_in_stock))
            self.products_table.setItem(row, 6, qty_item)
            
            # Highlight low stock items
            if product.needs_reorder:
                qty_item.setBackground(QColor(255, 200, 200))
            
            self.products_table.setItem(row, 7, QTableWidgetItem(str(product.reorder_level)))
    
    def filter_products(self):
        """Filter products based on search text and filters."""
        try:
            session = get_session()
            query = session.query(Product)
            
            # Apply search filter
            search_text = self.search_input.text().strip().lower()
            if search_text:
                query = query.filter(
                    (Product.name.ilike(f"%{search_text}%")) |
                    (Product.sku.ilike(f"%{search_text}%")) |
                    (Product.description.ilike(f"%{search_text}%"))
                )
            
            # Apply category filter
            selected_category = self.category_filter.currentText()
            if selected_category != "All Categories":
                query = query.filter(Product.category == selected_category)
            
            # Apply low stock filter
            if self.low_stock_filter.isChecked():
                query = query.filter(Product.quantity_in_stock <= Product.reorder_level)
            
            # Execute query
            products = query.all()
            self.display_products(products)
            
            self.status_label.setText(f"Found {len(products)} products")
            
        except SQLAlchemyError as e:
            self.status_label.setText(f"Filter error: {str(e)}")
            logger.error(f"Error when filtering products: {str(e)}")
        finally:
            session.close()
    
    def add_product(self):
        """Open dialog to add a new product."""
        dialog = ProductDialog(self)
        if dialog.exec_():
            self.refresh_required.emit()
            self.status_label.setText("Product added successfully")
    
    def edit_product(self):
        """Open dialog to edit the selected product."""
        selected_rows = self.products_table.selectionModel().selectedRows()
        if not selected_rows:
            self.status_label.setText("No product selected")
            return
        
        row = selected_rows[0].row()
        product_id = int(self.products_table.item(row, 0).text())
        
        try:
            session = get_session()
            product = session.query(Product).get(product_id)
            
            if product:
                dialog = ProductDialog(self, product)
                if dialog.exec_():
                    self.refresh_required.emit()
                    self.status_label.setText("Product updated successfully")
            else:
                self.status_label.setText(f"Product with ID {product_id} not found")
        
        except SQLAlchemyError as e:
            self.status_label.setText(f"Error editing product: {str(e)}")
            logger.error(f"Error when editing product: {str(e)}")
        finally:
            session.close()
    
    def delete_product(self):
        """Delete the selected product."""
        selected_rows = self.products_table.selectionModel().selectedRows()
        if not selected_rows:
            self.status_label.setText("No product selected")
            return
        
        row = selected_rows[0].row()
        product_id = int(self.products_table.item(row, 0).text())
        product_name = self.products_table.item(row, 2).text()
        
        reply = QMessageBox.question(
            self, 
            "Confirm Deletion",
            f"Are you sure you want to delete '{product_name}'?\nThis cannot be undone.",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            session = get_session()
            product = session.query(Product).get(product_id)
            
            if product:
                session.delete(product)
                session.commit()
                self.refresh_required.emit()
                self.status_label.setText(f"Product '{product_name}' deleted")
            else:
                self.status_label.setText(f"Product with ID {product_id} not found")
        
        except SQLAlchemyError as e:
            session.rollback()
            self.status_label.setText(f"Error deleting product: {str(e)}")
            logger.error(f"Error when deleting product: {str(e)}")
        finally:
            session.close()
    
    def generate_qr(self):
        """Generate QR code for the selected product."""
        selected_rows = self.products_table.selectionModel().selectedRows()
        if not selected_rows:
            self.status_label.setText("No product selected")
            return
        
        row = selected_rows[0].row()
        product_id = int(self.products_table.item(row, 0).text())
        
        try:
            session = get_session()
            product = session.query(Product).get(product_id)
            
            if product:
                qr_path = generate_product_qr_code(product)
                
                # Update product with QR code path
                product.qr_code = qr_path
                session.commit()
                
                self.status_label.setText(f"QR code generated for '{product.name}'")
                
                # Show success message with path
                QMessageBox.information(
                    self,
                    "QR Code Generated",
                    f"QR code successfully generated and saved to:\n{qr_path}\n\nThe QR code contains the product's ID and can be scanned for quick access."
                )
                
            else:
                self.status_label.setText(f"Product with ID {product_id} not found")
        
        except Exception as e:
            session.rollback()
            self.status_label.setText(f"Error generating QR code: {str(e)}")
            logger.error(f"Error generating QR code: {str(e)}")
        finally:
            session.close()
    
    def export_data(self):
        """Export inventory data to Excel or CSV."""
        options = QFileDialog.Options()
        file_path, file_type = QFileDialog.getSaveFileName(
            self,
            "Export Inventory Data",
            "",
            "Excel Files (*.xlsx);;CSV Files (*.csv)",
            options=options
        )
        
        if not file_path:
            return
        
        try:
            session = get_session()
            products = session.query(Product).all()
            
            # Prepare data for export
            data = []
            headers = ["ID", "SKU", "Name", "Description", "Category", "Supplier", 
                      "Unit Price", "Quantity", "Reorder Level", "Stock Value"]
            
            for product in products:
                supplier_name = product.supplier.name if product.supplier else "N/A"
                data.append([
                    product.id,
                    product.sku,
                    product.name,
                    product.description,
                    product.category,
                    supplier_name,
                    product.unit_price,
                    product.quantity_in_stock,
                    product.reorder_level,
                    product.stock_value
                ])
            
            # Export based on file type
            if file_path.endswith('.xlsx'):
                export_to_excel(file_path, "Inventory", headers, data)
            elif file_path.endswith('.csv'):
                export_to_csv(file_path, headers, data)
            else:
                # Add extension based on selected filter
                if "Excel" in file_type:
                    file_path += ".xlsx"
                    export_to_excel(file_path, "Inventory", headers, data)
                else:
                    file_path += ".csv"
                    export_to_csv(file_path, headers, data)
            
            self.status_label.setText(f"Data exported to {file_path}")
            
        except Exception as e:
            self.status_label.setText(f"Export error: {str(e)}")
            logger.error(f"Error exporting data: {str(e)}")
        finally:
            session.close()
    
    def refresh_data(self):
        """Public method to refresh the data."""
        self.load_data()
