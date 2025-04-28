"""
Supplier management tab for managing vendor information.
"""

import logging
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                           QTableWidgetItem, QPushButton, QLabel, QLineEdit, 
                           QHeaderView, QMessageBox, QFormLayout, QTextEdit,
                           QDialog, QDialogButtonBox, QFileDialog, QCheckBox)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor

from sqlalchemy.exc import SQLAlchemyError
from database import get_session
from models import Supplier, Product
from utils.export_utils import export_to_excel, export_to_csv

logger = logging.getLogger(__name__)


class SupplierDialog(QDialog):
    """Dialog for adding or editing a supplier."""
    
    def __init__(self, parent=None, supplier=None):
        super().__init__(parent)
        self.supplier = supplier
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Add Supplier" if not self.supplier else "Edit Supplier")
        self.setMinimumWidth(500)
        
        layout = QVBoxLayout(self)
        
        form_layout = QFormLayout()
        
        # Name field
        self.name_input = QLineEdit()
        form_layout.addRow("Name:", self.name_input)
        
        # Contact name field
        self.contact_name_input = QLineEdit()
        form_layout.addRow("Contact Name:", self.contact_name_input)
        
        # Email field
        self.email_input = QLineEdit()
        form_layout.addRow("Email:", self.email_input)
        
        # Phone field
        self.phone_input = QLineEdit()
        form_layout.addRow("Phone:", self.phone_input)
        
        # Address field
        self.address_input = QTextEdit()
        self.address_input.setMaximumHeight(100)
        form_layout.addRow("Address:", self.address_input)
        
        # Notes field
        self.notes_input = QTextEdit()
        self.notes_input.setMaximumHeight(100)
        form_layout.addRow("Notes:", self.notes_input)
        
        # Active checkbox
        self.active_checkbox = QCheckBox("Active")
        self.active_checkbox.setChecked(True)
        form_layout.addRow("Status:", self.active_checkbox)
        
        layout.addLayout(form_layout)
        
        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        
        # Fill data if editing
        if self.supplier:
            self.name_input.setText(self.supplier.name)
            self.contact_name_input.setText(self.supplier.contact_name or "")
            self.email_input.setText(self.supplier.email or "")
            self.phone_input.setText(self.supplier.phone or "")
            self.address_input.setText(self.supplier.address or "")
            self.notes_input.setText(self.supplier.notes or "")
            self.active_checkbox.setChecked(self.supplier.active)
    
    def accept(self):
        """Save the supplier data when OK is clicked."""
        # Validate required fields
        if not self.name_input.text().strip():
            QMessageBox.warning(self, "Validation Error", "Supplier name is required.")
            return
        
        try:
            session = get_session()
            
            if not self.supplier:
                # Create new supplier
                self.supplier = Supplier(
                    name=self.name_input.text().strip(),
                    contact_name=self.contact_name_input.text().strip(),
                    email=self.email_input.text().strip(),
                    phone=self.phone_input.text().strip(),
                    address=self.address_input.toPlainText().strip(),
                    notes=self.notes_input.toPlainText().strip(),
                    active=self.active_checkbox.isChecked()
                )
                session.add(self.supplier)
            else:
                # Update existing supplier
                self.supplier.name = self.name_input.text().strip()
                self.supplier.contact_name = self.contact_name_input.text().strip()
                self.supplier.email = self.email_input.text().strip()
                self.supplier.phone = self.phone_input.text().strip()
                self.supplier.address = self.address_input.toPlainText().strip()
                self.supplier.notes = self.notes_input.toPlainText().strip()
                self.supplier.active = self.active_checkbox.isChecked()
            
            session.commit()
            super().accept()
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error saving supplier: {str(e)}")
            QMessageBox.critical(self, "Database Error", f"Error saving supplier: {str(e)}")
        finally:
            session.close()


