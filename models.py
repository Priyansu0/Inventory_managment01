"""
Database models for the Inventory Management System.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Boolean, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base
import datetime


class Product(Base):
    """Product model representing inventory items."""
    __tablename__ = 'products'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    sku = Column(String(50), unique=True, nullable=False)
    description = Column(Text)
    category = Column(String(50))
    unit_price = Column(Float, nullable=False)
    quantity_in_stock = Column(Integer, default=0)
    reorder_level = Column(Integer, default=5)
    reorder_quantity = Column(Integer, default=10)
    supplier_id = Column(Integer, ForeignKey('suppliers.id'))
    qr_code = Column(String(255))  # Path to stored QR code
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    supplier = relationship("Supplier", back_populates="products")
    purchase_items = relationship("PurchaseItem", back_populates="product")
    
    @property
    def stock_value(self):
        """Calculate the current value of stock for this product."""
        return self.quantity_in_stock * self.unit_price
    
    @property
    def needs_reorder(self):
        """Check if the product needs to be reordered."""
        return self.quantity_in_stock <= self.reorder_level


class Supplier(Base):
    """Supplier model representing vendors."""
    __tablename__ = 'suppliers'
    
    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    contact_name = Column(String(100))
    email = Column(String(100))
    phone = Column(String(20))
    address = Column(Text)
    notes = Column(Text)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    products = relationship("Product", back_populates="supplier")
    purchase_orders = relationship("PurchaseOrder", back_populates="supplier")


class PurchaseOrder(Base):
    """Purchase order model representing orders to suppliers."""
    __tablename__ = 'purchase_orders'
    
    id = Column(Integer, primary_key=True)
    order_number = Column(String(50), unique=True, nullable=False)
    supplier_id = Column(Integer, ForeignKey('suppliers.id'), nullable=False)
    order_date = Column(DateTime, default=datetime.datetime.utcnow)
    expected_delivery = Column(DateTime)
    status = Column(String(20), default='pending')  # pending, delivered, cancelled
    total_amount = Column(Float, default=0.0)
    notes = Column(Text)
    qr_code = Column(String(255))  # Path to stored QR code
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    
    # Relationships
    supplier = relationship("Supplier", back_populates="purchase_orders")
    items = relationship("PurchaseItem", back_populates="purchase_order", cascade="all, delete-orphan")


class PurchaseItem(Base):
    """Purchase item model representing individual items in a purchase order."""
    __tablename__ = 'purchase_items'
    
    id = Column(Integer, primary_key=True)
    purchase_order_id = Column(Integer, ForeignKey('purchase_orders.id'), nullable=False)
    product_id = Column(Integer, ForeignKey('products.id'), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    received_quantity = Column(Integer, default=0)
    
    # Relationships
    purchase_order = relationship("PurchaseOrder", back_populates="items")
    product = relationship("Product", back_populates="purchase_items")
    
    @property
    def total_price(self):
        """Calculate the total price for this purchase item."""
        return self.quantity * self.unit_price
