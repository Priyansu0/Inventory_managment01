"""
Purchase order management tab for creating and managing orders.
"""

import logging
import datetime
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QTableWidget, 
                           QTableWidgetItem, QPushButton, QLabel, QLineEdit, 
                           QHeaderView, QMessageBox, QTabWidget, QComboBox,
                           QDateEdit, QSpinBox, QDoubleSpinBox, QFileDialog,
                           QDialog, QFormLayout, QDialogButtonBox)
from PyQt5.QtCore import Qt, pyqtSignal, QDate
from PyQt5.QtGui import QColor

from sqlalchemy.exc import SQLAlchemyError
from database import get_session
from models import PurchaseOrder, PurchaseItem, Product, Supplier
from utils.export_utils import export_to_excel, export_to_csv
from utils.qr_utils import generate_purchase_order_qr_code

logger = logging.getLogger(__name__)


class PurchaseOrderDialog(QDialog):
    """Dialog for creating or editing purchase orders."""
    
    def __init__(self, parent=None, purchase_order=None):
        super().__init__(parent)
        self.purchase_order = purchase_order
        self.items = []  # Will hold PurchaseItem objects
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Purchase Order" if not self.purchase_order else "Edit Purchase Order")
        self.setMinimumWidth(600)
        
        layout = QVBoxLayout(self)
        
        # Order details section
        order_form = QFormLayout()
        
        # Order number field
        self.order_number = QLineEdit()
        if self.purchase_order:
            self.order_number.setText(self.purchase_order.order_number)
            self.order_number.setReadOnly(True)
        else:
            # Generate a new order number (PO-YYYYMMDD-XXX)
            today = datetime.datetime.now()
            prefix = f"PO-{today.strftime('%Y%m%d')}-"
            
            try:
                session = get_session()
                # Get the count of today's orders to generate the next number
                count = session.query(PurchaseOrder).filter(
                    PurchaseOrder.order_number.like(f"{prefix}%")
                ).count()
                
                self.order_number.setText(f"{prefix}{count+1:03d}")
            except Exception as e:
                logger.error(f"Error generating order number: {str(e)}")
                self.order_number.setText(f"{prefix}001")
            finally:
                session.close()
        
        order_form.addRow("Order Number:", self.order_number)
        
        # Supplier selection
        self.supplier_combo = QComboBox()
        self.load_suppliers()
        order_form.addRow("Supplier:", self.supplier_combo)
        
        # Order date
        self.order_date = QDateEdit()
        self.order_date.setCalendarPopup(True)
        self.order_date.setDate(QDate.currentDate())
        order_form.addRow("Order Date:", self.order_date)
        
        # Expected delivery date
        self.expected_delivery = QDateEdit()
        self.expected_delivery.setCalendarPopup(True)
        self.expected_delivery.setDate(QDate.currentDate().addDays(7))
        order_form.addRow("Expected Delivery:", self.expected_delivery)
        
        # Status selection
        self.status_combo = QComboBox()
        self.status_combo.addItems(["pending", "delivered", "cancelled"])
        order_form.addRow("Status:", self.status_combo)
        
        # Notes field
        self.notes = QLineEdit()
        order_form.addRow("Notes:", self.notes)
        
        layout.addLayout(order_form)
        
        # Items section
        layout.addWidget(QLabel("<b>Order Items</b>"))
        
        # Add items table
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(5)
        self.items_table.setHorizontalHeaderLabels(["Product", "Quantity", "Unit Price", "Total", ""])
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.items_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        
        layout.addWidget(self.items_table)
        
        # Add item button
        self.add_item_btn = QPushButton("Add Item")
        self.add_item_btn.clicked.connect(self.add_item)
        layout.addWidget(self.add_item_btn)
        
        # Total amount display
        self.total_label = QLabel("Total: $0.00")
        layout.addWidget(self.total_label)
        
        # Dialog buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
        
        # Load existing data if editing
        if self.purchase_order:
            self.load_purchase_order_data()
    
    def load_suppliers(self):
        """Load suppliers into combobox."""
        try:
            session = get_session()
            suppliers = session.query(Supplier).filter_by(active=True).all()
            
            self.supplier_combo.clear()
            for supplier in suppliers:
                self.supplier_combo.addItem(supplier.name, supplier.id)
            
            # Select the supplier if editing
            if self.purchase_order and self.purchase_order.supplier_id:
                index = self.supplier_combo.findData(self.purchase_order.supplier_id)
                if index >= 0:
                    self.supplier_combo.setCurrentIndex(index)
            
        except SQLAlchemyError as e:
            logger.error(f"Error loading suppliers: {str(e)}")
        finally:
            session.close()
    
    def load_purchase_order_data(self):
        """Load existing purchase order data when editing."""
        if not self.purchase_order:
            return
        
        # Set order details
        if self.purchase_order.order_date:
            self.order_date.setDate(QDate.fromString(self.purchase_order.order_date.strftime("%Y-%m-%d"), "yyyy-MM-dd"))
        
        if self.purchase_order.expected_delivery:
            self.expected_delivery.setDate(QDate.fromString(self.purchase_order.expected_delivery.strftime("%Y-%m-%d"), "yyyy-MM-dd"))
        
        index = self.status_combo.findText(self.purchase_order.status)
        if index >= 0:
            self.status_combo.setCurrentIndex(index)
        
        if self.purchase_order.notes:
            self.notes.setText(self.purchase_order.notes)
        
        # Load items
        try:
            session = get_session()
            items = session.query(PurchaseItem).filter_by(purchase_order_id=self.purchase_order.id).all()
            
            for item in items:
                self.items.append(item)
            
            self.update_items_table()
            self.update_total()
            
        except SQLAlchemyError as e:
            logger.error(f"Error loading purchase order items: {str(e)}")
        finally:
            session.close()
    
    def add_item(self):
        """Open dialog to add an item to the purchase order."""
        dialog = ItemSelectionDialog(self)
        if dialog.exec_():
            product_id = dialog.product_id
            quantity = dialog.quantity.value()
            unit_price = dialog.price.value()
            
            # Create a temporary item
            new_item = PurchaseItem(
                product_id=product_id,
                quantity=quantity,
                unit_price=unit_price
            )
            
            # Load the product name
            try:
                session = get_session()
                product = session.query(Product).get(product_id)
                if product:
                    new_item.product = product  # Attach product for display
            except SQLAlchemyError as e:
                logger.error(f"Error loading product for item: {str(e)}")
            finally:
                session.close()
            
            self.items.append(new_item)
            self.update_items_table()
            self.update_total()
    
    def update_items_table(self):
        """Update the items table with current items."""
        self.items_table.setRowCount(0)
        
        for row, item in enumerate(self.items):
            self.items_table.insertRow(row)
            
            product_name = item.product.name if hasattr(item, 'product') and item.product else "Unknown"
            
            self.items_table.setItem(row, 0, QTableWidgetItem(product_name))
            self.items_table.setItem(row, 1, QTableWidgetItem(str(item.quantity)))
            self.items_table.setItem(row, 2, QTableWidgetItem(f"${item.unit_price:.2f}"))
            self.items_table.setItem(row, 3, QTableWidgetItem(f"${item.total_price:.2f}"))
            
            # Add remove button
            remove_btn = QPushButton("Remove")
            remove_btn.clicked.connect(lambda _, r=row: self.remove_item(r))
            self.items_table.setCellWidget(row, 4, remove_btn)
    
    def remove_item(self, row):
        """Remove an item from the order."""
        if 0 <= row < len(self.items):
            del self.items[row]
            self.update_items_table()
            self.update_total()
    
    def update_total(self):
        """Update the total amount display."""
        total = sum(item.total_price for item in self.items)
        self.total_label.setText(f"Total: ${total:.2f}")
    
    def accept(self):
        """Save the purchase order when OK is clicked."""
        # Validate that we have a supplier and at least one item
        if self.supplier_combo.currentIndex() < 0:
            QMessageBox.warning(self, "Validation Error", "Please select a supplier.")
            return
        
        if not self.items:
            QMessageBox.warning(self, "Validation Error", "Please add at least one item to the order.")
            return
        
        try:
            session = get_session()
            
            if not self.purchase_order:
                # Create new purchase order
                self.purchase_order = PurchaseOrder(
                    order_number=self.order_number.text(),
                    supplier_id=self.supplier_combo.currentData(),
                    order_date=self.order_date.date().toPyDate(),
                    expected_delivery=self.expected_delivery.date().toPyDate(),
                    status=self.status_combo.currentText(),
                    notes=self.notes.text()
                )
                session.add(self.purchase_order)
                session.flush()  # Get ID without committing
            else:
                # Update existing purchase order
                self.purchase_order.supplier_id = self.supplier_combo.currentData()
                self.purchase_order.order_date = self.order_date.date().toPyDate()
                self.purchase_order.expected_delivery = self.expected_delivery.date().toPyDate()
                self.purchase_order.status = self.status_combo.currentText()
                self.purchase_order.notes = self.notes.text()
                
                # Delete existing items to replace with new ones
                session.query(PurchaseItem).filter_by(purchase_order_id=self.purchase_order.id).delete()
            
            # Add all items
            total_amount = 0
            for item in self.items:
                new_item = PurchaseItem(
                    purchase_order_id=self.purchase_order.id,
                    product_id=item.product_id,
                    quantity=item.quantity,
                    unit_price=item.unit_price
                )
                total_amount += new_item.total_price
                session.add(new_item)
            
            # Update total amount
            self.purchase_order.total_amount = total_amount
            
            session.commit()
            super().accept()
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error saving purchase order: {str(e)}")
            QMessageBox.critical(self, "Database Error", f"Error saving purchase order: {str(e)}")
        finally:
            session.close()


