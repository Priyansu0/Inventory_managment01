"""
Web routes for the Inventory Management System's Flask web interface
"""

import logging
from datetime import datetime
from flask import render_template, request, redirect, url_for, flash, jsonify
from sqlalchemy.exc import SQLAlchemyError

from app import app, db
from models import Product, Supplier, PurchaseOrder, PurchaseItem

logger = logging.getLogger(__name__)

@app.route('/')
def home():
    """Render the dashboard/home page with system overview."""
    product_count = db.session.query(Product).count()
    supplier_count = db.session.query(Supplier).count()
    order_count = db.session.query(PurchaseOrder).count()
    
    # Get low stock products
    low_stock_products = db.session.query(Product).filter(
        Product.quantity_in_stock <= Product.reorder_level
    ).limit(5).all()
    
    # Get recent purchase orders
    recent_orders = db.session.query(PurchaseOrder).order_by(
        PurchaseOrder.created_at.desc()
    ).limit(5).all()
    
    # Calculate total inventory value
    inventory_value = db.session.query(
        db.func.sum(Product.unit_price * Product.quantity_in_stock)
    ).scalar() or 0
    
    return render_template(
        'index.html',
        product_count=product_count,
        supplier_count=supplier_count,
        order_count=order_count,
        low_stock_products=low_stock_products,
        recent_orders=recent_orders,
        inventory_value=inventory_value,
        year=datetime.now().year
    )

@app.route('/products')
def products():
    """Display the inventory/products page."""
    products = db.session.query(Product).all()
    return render_template('products.html', products=products, year=datetime.now().year)

@app.route('/product/<int:product_id>')
def product_detail(product_id):
    """Display details for a specific product."""
    product = db.session.query(Product).get_or_404(product_id)
    return render_template('product_detail.html', product=product, year=datetime.now().year)