class SupplierProductsDialog(QDialog):
    """Dialog for viewing products from a supplier."""
    
    def __init__(self, parent=None, supplier=None):
        super().__init__(parent)
        self.supplier = supplier
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle(f"Products from {self.supplier.name}")
        self.setMinimumSize(600, 400)
        
        layout = QVBoxLayout(self)
        
        # Supplier info
        info_label = QLabel(f"""
        <h3>Supplier: {self.supplier.name}</h3>
        <p><b>Contact:</b> {self.supplier.contact_name or 'N/A'}</p>
        <p><b>Email:</b> {self.supplier.email or 'N/A'}</p>
        <p><b>Phone:</b> {self.supplier.phone or 'N/A'}</p>
        """)
        layout.addWidget(info_label)
        
        # Products table
        self.products_table = QTableWidget()
        self.products_table.setColumnCount(5)
        self.products_table.setHorizontalHeaderLabels([
            "ID", "SKU", "Name", "Unit Price", "Stock"
        ])
        self.products_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.products_table.setAlternatingRowColors(True)
        
        layout.addWidget(self.products_table, 1)
        
        # Load products
        self.load_products()
        
        # Buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Close)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
    
    def load_products(self):
        """Load products from this supplier."""
        try:
            session = get_session()
            products = session.query(Product).filter_by(supplier_id=self.supplier.id).all()
            
            self.products_table.setRowCount(len(products))
            
            for row, product in enumerate(products):
                self.products_table.setItem(row, 0, QTableWidgetItem(str(product.id)))
                self.products_table.setItem(row, 1, QTableWidgetItem(product.sku))
                self.products_table.setItem(row, 2, QTableWidgetItem(product.name))
                self.products_table.setItem(row, 3, QTableWidgetItem(f"${product.unit_price:.2f}"))
                
                qty_item = QTableWidgetItem(str(product.quantity_in_stock))
                if product.needs_reorder:
                    qty_item.setBackground(QColor(255, 200, 200))
                self.products_table.setItem(row, 4, qty_item)
            
        except SQLAlchemyError as e:
            logger.error(f"Error loading supplier products: {str(e)}")
            QMessageBox.critical(self, "Database Error", f"Error loading products: {str(e)}")
        finally:
            session.close()


