"""
Dialog windows for the Inventory Management System.
"""

import logging
import os
from PyQt5.QtWidgets import (QDialog, QFormLayout, QVBoxLayout, QHBoxLayout, QLabel, 
                           QLineEdit, QTextEdit, QSpinBox, QDoubleSpinBox, QComboBox, 
                           QPushButton, QDialogButtonBox, QFileDialog, QMessageBox,
                           QCheckBox, QWidget, QTabWidget)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QPixmap, QImage

from sqlalchemy.exc import SQLAlchemyError
from database import get_session
from models import Product, Supplier
from utils.qr_utils import generate_product_qr_code
from gui.qr_scanner import QRScannerDialog

logger = logging.getLogger(__name__)


class ProductDialog(QDialog):
    """Dialog for adding or editing a product."""
    
    def __init__(self, parent=None, product=None):
        super().__init__(parent)
        self.product = product
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Add Product" if not self.product else "Edit Product")
        self.setMinimumWidth(500)
        
        # Create tab widget for organization
        tab_widget = QTabWidget(self)
        
        # Main Details Tab
        details_widget = QWidget()
        details_layout = QFormLayout(details_widget)
        
        # SKU field
        self.sku_input = QLineEdit()
        details_layout.addRow("SKU*:", self.sku_input)
        
        # Name field
        self.name_input = QLineEdit()
        details_layout.addRow("Name*:", self.name_input)
        
        # Category dropdown/input
        self.category_combo = QComboBox()
        self.category_combo.setEditable(True)
        self.load_categories()
        details_layout.addRow("Category:", self.category_combo)
        
        # Description field
        self.description_input = QTextEdit()
        self.description_input.setMaximumHeight(100)
        details_layout.addRow("Description:", self.description_input)
        
        # Unit price field
        self.price_input = QDoubleSpinBox()
        self.price_input.setRange(0.01, 1000000.00)
        self.price_input.setDecimals(2)
        self.price_input.setPrefix("$")
        details_layout.addRow("Unit Price*:", self.price_input)
        
        # Inventory Tab
        inventory_widget = QWidget()
        inventory_layout = QFormLayout(inventory_widget)
        
        # Quantity in stock
        self.stock_input = QSpinBox()
        self.stock_input.setRange(0, 1000000)
        inventory_layout.addRow("Quantity in Stock:", self.stock_input)
        
        # Reorder level
        self.reorder_level_input = QSpinBox()
        self.reorder_level_input.setRange(0, 1000000)
        self.reorder_level_input.setValue(5)  # Default reorder level
        inventory_layout.addRow("Reorder Level:", self.reorder_level_input)
        
        # Reorder quantity
        self.reorder_qty_input = QSpinBox()
        self.reorder_qty_input.setRange(1, 1000000)
        self.reorder_qty_input.setValue(10)  # Default reorder quantity
        inventory_layout.addRow("Reorder Quantity:", self.reorder_qty_input)
        
        # Supplier Tab
        supplier_widget = QWidget()
        supplier_layout = QFormLayout(supplier_widget)
        
        # Supplier selection
        self.supplier_combo = QComboBox()
        self.supplier_combo.addItem("-- No Supplier --", None)
        self.load_suppliers()
        supplier_layout.addRow("Supplier:", self.supplier_combo)
        
        # QR Code Tab
        qr_widget = QWidget()
        qr_layout = QVBoxLayout(qr_widget)
        
        # QR code display
        self.qr_label = QLabel("No QR code generated yet")
        self.qr_label.setAlignment(Qt.AlignCenter)
        self.qr_label.setMinimumHeight(200)
        qr_layout.addWidget(self.qr_label)
        
        # QR code buttons
        qr_buttons = QHBoxLayout()
        
        self.generate_qr_btn = QPushButton("Generate QR Code")
        self.generate_qr_btn.setEnabled(False)  # Only enable after save
        self.generate_qr_btn.clicked.connect(self.generate_qr_code)
        
        self.scan_qr_btn = QPushButton("Scan QR Code")
        self.scan_qr_btn.clicked.connect(self.scan_qr_code)
        
        qr_buttons.addWidget(self.generate_qr_btn)
        qr_buttons.addWidget(self.scan_qr_btn)
        qr_layout.addLayout(qr_buttons)
        
        # Add tabs
        tab_widget.addTab(details_widget, "Details")
        tab_widget.addTab(inventory_widget, "Inventory")
        tab_widget.addTab(supplier_widget, "Supplier")
        tab_widget.addTab(qr_widget, "QR Code")
        
        # Create main layout
        main_layout = QVBoxLayout(self)
        main_layout.addWidget(tab_widget)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        main_layout.addWidget(button_box)
        
        # Fill fields if editing existing product
        if self.product:
            self.populate_fields()
            self.generate_qr_btn.setEnabled(True)
            self.load_qr_code()
    
    def load_categories(self):
        """Load unique categories into the combo box."""
        try:
            session = get_session()
            categories = session.query(Product.category).distinct().all()
            
            # Add categories to combo box
            for category in categories:
                if category[0]:  # Skip None values
                    self.category_combo.addItem(category[0])
            
        except SQLAlchemyError as e:
            logger.error(f"Error loading categories: {str(e)}")
        finally:
            session.close()
    
    def load_suppliers(self):
        """Load suppliers into the combo box."""
        try:
            session = get_session()
            suppliers = session.query(Supplier).filter_by(active=True).order_by(Supplier.name).all()
            
            # Add suppliers to combo box
            for supplier in suppliers:
                self.supplier_combo.addItem(supplier.name, supplier.id)
            
        except SQLAlchemyError as e:
            logger.error(f"Error loading suppliers: {str(e)}")
        finally:
            session.close()
    
    def populate_fields(self):
        """Populate fields with existing product data."""
        if not self.product:
            return
        
        # Set field values
        self.sku_input.setText(self.product.sku)
        self.name_input.setText(self.product.name)
        
        # Set category
        if self.product.category:
            index = self.category_combo.findText(self.product.category)
            if index >= 0:
                self.category_combo.setCurrentIndex(index)
            else:
                self.category_combo.addItem(self.product.category)
                self.category_combo.setCurrentText(self.product.category)
        
        self.description_input.setText(self.product.description or "")
        self.price_input.setValue(self.product.unit_price)
        self.stock_input.setValue(self.product.quantity_in_stock)
        self.reorder_level_input.setValue(self.product.reorder_level)
        self.reorder_qty_input.setValue(self.product.reorder_quantity)
        
        # Set supplier
        if self.product.supplier_id:
            index = self.supplier_combo.findData(self.product.supplier_id)
            if index >= 0:
                self.supplier_combo.setCurrentIndex(index)
    
    def load_qr_code(self):
        """Load existing QR code if available."""
        if not self.product or not self.product.qr_code:
            return
        
        try:
            if os.path.exists(self.product.qr_code):
                pixmap = QPixmap(self.product.qr_code)
                self.qr_label.setPixmap(pixmap.scaled(
                    200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation
                ))
            else:
                self.qr_label.setText("QR code file not found")
        except Exception as e:
            logger.error(f"Error loading QR code: {str(e)}")
            self.qr_label.setText("Error loading QR code")
    
    def generate_qr_code(self):
        """Generate QR code for the product."""
        if not self.product:
            QMessageBox.warning(self, "Warning", "Product must be saved before generating a QR code.")
            return
        
        try:
            qr_path = generate_product_qr_code(self.product)
            
            # Update product in database
            session = get_session()
            product = session.query(Product).get(self.product.id)
            if product:
                product.qr_code = qr_path
                session.commit()
                
                # Update display
                pixmap = QPixmap(qr_path)
                self.qr_label.setPixmap(pixmap.scaled(
                    200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation
                ))
                
                QMessageBox.information(self, "QR Code Generated", 
                                     f"QR code generated and saved to:\n{qr_path}")
            
        except Exception as e:
            logger.error(f"Error generating QR code: {str(e)}")
            QMessageBox.critical(self, "Error", f"Failed to generate QR code: {str(e)}")
        finally:
            session.close()
    
    def scan_qr_code(self):
        """Open QR code scanner dialog."""
        scanner = QRScannerDialog(self)
        scanner.exec_()
    
    def accept(self):
        """Save the product when OK is clicked."""
        # Validate required fields
        if not self.sku_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "SKU is required.")
            return
        
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Name is required.")
            return
        
        if self.price_input.value() <= 0:
            QMessageBox.warning(self, "Validation Error", "Unit price must be greater than zero.")
            return
        
        try:
            session = get_session()
            
            # Check if SKU exists (for new products or changed SKUs)
            sku = self.sku_input.text().strip()
            if not self.product or sku != self.product.sku:
                existing = session.query(Product).filter_by(sku=sku).first()
                if existing:
                    QMessageBox.warning(self, "Validation Error", f"SKU '{sku}' already exists.")
                    return
            
            # Get supplier ID
            supplier_id = self.supplier_combo.currentData()
            
            if not self.product:
                # Create new product
                self.product = Product(
                    sku=sku,
                    name=self.name_input.text().strip(),
                    category=self.category_combo.currentText() if self.category_combo.currentText() else None,
                    description=self.description_input.toPlainText().strip(),
                    unit_price=self.price_input.value(),
                    quantity_in_stock=self.stock_input.value(),
                    reorder_level=self.reorder_level_input.value(),
                    reorder_quantity=self.reorder_qty_input.value(),
                    supplier_id=supplier_id if supplier_id else None
                )
                session.add(self.product)
            else:
                # Update existing product
                self.product.sku = sku
                self.product.name = self.name_input.text().strip()
                self.product.category = self.category_combo.currentText() if self.category_combo.currentText() else None
                self.product.description = self.description_input.toPlainText().strip()
                self.product.unit_price = self.price_input.value()
                self.product.quantity_in_stock = self.stock_input.value()
                self.product.reorder_level = self.reorder_level_input.value()
                self.product.reorder_quantity = self.reorder_qty_input.value()
                self.product.supplier_id = supplier_id if supplier_id else None
            
            session.commit()
            
            # Enable QR code generation after saving
            self.generate_qr_btn.setEnabled(True)
            
            super().accept()
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error saving product: {str(e)}")
            QMessageBox.critical(self, "Database Error", f"Error saving product: {str(e)}")
        finally:
            session.close()
