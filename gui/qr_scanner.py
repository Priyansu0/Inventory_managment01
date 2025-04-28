"""
QR code scanner interface using webcam.
"""

import logging
import threading
import time
import cv2
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, 
                           QComboBox, QMessageBox)
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, pyqtSlot

# Check if pyzbar is available
from utils.qr_utils import PYZBAR_AVAILABLE, decode

from sqlalchemy.exc import SQLAlchemyError
from database import get_session
from models import Product, PurchaseOrder

logger = logging.getLogger(__name__)


class QRScannerDialog(QDialog):
    """Dialog for scanning QR codes using webcam."""
    
    scan_complete = pyqtSignal(str, str)  # Signal for scan completion (type, id)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.cap = None
        self.capture_thread = None
        self.camera_active = False
        self.available_cameras = []
        self.pyzbar_available = PYZBAR_AVAILABLE
        self.setupUI()
    
    def setupUI(self):
        """Set up the scanner dialog UI."""
        self.setWindowTitle("QR Code Scanner")
        self.setMinimumSize(640, 520)
        
        layout = QVBoxLayout(self)
        
        # Show warning if pyzbar is not available
        if not self.pyzbar_available:
            warning_label = QLabel(
                "WARNING: QR code scanning functionality is limited because the pyzbar library is not available.\n"
                "You can still use the camera but QR codes will not be detected."
            )
            warning_label.setStyleSheet("color: red; font-weight: bold; background-color: #FFEEEE; padding: 10px;")
            warning_label.setWordWrap(True)
            warning_label.setAlignment(Qt.AlignCenter)
            layout.addWidget(warning_label)
        
        # Camera selection
        camera_layout = QHBoxLayout()
        camera_layout.addWidget(QLabel("Select Camera:"))
        
        self.camera_combo = QComboBox()
        self.refresh_cameras()
        camera_layout.addWidget(self.camera_combo, 1)
        
        self.refresh_btn = QPushButton("Refresh List")
        self.refresh_btn.clicked.connect(self.refresh_cameras)
        camera_layout.addWidget(self.refresh_btn)
        
        layout.addLayout(camera_layout)
        
        # Video feed
        self.video_label = QLabel()
        self.video_label.setAlignment(Qt.AlignCenter)
        self.video_label.setText("Camera feed will appear here")
        self.video_label.setStyleSheet("background-color: black; color: white;")
        layout.addWidget(self.video_label, 1)
        
        # Scanner status
        self.status_label = QLabel("Ready to scan")
        if not self.pyzbar_available:
            self.status_label.setText("QR scanning is disabled - pyzbar library not available")
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Control buttons
        buttons_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("Start Camera")
        self.start_btn.clicked.connect(self.toggle_camera)
        buttons_layout.addWidget(self.start_btn)
        
        self.close_btn = QPushButton("Close")
        self.close_btn.clicked.connect(self.close_scanner)
        buttons_layout.addWidget(self.close_btn)
        
        layout.addLayout(buttons_layout)
        
        # Timer for updating the video feed
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_frame)
        
        # Connect scan complete signal
        self.scan_complete.connect(self.on_scan_complete)
    
    def refresh_cameras(self):
        """Find available cameras."""
        self.camera_combo.clear()
        self.available_cameras = []
        
        # Try the first 5 camera indexes
        for i in range(5):
            try:
                cap = cv2.VideoCapture(i)
                if cap.isOpened():
                    self.available_cameras.append(i)
                    self.camera_combo.addItem(f"Camera {i}", i)
                    cap.release()
            except Exception:
                pass
        
        if not self.available_cameras:
            self.camera_combo.addItem("No cameras found")
            self.start_btn.setEnabled(False)
        else:
            self.start_btn.setEnabled(True)
    
    def toggle_camera(self):
        """Start or stop the camera."""
        if not self.camera_active:
            # Start camera
            if not self.available_cameras:
                QMessageBox.warning(self, "No Camera", "No cameras available.")
                return
            
            camera_index = self.camera_combo.currentData()
            if camera_index is None:
                return
            
            try:
                self.cap = cv2.VideoCapture(camera_index)
                if not self.cap.isOpened():
                    QMessageBox.warning(self, "Camera Error", f"Failed to open camera {camera_index}.")
                    return
                
                # Start the video feed timer
                self.camera_active = True
                self.start_btn.setText("Stop Camera")
                self.status_label.setText("Scanning for QR codes...")
                self.timer.start(30)  # Update every 30ms
                
            except Exception as e:
                QMessageBox.critical(self, "Camera Error", f"Error starting camera: {str(e)}")
                logger.error(f"Error starting camera: {str(e)}")
        else:
            # Stop camera
            self.stop_camera()
    
    def stop_camera(self):
        """Stop the camera and release resources."""
        self.timer.stop()
        if self.cap:
            self.cap.release()
        self.camera_active = False
        self.start_btn.setText("Start Camera")
        self.status_label.setText("Ready to scan")
        self.video_label.setText("Camera feed will appear here")
    
    def update_frame(self):
        """Update the video frame and scan for QR codes."""
        if not self.cap or not self.cap.isOpened():
            self.stop_camera()
            return
        
        ret, frame = self.cap.read()
        if not ret:
            self.stop_camera()
            return
        
        # Scan for QR codes if pyzbar is available
        if self.pyzbar_available:
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                qr_codes = decode(gray)
                
                for qr in qr_codes:
                    # Draw bounding box
                    points = qr.polygon
                    if len(points) > 4:
                        hull = cv2.convexHull(np.array([point for point in points], dtype=np.float32))
                        cv2.polylines(frame, [hull], True, (0, 255, 0), 2)
                    else:
                        cv2.polylines(frame, [np.array(points)], True, (0, 255, 0), 2)
                    
                    # Extract data
                    qr_data = qr.data.decode('utf-8')
                    
                    # Process the QR code data
                    self.process_qr_data(qr_data)
                    
                    # Display data on frame
                    cv2.putText(frame, qr_data, (qr.rect.left, qr.rect.top - 10),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
            except Exception as e:
                logger.error(f"Error scanning QR code: {str(e)}")
        
        # Convert frame to QImage and display
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        h, w, ch = rgb_frame.shape
        bytes_per_line = ch * w
        q_img = QImage(rgb_frame.data, w, h, bytes_per_line, QImage.Format_RGB888)
        self.video_label.setPixmap(QPixmap.fromImage(q_img).scaled(
            self.video_label.width(), self.video_label.height(),
            Qt.KeepAspectRatio, Qt.SmoothTransformation
        ))
    
    def process_qr_data(self, qr_data):
        """Process the scanned QR code data."""
        try:
            # Expected format: "type:id", e.g., "product:123" or "order:456"
            parts = qr_data.split(":")
            if len(parts) == 2:
                data_type, data_id = parts
                
                # Emit signal with scan result
                self.scan_complete.emit(data_type, data_id)
                
                # Pause scanning briefly
                self.timer.stop()
                QTimer.singleShot(2000, lambda: self.timer.start(30))
            
        except Exception as e:
            logger.error(f"Error processing QR data: {str(e)}")
    
    @pyqtSlot(str, str)
    def on_scan_complete(self, data_type, data_id):
        """Handle the completed scan."""
        self.status_label.setText(f"Scanned: {data_type}:{data_id}")
        
        try:
            session = get_session()
            
            if data_type == "product":
                product = session.query(Product).get(int(data_id))
                if product:
                    self.show_product_info(product)
                else:
                    self.status_label.setText(f"Product with ID {data_id} not found")
            
            elif data_type == "order":
                order = session.query(PurchaseOrder).get(int(data_id))
                if order:
                    self.show_order_info(order)
                else:
                    self.status_label.setText(f"Order with ID {data_id} not found")
            
            else:
                self.status_label.setText(f"Unknown QR code type: {data_type}")
            
        except Exception as e:
            self.status_label.setText(f"Error processing scan: {str(e)}")
            logger.error(f"Error processing scan result: {str(e)}")
        finally:
            session.close()
    
    def show_product_info(self, product):
        """Show information about the scanned product."""
        supplier_name = product.supplier.name if product.supplier else "N/A"
        
        info_text = f"""
        <h3>Product Information</h3>
        <p><b>Name:</b> {product.name}</p>
        <p><b>SKU:</b> {product.sku}</p>
        <p><b>Category:</b> {product.category or 'Uncategorized'}</p>
        <p><b>Supplier:</b> {supplier_name}</p>
        <p><b>Price:</b> ${product.unit_price:.2f}</p>
        <p><b>Stock:</b> {product.quantity_in_stock} units</p>
        <p><b>Reorder Level:</b> {product.reorder_level} units</p>
        """
        
        stock_status = ""
        if product.quantity_in_stock == 0:
            stock_status = "<p style='color: red; font-weight: bold;'>OUT OF STOCK</p>"
        elif product.quantity_in_stock < product.reorder_level:
            stock_status = "<p style='color: orange; font-weight: bold;'>LOW STOCK</p>"
        
        # Show in dialog
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Product Information")
        msg_box.setTextFormat(Qt.RichText)
        msg_box.setText(info_text + stock_status)
        msg_box.setDetailedText(product.description or "No detailed description available.")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()
    
    def show_order_info(self, order):
        """Show information about the scanned order."""
        supplier_name = order.supplier.name if order.supplier else "N/A"
        order_date = order.order_date.strftime('%Y-%m-%d') if order.order_date else "N/A"
        expected_date = order.expected_delivery.strftime('%Y-%m-%d') if order.expected_delivery else "N/A"
        
        info_text = f"""
        <h3>Purchase Order Information</h3>
        <p><b>Order Number:</b> {order.order_number}</p>
        <p><b>Supplier:</b> {supplier_name}</p>
        <p><b>Order Date:</b> {order_date}</p>
        <p><b>Expected Delivery:</b> {expected_date}</p>
        <p><b>Status:</b> {order.status}</p>
        <p><b>Total Amount:</b> ${order.total_amount:.2f}</p>
        """
        
        # Get items info
        items_text = "<h4>Order Items:</h4><ul>"
        for item in order.items:
            product_name = item.product.name if item.product else f"Product #{item.product_id}"
            items_text += f"<li>{product_name} - {item.quantity} units at ${item.unit_price:.2f}</li>"
        items_text += "</ul>"
        
        # Show in dialog
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Order Information")
        msg_box.setTextFormat(Qt.RichText)
        msg_box.setText(info_text + items_text)
        msg_box.setDetailedText(order.notes or "No additional notes.")
        msg_box.setStandardButtons(QMessageBox.Ok)
        msg_box.exec_()
    
    def close_scanner(self):
        """Close the scanner and release resources."""
        self.stop_camera()
        self.accept()
    
    def closeEvent(self, event):
        """Handle the dialog close event."""
        self.stop_camera()
        event.accept()