class SupplierTab(QWidget):
    """Tab for managing suppliers."""
    
    refresh_required = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        """Initialize the user interface."""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Search layout
        search_layout = QHBoxLayout()
        
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Search suppliers...")
        self.search_input.textChanged.connect(self.filter_suppliers)
        
        self.active_filter = QCheckBox("Show active only")
        self.active_filter.setChecked(True)
        self.active_filter.stateChanged.connect(self.filter_suppliers)
        
        search_layout.addWidget(QLabel("Search:"))
        search_layout.addWidget(self.search_input, 1)
        search_layout.addWidget(self.active_filter)
        
        main_layout.addLayout(search_layout)
        
        # Suppliers table
        self.suppliers_table = QTableWidget()
        self.suppliers_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.suppliers_table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.suppliers_table.setColumnCount(6)
        self.suppliers_table.setHorizontalHeaderLabels([
            "ID", "Name", "Contact", "Email", "Phone", "Status"
        ])
        self.suppliers_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.suppliers_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.suppliers_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        self.suppliers_table.verticalHeader().setVisible(False)
        self.suppliers_table.setAlternatingRowColors(True)
        self.suppliers_table.doubleClicked.connect(self.edit_supplier)
        
        main_layout.addWidget(self.suppliers_table, 1)
        
        # Buttons layout
        buttons_layout = QHBoxLayout()
        
        self.add_btn = QPushButton("Add Supplier")
        self.add_btn.clicked.connect(self.add_supplier)
        
        self.edit_btn = QPushButton("Edit Selected")
        self.edit_btn.clicked.connect(self.edit_supplier)
        
        self.view_products_btn = QPushButton("View Products")
        self.view_products_btn.clicked.connect(self.view_supplier_products)
        
        self.toggle_status_btn = QPushButton("Toggle Status")
        self.toggle_status_btn.clicked.connect(self.toggle_supplier_status)
        
        self.export_btn = QPushButton("Export Data")
        self.export_btn.clicked.connect(self.export_data)
        
        buttons_layout.addWidget(self.add_btn)
        buttons_layout.addWidget(self.edit_btn)
        buttons_layout.addWidget(self.view_products_btn)
        buttons_layout.addWidget(self.toggle_status_btn)
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
        """Load supplier data from the database."""
        try:
            session = get_session()
            
            # Apply active filter
            query = session.query(Supplier)
            if self.active_filter.isChecked():
                query = query.filter_by(active=True)
            
            suppliers = query.order_by(Supplier.name).all()
            
            self.display_suppliers(suppliers)
            
            self.status_label.setText(f"Loaded {len(suppliers)} suppliers")
            
        except SQLAlchemyError as e:
            self.status_label.setText(f"Database error: {str(e)}")
            logger.error(f"Database error when loading suppliers: {str(e)}")
        finally:
            session.close()
    
    def display_suppliers(self, suppliers):
        """Display suppliers in the table widget."""
        self.suppliers_table.setRowCount(0)
        
        for row, supplier in enumerate(suppliers):
            self.suppliers_table.insertRow(row)
            
            # Set data in cells
            self.suppliers_table.setItem(row, 0, QTableWidgetItem(str(supplier.id)))
            self.suppliers_table.setItem(row, 1, QTableWidgetItem(supplier.name))
            self.suppliers_table.setItem(row, 2, QTableWidgetItem(supplier.contact_name or ""))
            self.suppliers_table.setItem(row, 3, QTableWidgetItem(supplier.email or ""))
            self.suppliers_table.setItem(row, 4, QTableWidgetItem(supplier.phone or ""))
            
            status_text = "Active" if supplier.active else "Inactive"
            status_item = QTableWidgetItem(status_text)
            status_item.setBackground(QColor(200, 255, 200) if supplier.active else QColor(255, 200, 200))
            self.suppliers_table.setItem(row, 5, status_item)
    
    def filter_suppliers(self):
        """Filter suppliers based on search text."""
        try:
            session = get_session()
            query = session.query(Supplier)
            
            # Apply search filter
            search_text = self.search_input.text().strip().lower()
            if search_text:
                query = query.filter(
                    (Supplier.name.ilike(f"%{search_text}%")) |
                    (Supplier.contact_name.ilike(f"%{search_text}%")) |
                    (Supplier.email.ilike(f"%{search_text}%")) |
                    (Supplier.phone.ilike(f"%{search_text}%"))
                )
            
            # Apply active filter
            if self.active_filter.isChecked():
                query = query.filter_by(active=True)
            
            # Execute query
            suppliers = query.order_by(Supplier.name).all()
            self.display_suppliers(suppliers)
            
            self.status_label.setText(f"Found {len(suppliers)} suppliers")
            
        except SQLAlchemyError as e:
            self.status_label.setText(f"Filter error: {str(e)}")
            logger.error(f"Error when filtering suppliers: {str(e)}")
        finally:
            session.close()
    
    def add_supplier(self):
        """Open dialog to add a new supplier."""
        dialog = SupplierDialog(self)
        if dialog.exec_():
            self.refresh_required.emit()
            self.status_label.setText("Supplier added successfully")
    
    def edit_supplier(self):
        """Open dialog to edit the selected supplier."""
        selected_rows = self.suppliers_table.selectionModel().selectedRows()
        if not selected_rows:
            self.status_label.setText("No supplier selected")
            return
        
        row = selected_rows[0].row()
        supplier_id = int(self.suppliers_table.item(row, 0).text())
        
        try:
            session = get_session()
            supplier = session.query(Supplier).get(supplier_id)
            
            if supplier:
                dialog = SupplierDialog(self, supplier)
                if dialog.exec_():
                    self.refresh_required.emit()
                    self.status_label.setText("Supplier updated successfully")
            else:
                self.status_label.setText(f"Supplier with ID {supplier_id} not found")
        
        except SQLAlchemyError as e:
            self.status_label.setText(f"Error editing supplier: {str(e)}")
            logger.error(f"Error when editing supplier: {str(e)}")
        finally:
            session.close()
    
    def view_supplier_products(self):
        """View products from the selected supplier."""
        selected_rows = self.suppliers_table.selectionModel().selectedRows()
        if not selected_rows:
            self.status_label.setText("No supplier selected")
            return
        
        row = selected_rows[0].row()
        supplier_id = int(self.suppliers_table.item(row, 0).text())
        
        try:
            session = get_session()
            supplier = session.query(Supplier).get(supplier_id)
            
            if supplier:
                dialog = SupplierProductsDialog(self, supplier)
                dialog.exec_()
            else:
                self.status_label.setText(f"Supplier with ID {supplier_id} not found")
        
        except SQLAlchemyError as e:
            self.status_label.setText(f"Error loading supplier products: {str(e)}")
            logger.error(f"Error when loading supplier products: {str(e)}")
        finally:
            session.close()
    
    def toggle_supplier_status(self):
        """Toggle the active status of the selected supplier."""
        selected_rows = self.suppliers_table.selectionModel().selectedRows()
        if not selected_rows:
            self.status_label.setText("No supplier selected")
            return
        
        row = selected_rows[0].row()
        supplier_id = int(self.suppliers_table.item(row, 0).text())
        supplier_name = self.suppliers_table.item(row, 1).text()
        current_status = self.suppliers_table.item(row, 5).text()
        
        new_status = current_status != "Active"  # Toggle status
        status_text = "activate" if new_status else "deactivate"
        
        reply = QMessageBox.question(
            self, 
            "Confirm Status Change",
            f"Are you sure you want to {status_text} supplier '{supplier_name}'?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply != QMessageBox.Yes:
            return
        
        try:
            session = get_session()
            supplier = session.query(Supplier).get(supplier_id)
            
            if supplier:
                supplier.active = new_status
                session.commit()
                self.refresh_required.emit()
                
                status_verb = "activated" if new_status else "deactivated"
                self.status_label.setText(f"Supplier '{supplier_name}' {status_verb}")
            else:
                self.status_label.setText(f"Supplier with ID {supplier_id} not found")
        
        except SQLAlchemyError as e:
            session.rollback()
            self.status_label.setText(f"Error updating supplier status: {str(e)}")
            logger.error(f"Error when updating supplier status: {str(e)}")
        finally:
            session.close()
    
    def export_data(self):
        """Export supplier data to Excel or CSV."""
        options = QFileDialog.Options()
        file_path, file_type = QFileDialog.getSaveFileName(
            self,
            "Export Supplier Data",
            "",
            "Excel Files (*.xlsx);;CSV Files (*.csv)",
            options=options
        )
        
        if not file_path:
            return
        
        try:
            session = get_session()
            
            # Use current filter settings
            query = session.query(Supplier)
            if self.active_filter.isChecked():
                query = query.filter_by(active=True)
                
            search_text = self.search_input.text().strip().lower()
            if search_text:
                query = query.filter(
                    (Supplier.name.ilike(f"%{search_text}%")) |
                    (Supplier.contact_name.ilike(f"%{search_text}%")) |
                    (Supplier.email.ilike(f"%{search_text}%")) |
                    (Supplier.phone.ilike(f"%{search_text}%"))
                )
            
            suppliers = query.order_by(Supplier.name).all()
            
            # Prepare data for export
            data = []
            headers = ["ID", "Name", "Contact Name", "Email", "Phone", "Address", "Notes", "Status"]
            
            for supplier in suppliers:
                data.append([
                    supplier.id,
                    supplier.name,
                    supplier.contact_name,
                    supplier.email,
                    supplier.phone,
                    supplier.address,
                    supplier.notes,
                    "Active" if supplier.active else "Inactive"
                ])
            
            # Export based on file type
            if file_path.endswith('.xlsx'):
                export_to_excel(file_path, "Suppliers", headers, data)
            elif file_path.endswith('.csv'):
                export_to_csv(file_path, headers, data)
            else:
                # Add extension based on selected filter
                if "Excel" in file_type:
                    file_path += ".xlsx"
                    export_to_excel(file_path, "Suppliers", headers, data)
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