class ItemSelectionDialog(QDialog):
    """Dialog for selecting a product and quantity for purchase order."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.product_id = None
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle("Add Item to Order")
        self.setMinimumWidth(400)
        
        layout = QFormLayout(self)
        
        # Product selection
        self.product_combo = QComboBox()
        self.load_products()
        layout.addRow("Product:", self.product_combo)
        
        # Quantity spinbox
        self.quantity = QSpinBox()
        self.quantity.setMinimum(1)
        self.quantity.setMaximum(10000)
        self.quantity.setValue(1)
        layout.addRow("Quantity:", self.quantity)
        
        # Unit price
        self.price = QDoubleSpinBox()
        self.price.setMinimum(0.01)
        self.price.setMaximum(1000000.00)
        self.price.setDecimals(2)
        self.price.setPrefix("$")
        self.price.setValue(0.00)
        layout.addRow("Unit Price:", self.price)
        
        # Auto-fill price when product selected
        self.product_combo.currentIndexChanged.connect(self.update_price)
        
        # Dialog buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
    
    def load_products(self):
        """Load products into combobox."""
        try:
            session = get_session()
            products = session.query(Product).order_by(Product.name).all()
            
            self.product_combo.clear()
            for product in products:
                self.product_combo.addItem(f"{product.name} (SKU: {product.sku})", product.id)
            
            # Update price for initial selection
            if self.product_combo.count() > 0:
                self.update_price()
            
        except SQLAlchemyError as e:
            logger.error(f"Error loading products: {str(e)}")
        finally:
            session.close()
    
    def update_price(self):
        """Update the price field based on selected product."""
        if self.product_combo.currentIndex() < 0:
            return
        
        product_id = self.product_combo.currentData()
        
        try:
            session = get_session()
            product = session.query(Product).get(product_id)
            
            if product:
                self.price.setValue(product.unit_price)
            
        except SQLAlchemyError as e:
            logger.error(f"Error getting product price: {str(e)}")
        finally:
            session.close()
    
    def accept(self):
        """Save the selected product ID and close."""
        if self.product_combo.currentIndex() < 0:
            QMessageBox.warning(self, "Validation Error", "Please select a product.")
            return
        
        self.product_id = self.product_combo.currentData()
        super().accept()


class ReceiveOrderDialog(QDialog):
    """Dialog for receiving items from a purchase order."""
    
    def __init__(self, parent=None, purchase_order=None):
        super().__init__(parent)
        self.purchase_order = purchase_order
        self.setup_ui()
        
    def setup_ui(self):
        """Set up the dialog UI."""
        self.setWindowTitle(f"Receive Order: {self.purchase_order.order_number}")
        self.setMinimumWidth(600)
        
        layout = QVBoxLayout(self)
        
        # Order info
        order_info = QLabel(f"""
        <h3>Purchase Order: {self.purchase_order.order_number}</h3>
        <p><b>Supplier:</b> {self.purchase_order.supplier.name if self.purchase_order.supplier else 'N/A'}</p>
        <p><b>Order Date:</b> {self.purchase_order.order_date.strftime('%Y-%m-%d') if self.purchase_order.order_date else 'N/A'}</p>
        <p><b>Status:</b> {self.purchase_order.status}</p>
        """)
        layout.addWidget(order_info)
        
        # Items table
        layout.addWidget(QLabel("<b>Order Items</b>"))
        
        self.items_table = QTableWidget()
        self.items_table.setColumnCount(5)
        self.items_table.setHorizontalHeaderLabels([
            "Product", "Ordered Qty", "Already Received", "Receive Now", "Total Received"
        ])
        self.items_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        
        layout.addWidget(self.items_table)
        
        # Load items
        self.load_items()
        
        # Dialog buttons
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        layout.addWidget(self.button_box)
    
    def load_items(self):
        """Load purchase order items into the table."""
        try:
            session = get_session()
            items = session.query(PurchaseItem).filter_by(purchase_order_id=self.purchase_order.id).all()
            
            self.items_table.setRowCount(len(items))
            
            self.receive_spinboxes = []
            self.display_labels = []
            
            for row, item in enumerate(items):
                product = session.query(Product).get(item.product_id)
                product_name = product.name if product else "Unknown"
                
                self.items_table.setItem(row, 0, QTableWidgetItem(product_name))
                self.items_table.setItem(row, 1, QTableWidgetItem(str(item.quantity)))
                self.items_table.setItem(row, 2, QTableWidgetItem(str(item.received_quantity)))
                
                # Spinbox for receiving items
                receive_spinbox = QSpinBox()
                receive_spinbox.setMinimum(0)
                receive_spinbox.setMaximum(item.quantity - item.received_quantity)
                receive_spinbox.setValue(0)
                self.items_table.setCellWidget(row, 3, receive_spinbox)
                self.receive_spinboxes.append(receive_spinbox)
                
                # Display label for total
                display_label = QLabel(str(item.received_quantity))
                self.items_table.setCellWidget(row, 4, display_label)
                self.display_labels.append(display_label)
                
                # Connect the spinbox to update the display label
                receive_spinbox.valueChanged.connect(
                    lambda value, r=row, current=item.received_quantity: 
                    self.display_labels[r].setText(str(current + value))
                )
            
        except SQLAlchemyError as e:
            logger.error(f"Error loading purchase order items: {str(e)}")
        finally:
            session.close()
    
    def accept(self):
        """Process the received items and update inventory."""
        try:
            session = get_session()
            items = session.query(PurchaseItem).filter_by(purchase_order_id=self.purchase_order.id).all()
            
            # Check if any items are being received
            any_received = False
            for i, item in enumerate(items):
                if self.receive_spinboxes[i].value() > 0:
                    any_received = True
                    break
            
            if not any_received:
                QMessageBox.warning(self, "No Items Received", "Please enter quantities to receive, or cancel.")
                return
            
            # Update the received quantities and inventory
            for i, item in enumerate(items):
                received_qty = self.receive_spinboxes[i].value()
                if received_qty > 0:
                    # Update the received quantity on the purchase item
                    item.received_quantity += received_qty
                    
                    # Update the product inventory
                    product = session.query(Product).get(item.product_id)
                    if product:
                        product.quantity_in_stock += received_qty
                        logger.info(f"Updated inventory for {product.name}: +{received_qty} units")
            
            # If all items are fully received, update the order status
            all_received = all(item.received_quantity >= item.quantity for item in items)
            if all_received and self.purchase_order.status == "pending":
                self.purchase_order.status = "delivered"
            
            session.commit()
            super().accept()
            
        except SQLAlchemyError as e:
            session.rollback()
            logger.error(f"Error processing received items: {str(e)}")
            QMessageBox.critical(self, "Database Error", f"Error updating inventory: {str(e)}")
        finally:
            session.close()


class PurchaseTab(QWidget):
    """Tab for managing purchase orders."""
    
    refresh_required = pyqtSignal()
    
    def __init__(self):
        super().__init__()
        self.initUI()
        
    def initUI(self):
        """Initialize the user interface."""
        # Main layout
        main_layout = QVBoxLayout(self)
        
        # Create tabs for different order statuses
        self.status_tabs = QTabWidget()
        
        # Create tabs for different order statuses
        self.all_orders_tab = self.create_orders_tab("all")
        self.pending_orders_tab = self.create_orders_tab("pending")
        self.delivered_orders_tab = self.create_orders_tab("delivered")
        self.cancelled_orders_tab = self.create_orders_tab("cancelled")
        
        self.status_tabs.addTab(self.all_orders_tab, "All Orders")
        self.status_tabs.addTab(self.pending_orders_tab, "Pending")
        self.status_tabs.addTab(self.delivered_orders_tab, "Delivered")
        self.status_tabs.addTab(self.cancelled_orders_tab, "Cancelled")
        
        main_layout.addWidget(self.status_tabs)
        
        # Connect tab changed signal
        self.status_tabs.currentChanged.connect(self.on_tab_changed)
        
        # Buttons layout
        buttons_layout = QHBoxLayout()
        
        self.new_order_btn = QPushButton("New Purchase Order")
        self.new_order_btn.clicked.connect(self.new_purchase_order)
        
        self.edit_order_btn = QPushButton("Edit Order")
        self.edit_order_btn.clicked.connect(self.edit_purchase_order)
        
        self.receive_order_btn = QPushButton("Receive Items")
        self.receive_order_btn.clicked.connect(self.receive_order)
        
        self.generate_qr_btn = QPushButton("Generate QR Code")
        self.generate_qr_btn.clicked.connect(self.generate_qr)
        
        self.export_btn = QPushButton("Export Data")
        self.export_btn.clicked.connect(self.export_data)
        
        buttons_layout.addWidget(self.new_order_btn)
        buttons_layout.addWidget(self.edit_order_btn)
        buttons_layout.addWidget(self.receive_order_btn)
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
    
    def create_orders_tab(self, status):
        """Create a tab for a specific order status."""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Search layout
        search_layout = QHBoxLayout()
        search_label = QLabel("Search:")
        search_input = QLineEdit()
        search_input.setPlaceholderText("Search orders...")
        search_input.textChanged.connect(lambda text, s=status: self.filter_orders(text, s))
        
        search_layout.addWidget(search_label)
        search_layout.addWidget(search_input, 1)
        
        layout.addLayout(search_layout)
        
        # Create the orders table
        orders_table = QTableWidget()
        orders_table.setSelectionBehavior(QTableWidget.SelectRows)
        orders_table.setEditTriggers(QTableWidget.NoEditTriggers)
        orders_table.setColumnCount(7)
        orders_table.setHorizontalHeaderLabels([
            "ID", "Order Number", "Supplier", "Date", "Expected Delivery", 
            "Status", "Total Amount"
        ])
        orders_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        orders_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        orders_table.verticalHeader().setVisible(False)
        orders_table.setAlternatingRowColors(True)
        orders_table.doubleClicked.connect(self.edit_purchase_order)
        
        layout.addWidget(orders_table, 1)
        
        # Store the widget references
        setattr(tab, "search_input", search_input)
        setattr(tab, "orders_table", orders_table)
        setattr(tab, "status", status)
        
        return tab
    
    def load_data(self):
        """Load purchase order data."""
        current_tab = self.status_tabs.currentWidget()
        if current_tab:
            self.load_tab_data(current_tab)
    
    def load_tab_data(self, tab):
        """Load data for the specified tab."""
        status = getattr(tab, "status", "all")
        orders_table = getattr(tab, "orders_table", None)
        search_input = getattr(tab, "search_input", None)
        
        if not orders_table:
            return
        
        try:
            session = get_session()
            query = session.query(PurchaseOrder)
            
            # Apply status filter if not "all"
            if status != "all":
                query = query.filter(PurchaseOrder.status == status)
            
            # Apply search filter if any
            if search_input and search_input.text().strip():
                search_text = search_input.text().strip().lower()
                query = query.filter(
                    (PurchaseOrder.order_number.ilike(f"%{search_text}%"))
                )
            
            # Order by date, newest first
            orders = query.order_by(PurchaseOrder.order_date.desc()).all()
            
            # Clear the table
            orders_table.setRowCount(0)
            
            # Populate the table
            for row, order in enumerate(orders):
                orders_table.insertRow(row)
                
                supplier_name = order.supplier.name if order.supplier else "N/A"
                order_date = order.order_date.strftime('%Y-%m-%d') if order.order_date else "N/A"
                expected_date = order.expected_delivery.strftime('%Y-%m-%d') if order.expected_delivery else "N/A"
                
                orders_table.setItem(row, 0, QTableWidgetItem(str(order.id)))
                orders_table.setItem(row, 1, QTableWidgetItem(order.order_number))
                orders_table.setItem(row, 2, QTableWidgetItem(supplier_name))
                orders_table.setItem(row, 3, QTableWidgetItem(order_date))
                orders_table.setItem(row, 4, QTableWidgetItem(expected_date))
                
                status_item = QTableWidgetItem(order.status)
                if order.status == "pending":
                    status_item.setBackground(QColor(255, 255, 200))  # Light yellow
                elif order.status == "delivered":
                    status_item.setBackground(QColor(200, 255, 200))  # Light green
                elif order.status == "cancelled":
                    status_item.setBackground(QColor(255, 200, 200))  # Light red
                
                orders_table.setItem(row, 5, status_item)
                orders_table.setItem(row, 6, QTableWidgetItem(f"${order.total_amount:.2f}"))
            
            self.status_label.setText(f"Loaded {len(orders)} orders")
            
        except SQLAlchemyError as e:
            self.status_label.setText(f"Database error: {str(e)}")
            logger.error(f"Database error when loading purchase orders: {str(e)}")
        finally:
            session.close()
    
    def on_tab_changed(self, index):
        """Handle tab change event."""
        current_tab = self.status_tabs.widget(index)
        if current_tab:
            self.load_tab_data(current_tab)
    
    def filter_orders(self, text, status):
        """Filter orders based on search text and status."""
        # Find the tab for the specified status
        for i in range(self.status_tabs.count()):
            tab = self.status_tabs.widget(i)
            if getattr(tab, "status", None) == status:
                self.load_tab_data(tab)
                break
    
    def get_current_table(self):
        """Get the orders table from the current tab."""
        current_tab = self.status_tabs.currentWidget()
        if current_tab:
            return getattr(current_tab, "orders_table", None)
        return None
    
    def new_purchase_order(self):
        """Create a new purchase order."""
        dialog = PurchaseOrderDialog(self)
        if dialog.exec_():
            self.refresh_required.emit()
            self.status_label.setText("Purchase order created successfully")
    
    def edit_purchase_order(self):
        """Edit the selected purchase order."""
        table = self.get_current_table()
        if not table:
            return
            
        selected_rows = table.selectionModel().selectedRows()
        if not selected_rows:
            self.status_label.setText("No order selected")
            return
        
        row = selected_rows[0].row()
        order_id = int(table.item(row, 0).text())
        
        try:
            session = get_session()
            order = session.query(PurchaseOrder).get(order_id)
            
            if order:
                # Check if order can be edited
                if order.status == "delivered":
                    QMessageBox.warning(
                        self,
                        "Cannot Edit",
                        "Delivered orders cannot be edited."
                    )
                    return
                
                dialog = PurchaseOrderDialog(self, order)
                if dialog.exec_():
                    self.refresh_required.emit()
                    self.status_label.setText("Purchase order updated successfully")
            else:
                self.status_label.setText(f"Order with ID {order_id} not found")
        
        except SQLAlchemyError as e:
            self.status_label.setText(f"Error editing order: {str(e)}")
            logger.error(f"Error when editing purchase order: {str(e)}")
        finally:
            session.close()
    
    def receive_order(self):
        """Receive items for the selected purchase order."""
        table = self.get_current_table()
        if not table:
            return
            
        selected_rows = table.selectionModel().selectedRows()
        if not selected_rows:
            self.status_label.setText("No order selected")
            return
        
        row = selected_rows[0].row()
        order_id = int(table.item(row, 0).text())
        order_status = table.item(row, 5).text()
        
        # Check if order can be received
        if order_status != "pending":
            QMessageBox.warning(
                self,
                "Cannot Receive",
                f"Only pending orders can be received. This order is {order_status}."
            )
            return
        
        try:
            session = get_session()
            order = session.query(PurchaseOrder).get(order_id)
            
            if order:
                dialog = ReceiveOrderDialog(self, order)
                if dialog.exec_():
                    self.refresh_required.emit()
                    self.status_label.setText("Items received and inventory updated")
            else:
                self.status_label.setText(f"Order with ID {order_id} not found")
        
        except SQLAlchemyError as e:
            self.status_label.setText(f"Error processing order: {str(e)}")
            logger.error(f"Error when receiving purchase order: {str(e)}")
        finally:
            session.close()
    
    def generate_qr(self):
        """Generate QR code for the selected purchase order."""
        table = self.get_current_table()
        if not table:
            return
            
        selected_rows = table.selectionModel().selectedRows()
        if not selected_rows:
            self.status_label.setText("No order selected")
            return
        
        row = selected_rows[0].row()
        order_id = int(table.item(row, 0).text())
        
        try:
            session = get_session()
            order = session.query(PurchaseOrder).get(order_id)
            
            if order:
                qr_path = generate_purchase_order_qr_code(order)
                
                # Update order with QR code path
                order.qr_code = qr_path
                session.commit()
                
                self.status_label.setText(f"QR code generated for order '{order.order_number}'")
                
                # Show success message with path
                QMessageBox.information(
                    self,
                    "QR Code Generated",
                    f"QR code successfully generated and saved to:\n{qr_path}\n\nThe QR code contains the order's ID and can be scanned for quick access."
                )
            else:
                self.status_label.setText(f"Order with ID {order_id} not found")
        
        except Exception as e:
            session.rollback()
            self.status_label.setText(f"Error generating QR code: {str(e)}")
            logger.error(f"Error generating QR code: {str(e)}")
        finally:
            session.close()
    
    def export_data(self):
        """Export purchase order data to Excel or CSV."""
        options = QFileDialog.Options()
        file_path, file_type = QFileDialog.getSaveFileName(
            self,
            "Export Purchase Orders",
            "",
            "Excel Files (*.xlsx);;CSV Files (*.csv)",
            options=options
        )
        
        if not file_path:
            return
        
        try:
            session = get_session()
            
            # Get filter from current tab
            current_tab = self.status_tabs.currentWidget()
            status = getattr(current_tab, "status", "all")
            
            query = session.query(PurchaseOrder)
            if status != "all":
                query = query.filter(PurchaseOrder.status == status)
            
            orders = query.order_by(PurchaseOrder.order_date.desc()).all()
            
            # Prepare data for export
            data = []
            headers = ["ID", "Order Number", "Supplier", "Order Date", "Expected Delivery", 
                      "Status", "Total Amount", "Notes"]
            
            for order in orders:
                supplier_name = order.supplier.name if order.supplier else "N/A"
                order_date = order.order_date.strftime('%Y-%m-%d') if order.order_date else "N/A"
                expected_date = order.expected_delivery.strftime('%Y-%m-%d') if order.expected_delivery else "N/A"
                
                data.append([
                    order.id,
                    order.order_number,
                    supplier_name,
                    order_date,
                    expected_date,
                    order.status,
                    order.total_amount,
                    order.notes
                ])
            
            # Export based on file type
            if file_path.endswith('.xlsx'):
                export_to_excel(file_path, "Purchase Orders", headers, data)
            elif file_path.endswith('.csv'):
                export_to_csv(file_path, headers, data)
            else:
                # Add extension based on selected filter
                if "Excel" in file_type:
                    file_path += ".xlsx"
                    export_to_excel(file_path, "Purchase Orders", headers, data)
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