@app.route('/product/new', methods=['GET', 'POST'])
def new_product():
    """Create a new product."""
    suppliers = db.session.query(Supplier).all()
    
    if request.method == 'POST':
        try:
            product = Product(
                name=request.form['name'],
                sku=request.form['sku'],
                description=request.form.get('description', ''),
                category=request.form.get('category', ''),
                unit_price=float(request.form['unit_price']),
                quantity_in_stock=int(request.form['quantity_in_stock']),
                reorder_level=int(request.form['reorder_level']),
                reorder_quantity=int(request.form['reorder_quantity']),
                supplier_id=int(request.form['supplier_id']) if request.form.get('supplier_id') else None
            )
            db.session.add(product)
            db.session.commit()
            flash('Product created successfully!', 'success')
            return redirect(url_for('products'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Error creating product: {str(e)}', 'danger')
    
    return render_template(
        'product_form.html', 
        suppliers=suppliers, 
        product=None, 
        year=datetime.now().year
    )

@app.route('/product/edit/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    """Edit an existing product."""
    product = db.session.query(Product).get_or_404(product_id)
    suppliers = db.session.query(Supplier).all()
    
    if request.method == 'POST':
        try:
            product.name = request.form['name']
            product.sku = request.form['sku']
            product.description = request.form.get('description', '')
            product.category = request.form.get('category', '')
            product.unit_price = float(request.form['unit_price'])
            product.quantity_in_stock = int(request.form['quantity_in_stock'])
            product.reorder_level = int(request.form['reorder_level'])
            product.reorder_quantity = int(request.form['reorder_quantity'])
            product.supplier_id = int(request.form['supplier_id']) if request.form.get('supplier_id') else None
            
            db.session.commit()
            flash('Product updated successfully!', 'success')
            return redirect(url_for('products'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Error updating product: {str(e)}', 'danger')
    
    return render_template(
        'product_form.html',
        product=product,
        suppliers=suppliers,
        year=datetime.now().year
    )

@app.route('/suppliers')
def suppliers():
    """Display all suppliers."""
    suppliers = db.session.query(Supplier).all()
    return render_template('suppliers.html', suppliers=suppliers, year=datetime.now().year)

@app.route('/supplier/<int:supplier_id>')
def supplier_detail(supplier_id):
    """Display details for a specific supplier."""
    supplier = db.session.query(Supplier).get_or_404(supplier_id)
    return render_template('supplier_detail.html', supplier=supplier, year=datetime.now().year)

@app.route('/supplier/new', methods=['GET', 'POST'])
def new_supplier():
    """Create a new supplier."""
    if request.method == 'POST':
        try:
            supplier = Supplier(
                name=request.form['name'],
                contact_name=request.form.get('contact_name', ''),
                email=request.form.get('email', ''),
                phone=request.form.get('phone', ''),
                address=request.form.get('address', ''),
                notes=request.form.get('notes', ''),
                active=True
            )
            db.session.add(supplier)
            db.session.commit()
            flash('Supplier created successfully!', 'success')
            return redirect(url_for('suppliers'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Error creating supplier: {str(e)}', 'danger')
    
    return render_template('supplier_form.html', supplier=None, year=datetime.now().year)

@app.route('/supplier/edit/<int:supplier_id>', methods=['GET', 'POST'])
def edit_supplier(supplier_id):
    """Edit an existing supplier."""
    supplier = db.session.query(Supplier).get_or_404(supplier_id)
    
    if request.method == 'POST':
        try:
            supplier.name = request.form['name']
            supplier.contact_name = request.form.get('contact_name', '')
            supplier.email = request.form.get('email', '')
            supplier.phone = request.form.get('phone', '')
            supplier.address = request.form.get('address', '')
            supplier.notes = request.form.get('notes', '')
            supplier.active = 'active' in request.form
            
            db.session.commit()
            flash('Supplier updated successfully!', 'success')
            return redirect(url_for('suppliers'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Error updating supplier: {str(e)}', 'danger')
    
    return render_template('supplier_form.html', supplier=supplier, year=datetime.now().year)

@app.route('/purchase_orders')
def purchase_orders():
    """Display all purchase orders."""
    orders = db.session.query(PurchaseOrder).all()
    return render_template('purchase_orders.html', orders=orders, year=datetime.now().year)

@app.route('/purchase_order/<int:order_id>')
def order_detail(order_id):
    """Display details for a specific purchase order."""
    order = db.session.query(PurchaseOrder).get_or_404(order_id)
    return render_template('order_detail.html', order=order, year=datetime.now().year)

@app.route('/purchase_order/new', methods=['GET', 'POST'])
def new_purchase_order():
    """Create a new purchase order."""
    suppliers = db.session.query(Supplier).filter(Supplier.active == True).all()
    products = db.session.query(Product).all()
    
    if request.method == 'POST':
        try:
            # Generate order number
            current_time = datetime.now()
            order_number = f"PO-{current_time.strftime('%Y%m%d')}-{current_time.strftime('%H%M%S')}"
            
            # Create order
            order = PurchaseOrder(
                order_number=order_number,
                supplier_id=int(request.form['supplier_id']),
                order_date=datetime.now(),
                expected_delivery=datetime.strptime(request.form['expected_delivery'], '%Y-%m-%d') if request.form.get('expected_delivery') else None,
                status='pending',
                notes=request.form.get('notes', '')
            )
            
            db.session.add(order)
            db.session.flush()  # Get the order ID
            
            # Handle items (from JSON data)
            items_data = request.json.get('items', [])
            total_amount = 0
            
            for item_data in items_data:
                item = PurchaseItem(
                    purchase_order_id=order.id,
                    product_id=item_data['product_id'],
                    quantity=item_data['quantity'],
                    unit_price=item_data['unit_price']
                )
                total_amount += item.quantity * item.unit_price
                db.session.add(item)
            
            order.total_amount = total_amount
            db.session.commit()
            
            flash('Purchase order created successfully!', 'success')
            return redirect(url_for('purchase_orders'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Error creating purchase order: {str(e)}', 'danger')
    
    return render_template(
        'order_form.html',
        order=None,
        suppliers=suppliers,
        products=products,
        year=datetime.now().year
    )

@app.route('/receive_order/<int:order_id>', methods=['GET', 'POST'])
def receive_order(order_id):
    """Process receiving items for a purchase order."""
    order = db.session.query(PurchaseOrder).get_or_404(order_id)
    
    if order.status == 'delivered':
        flash('This order has already been received.', 'warning')
        return redirect(url_for('order_detail', order_id=order.id))
    
    if request.method == 'POST':
        try:
            # Update order status
            order.status = 'delivered'
            
            # Process each item
            for item in order.items:
                received_qty = int(request.form.get(f'item_{item.id}', 0))
                item.received_quantity = received_qty
                
                # Update inventory
                product = item.product
                product.quantity_in_stock += received_qty
            
            db.session.commit()
            flash('Order received successfully!', 'success')
            return redirect(url_for('purchase_orders'))
        except SQLAlchemyError as e:
            db.session.rollback()
            flash(f'Error receiving order: {str(e)}', 'danger')
    
    return render_template('receive_order.html', order=order, year=datetime.now().year)

@app.route('/api/products')
def api_products():
    """API endpoint for products data."""
    products = db.session.query(Product).all()
    result = [{
        'id': p.id,
        'name': p.name,
        'sku': p.sku,
        'category': p.category,
        'unit_price': p.unit_price,
        'quantity_in_stock': p.quantity_in_stock,
        'reorder_level': p.reorder_level
    } for p in products]
    return jsonify(result)

@app.route('/api/low_stock')
def api_low_stock():
    """API endpoint for low stock products data."""
    products = db.session.query(Product).filter(
        Product.quantity_in_stock <= Product.reorder_level
    ).all()
    result = [{
        'id': p.id,
        'name': p.name,
        'sku': p.sku,
        'category': p.category,
        'quantity_in_stock': p.quantity_in_stock,
        'reorder_level': p.reorder_level
    } for p in products]
    return jsonify(result)

@app.route('/api/orders')
def api_orders():
    """API endpoint for purchase orders data."""
    orders = db.session.query(PurchaseOrder).all()
    result = [{
        'id': o.id,
        'order_number': o.order_number,
        'supplier': o.supplier.name if o.supplier else None,
        'order_date': o.order_date.strftime('%Y-%m-%d') if o.order_date else None,
        'status': o.status,
        'total_amount': o.total_amount
    } for o in orders]
    return jsonify(result)

# Error handlers
@app.errorhandler(404)
def page_not_found(e):
    """Handle 404 errors."""
    return render_template('errors/404.html', year=datetime.now().year), 404

@app.errorhandler(500)
def server_error(e):
    """Handle 500 errors."""
    return render_template('errors/500.html', year=datetime.now().year), 500