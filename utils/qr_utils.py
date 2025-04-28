"""
QR code generation and scanning utilities.
"""

import os
import logging
import qrcode
from PIL import Image, ImageDraw, ImageFont
import cv2
from pyzbar.pyzbar import decode
import numpy as np

logger = logging.getLogger(__name__)


def create_qr_directory():
    """Create directory for storing QR code images if it doesn't exist."""
    qr_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'qr_codes')
    os.makedirs(qr_dir, exist_ok=True)
    return qr_dir


def generate_product_qr_code(product):
    """Generate a QR code for a product.
    
    Args:
        product: The Product model instance
        
    Returns:
        str: Path to the saved QR code image
    """
    try:
        # Create data string in format "product:id"
        qr_data = f"product:{product.id}"
        
        # Create QR code instance
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        
        # Add data and generate QR code
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Create an image with the QR code
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Add product information below the QR code
        # Create a larger image to accommodate text
        qr_size = qr_img.size[0]
        img_width = qr_size
        img_height = qr_size + 120  # Extra space for text
        
        # Create new image with white background
        final_img = Image.new('RGB', (img_width, img_height), color='white')
        
        # Paste QR code at the top
        final_img.paste(qr_img, (0, 0))
        
        # Add text below QR code
        draw = ImageDraw.Draw(final_img)
        
        # Try to get a font, fallback to default if not available
        try:
            font = ImageFont.truetype("arial.ttf", 14)
        except IOError:
            font = ImageFont.load_default()
        
        # Draw product information
        draw.text((10, qr_size + 10), f"ID: {product.id}", fill="black", font=font)
        draw.text((10, qr_size + 30), f"SKU: {product.sku}", fill="black", font=font)
        draw.text((10, qr_size + 50), f"Name: {product.name}", fill="black", font=font)
        draw.text((10, qr_size + 70), f"Price: ${product.unit_price:.2f}", fill="black", font=font)
        draw.text((10, qr_size + 90), f"Stock: {product.quantity_in_stock}", fill="black", font=font)
        
        # Ensure QR code directory exists
        qr_dir = create_qr_directory()
        
        # Save the image
        qr_filename = f"product_{product.id}_{product.sku}.png"
        qr_path = os.path.join(qr_dir, qr_filename)
        final_img.save(qr_path)
        
        logger.info(f"Generated QR code for product {product.id} at {qr_path}")
        return qr_path
        
    except Exception as e:
        logger.error(f"Error generating QR code for product {product.id}: {str(e)}")
        raise


def generate_purchase_order_qr_code(order):
    """Generate a QR code for a purchase order.
    
    Args:
        order: The PurchaseOrder model instance
        
    Returns:
        str: Path to the saved QR code image
    """
    try:
        # Create data string in format "order:id"
        qr_data = f"order:{order.id}"
        
        # Create QR code instance
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4,
        )
        
        # Add data and generate QR code
        qr.add_data(qr_data)
        qr.make(fit=True)
        
        # Create an image with the QR code
        qr_img = qr.make_image(fill_color="black", back_color="white")
        
        # Add order information below the QR code
        # Create a larger image to accommodate text
        qr_size = qr_img.size[0]
        img_width = qr_size
        img_height = qr_size + 120  # Extra space for text
        
        # Create new image with white background
        final_img = Image.new('RGB', (img_width, img_height), color='white')
        
        # Paste QR code at the top
        final_img.paste(qr_img, (0, 0))
        
        # Add text below QR code
        draw = ImageDraw.Draw(final_img)
        
        # Try to get a font, fallback to default if not available
        try:
            font = ImageFont.truetype("arial.ttf", 14)
        except IOError:
            font = ImageFont.load_default()
        
        # Get supplier name
        supplier_name = order.supplier.name if order.supplier else "N/A"
        
        # Draw order information
        draw.text((10, qr_size + 10), f"Order: {order.order_number}", fill="black", font=font)
        draw.text((10, qr_size + 30), f"Supplier: {supplier_name}", fill="black", font=font)
        draw.text((10, qr_size + 50), f"Date: {order.order_date.strftime('%Y-%m-%d') if order.order_date else 'N/A'}", 
                fill="black", font=font)
        draw.text((10, qr_size + 70), f"Status: {order.status}", fill="black", font=font)
        draw.text((10, qr_size + 90), f"Amount: ${order.total_amount:.2f}", fill="black", font=font)
        
        # Ensure QR code directory exists
        qr_dir = create_qr_directory()
        
        # Save the image
        qr_filename = f"order_{order.id}_{order.order_number}.png"
        qr_path = os.path.join(qr_dir, qr_filename)
        final_img.save(qr_path)
        
        logger.info(f"Generated QR code for order {order.id} at {qr_path}")
        return qr_path
        
    except Exception as e:
        logger.error(f"Error generating QR code for order {order.id}: {str(e)}")
        raise


def scan_qr_code_from_image(image_path):
    """Scan a QR code from an image file.
    
    Args:
        image_path: Path to the image file
        
    Returns:
        str: Decoded QR code data or None if not found
    """
    try:
        # Load the image
        image = cv2.imread(image_path)
        if image is None:
            logger.error(f"Failed to load image from {image_path}")
            return None
        
        # Convert to grayscale
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        # Decode QR codes
        qr_codes = decode(gray)
        
        if not qr_codes:
            logger.info("No QR codes found in the image")
            return None
        
        # Return the first QR code data
        qr_data = qr_codes[0].data.decode('utf-8')
        logger.info(f"Scanned QR code: {qr_data}")
        return qr_data
    
    except Exception as e:
        logger.error(f"Error scanning QR code: {str(e)}")
        return None


def scan_qr_code_from_webcam(camera_index=0, timeout=30):
    """Scan a QR code using the webcam.
    
    Args:
        camera_index: Index of the camera to use (default 0)
        timeout: Timeout in seconds (default 30)
        
    Returns:
        str: Decoded QR code data or None if not found
    """
    try:
        # Initialize webcam
        cap = cv2.VideoCapture(camera_index)
        if not cap.isOpened():
            logger.error(f"Failed to open camera {camera_index}")
            return None
        
        logger.info(f"Scanning for QR code using camera {camera_index}...")
        
        # Set a timeout
        import time
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            # Read frame
            ret, frame = cap.read()
            if not ret:
                logger.error("Failed to read from camera")
                break
            
            # Convert to grayscale
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            
            # Decode QR codes
            qr_codes = decode(gray)
            
            if qr_codes:
                # Found a QR code
                qr_data = qr_codes[0].data.decode('utf-8')
                logger.info(f"Scanned QR code: {qr_data}")
                
                # Draw outline and data on frame
                points = qr_codes[0].polygon
                if len(points) > 4:
                    hull = cv2.convexHull(np.array([point for point in points], dtype=np.float32))
                    cv2.polylines(frame, [hull], True, (0, 255, 0), 2)
                else:
                    cv2.polylines(frame, [np.array(points)], True, (0, 255, 0), 2)
                
                # Release camera and return data
                cap.release()
                return qr_data
            
            # Display frame
            cv2.imshow("QR Code Scanner", frame)
            
            # Exit on 'q' key
            if cv2.waitKey(1) & 0xFF == ord('q'):
                break
        
        # Timeout or user quit
        logger.info("QR code scanning timeout or user quit")
        cap.release()
        cv2.destroyAllWindows()
        return None
    
    except Exception as e:
        logger.error(f"Error scanning QR code with webcam: {str(e)}")
        return None
