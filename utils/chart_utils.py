"""
Chart generation utilities for the Inventory Management System.
"""

import logging
import os
import tempfile
import datetime
from PyQt5.QtWidgets import QVBoxLayout
from PyQt5.QtCore import Qt
from matplotlib.figure import Figure
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.pyplot as plt
import numpy as np
from sqlalchemy import func, extract, case, desc
from sqlalchemy.exc import SQLAlchemyError

from models import Product, PurchaseOrder, PurchaseItem, Supplier

logger = logging.getLogger(__name__)


def create_inventory_value_chart(session, parent_widget):
    """Create a chart showing inventory value by category.
    
    Args:
        session: SQLAlchemy database session
        parent_widget: Parent widget where chart will be displayed
    """
    try:
        # Clear any existing layouts
        clear_widget_layout(parent_widget)
        
        # Create matplotlib figure and canvas
        figure = Figure(figsize=(5, 4), dpi=100)
        canvas = FigureCanvas(figure)
        
        # Create layout and add canvas
        layout = QVBoxLayout(parent_widget)
        layout.addWidget(canvas)
        
        # Query data: inventory value by category
        query_result = session.query(
            func.coalesce(Product.category, "Uncategorized").label('category'),
            func.sum(Product.quantity_in_stock * Product.unit_price).label('value')
        ).group_by(
            func.coalesce(Product.category, "Uncategorized")
        ).all()
        
        # Check if we have data
        if not query_result:
            # No data, display message
            ax = figure.add_subplot(111)
            ax.text(0.5, 0.5, "No inventory data available", 
                   horizontalalignment='center', verticalalignment='center',
                   transform=ax.transAxes, fontsize=12)
            ax.axis('off')
            canvas.draw()
            return
        
        # Extract data from query results
        categories = [r.category for r in query_result]
        values = [float(r.value) if r.value else 0 for r in query_result]
        
        # Create pie chart
        ax = figure.add_subplot(111)
        wedges, texts, autotexts = ax.pie(
            values, 
            autopct='%1.1f%%',
            textprops={'color': "w", 'fontsize': 8},
            wedgeprops={'width': 0.5}
        )
        
        # Equal aspect ratio ensures that pie is drawn as a circle
        ax.axis('equal')
        
        # Add legend
        ax.legend(
            wedges, 
            [f"{c}: ${v:.2f}" for c, v in zip(categories, values)],
            loc="center left",
            bbox_to_anchor=(1, 0, 0.5, 1),
            fontsize=8
        )
        
        # Set title
        ax.set_title("Inventory Value by Category")
        
        # Adjust layout
        figure.tight_layout()
        
        # Draw the canvas
        canvas.draw()
        
    except Exception as e:
        logger.error(f"Error creating inventory value chart: {str(e)}")
        display_error_on_chart(parent_widget)


def create_orders_trend_chart(session, parent_widget):
    """Create a chart showing purchase order trends over time.
    
    Args:
        session: SQLAlchemy database session
        parent_widget: Parent widget where chart will be displayed
    """
    try:
        # Clear any existing layouts
        clear_widget_layout(parent_widget)
        
        # Create matplotlib figure and canvas
        figure = Figure(figsize=(5, 4), dpi=100)
        canvas = FigureCanvas(figure)
        
        # Create layout and add canvas
        layout = QVBoxLayout(parent_widget)
        layout.addWidget(canvas)
        
        # Calculate date range (last 6 months)
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=180)
        
        # Query data: orders by month
        query_result = session.query(
            extract('year', PurchaseOrder.order_date).label('year'),
            extract('month', PurchaseOrder.order_date).label('month'),
            func.count(PurchaseOrder.id).label('count'),
            func.sum(PurchaseOrder.total_amount).label('value')
        ).filter(
            PurchaseOrder.order_date.between(start_date, end_date)
        ).group_by(
            extract('year', PurchaseOrder.order_date),
            extract('month', PurchaseOrder.order_date)
        ).order_by(
            extract('year', PurchaseOrder.order_date),
            extract('month', PurchaseOrder.order_date)
        ).all()
        
        # Check if we have data
        if not query_result:
            # No data, display message
            ax = figure.add_subplot(111)
            ax.text(0.5, 0.5, "No purchase order data available", 
                   horizontalalignment='center', verticalalignment='center',
                   transform=ax.transAxes, fontsize=12)
            ax.axis('off')
            canvas.draw()
            return
        
        # Extract data from query results
        months = [f"{int(r.month)}/{int(r.year)}" for r in query_result]
        counts = [r.count for r in query_result]
        values = [float(r.value) if r.value else 0 for r in query_result]
        
        # Create bar chart with two y-axes
        ax1 = figure.add_subplot(111)
        
        # Plot order counts as bars
        x = np.arange(len(months))
        bar_width = 0.4
        bars = ax1.bar(x, counts, bar_width, label='Order Count', color='skyblue')
        
        # Set up the first y-axis
        ax1.set_xlabel('Month')
        ax1.set_ylabel('Number of Orders', color='skyblue')
        ax1.tick_params(axis='y', labelcolor='skyblue')
        
        # Add value labels on top of the bars
        for bar in bars:
            height = bar.get_height()
            ax1.annotate(f"{height}",
                        xy=(bar.get_x() + bar.get_width() / 2, height),
                        xytext=(0, 3),  # 3 points vertical offset
                        textcoords="offset points",
                        ha='center', va='bottom')
        
        # Create second y-axis for values
        ax2 = ax1.twinx()
        ax2.plot(x, values, 'ro-', label='Order Value')
        ax2.set_ylabel('Order Value ($)', color='red')
        ax2.tick_params(axis='y', labelcolor='red')
        
        # Set the x-tick labels to month names
        ax1.set_xticks(x)
        ax1.set_xticklabels(months, rotation=45)
        
        # Set title
        ax1.set_title("Purchase Order Trends (Last 6 Months)")
        
        # Adjust layout
        figure.tight_layout()
        
        # Draw the canvas
        canvas.draw()
        
    except Exception as e:
        logger.error(f"Error creating orders trend chart: {str(e)}")
        display_error_on_chart(parent_widget)


def create_report_chart(session, report_type, parent_widget, save_path=None, custom_data=None):
    """Create a chart for reports based on report type.
    
    Args:
        session: SQLAlchemy database session
        report_type: Type of report
        parent_widget: Parent widget where chart will be displayed (can be None if save_path is provided)
        save_path: Path to save the chart as an image (optional)
        custom_data: Custom data for the chart (optional)
    """
    try:
        # Create matplotlib figure and canvas
        fig_width = 8 if save_path else 5
        fig_height = 6 if save_path else 4
        
        figure = Figure(figsize=(fig_width, fig_height), dpi=100)
        
        if parent_widget:
            # Clear any existing layouts
            clear_widget_layout(parent_widget)
            
            # Create canvas and add to layout
            canvas = FigureCanvas(figure)
            layout = QVBoxLayout(parent_widget)
            layout.addWidget(canvas)
        
        # Generate chart based on report type
        if report_type == "Inventory Valuation":
            create_inventory_valuation_chart(session, figure)
        elif report_type == "Low Stock Items":
            create_low_stock_chart(session, figure)
        elif report_type == "Purchase Order History":
            create_purchase_history_chart(session, figure)
        elif report_type == "Supplier Performance":
            create_supplier_performance_chart(session, figure)
        elif report_type == "Category Analysis":
            create_category_analysis_chart(session, figure)
        elif report_type == "Monthly Purchases":
            create_monthly_purchases_chart(session, figure, custom_data)
        else:
            # Unknown report type
            ax = figure.add_subplot(111)
            ax.text(0.5, 0.5, f"No chart available for {report_type}", 
                   horizontalalignment='center', verticalalignment='center',
                   transform=ax.transAxes, fontsize=12)
            ax.axis('off')
        
        # Adjust layout
        figure.tight_layout()
        
        if parent_widget:
            # Draw the canvas
            canvas.draw()
        
        if save_path:
            # Save figure to file
            figure.savefig(save_path)
            plt.close(figure)
        
    except Exception as e:
        logger.error(f"Error creating report chart: {str(e)}")
        if parent_widget:
            display_error_on_chart(parent_widget)
        if save_path:
            # Create a simple error chart
            plt.figure(figsize=(8, 6))
            plt.text(0.5, 0.5, f"Error creating chart: {str(e)}", 
                    horizontalalignment='center', verticalalignment='center',
                    transform=plt.gca().transAxes, fontsize=12)
            plt.axis('off')
            plt.savefig(save_path)
            plt.close()


def create_inventory_valuation_chart(session, figure):
    """Create inventory valuation chart for reports."""
    # Query data: inventory value by category
    query_result = session.query(
        func.coalesce(Product.category, "Uncategorized").label('category'),
        func.sum(Product.quantity_in_stock * Product.unit_price).label('value')
    ).group_by(
        func.coalesce(Product.category, "Uncategorized")
    ).all()
    
    # Check if we have data
    if not query_result:
        ax = figure.add_subplot(111)
        ax.text(0.5, 0.5, "No inventory data available", 
               horizontalalignment='center', verticalalignment='center',
               transform=ax.transAxes, fontsize=12)
        ax.axis('off')
        return
    
    # Extract data from query results
    categories = [r.category for r in query_result]
    values = [float(r.value) if r.value else 0 for r in query_result]
    
    # Create pie chart
    ax = figure.add_subplot(111)
    wedges, texts, autotexts = ax.pie(
        values, 
        autopct='%1.1f%%',
        textprops={'color': "w"},
        wedgeprops={'width': 0.5}
    )
    
    # Equal aspect ratio ensures that pie is drawn as a circle
    ax.axis('equal')
    
    # Add legend
    ax.legend(
        wedges, 
        [f"{c}: ${v:.2f}" for c, v in zip(categories, values)],
        loc="center left",
        bbox_to_anchor=(1, 0, 0.5, 1)
    )
    
    # Set title
    ax.set_title("Inventory Valuation by Category")


def create_low_stock_chart(session, figure):
    """Create low stock items chart for reports."""
    # Query data: low stock items by category
    query_result = session.query(
        func.coalesce(Product.category, "Uncategorized").label('category'),
        func.count(Product.id).label('count')
    ).filter(
        Product.quantity_in_stock <= Product.reorder_level
    ).group_by(
        func.coalesce(Product.category, "Uncategorized")
    ).all()
    
    # Check if we have data
    if not query_result:
        ax = figure.add_subplot(111)
        ax.text(0.5, 0.5, "No low stock items available", 
               horizontalalignment='center', verticalalignment='center',
               transform=ax.transAxes, fontsize=12)
        ax.axis('off')
        return
    
    # Extract data from query results
    categories = [r.category for r in query_result]
    counts = [r.count for r in query_result]
    
    # Create horizontal bar chart
    ax = figure.add_subplot(111)
    y_pos = np.arange(len(categories))
    
    bars = ax.barh(y_pos, counts, align='center')
    ax.set_yticks(y_pos)
    ax.set_yticklabels(categories)
    ax.invert_yaxis()  # Labels read top-to-bottom
    ax.set_xlabel('Number of Items')
    ax.set_title('Low Stock Items by Category')
    
    # Add count labels at the end of each bar
    for i, bar in enumerate(bars):
        width = bar.get_width()
        ax.text(width + 0.1, bar.get_y() + bar.get_height()/2, str(counts[i]),
               ha='left', va='center')


def create_purchase_history_chart(session, figure):
    """Create purchase order history chart for reports."""
    # Calculate date range (last 6 months)
    end_date = datetime.datetime.now()
    start_date = end_date - datetime.timedelta(days=180)
    
    # Query data: orders by month and status
    query_result = session.query(
        extract('year', PurchaseOrder.order_date).label('year'),
        extract('month', PurchaseOrder.order_date).label('month'),
        PurchaseOrder.status,
        func.count(PurchaseOrder.id).label('count')
    ).filter(
        PurchaseOrder.order_date.between(start_date, end_date)
    ).group_by(
        extract('year', PurchaseOrder.order_date),
        extract('month', PurchaseOrder.order_date),
        PurchaseOrder.status
    ).order_by(
        extract('year', PurchaseOrder.order_date),
        extract('month', PurchaseOrder.order_date)
    ).all()
    
    # Check if we have data
    if not query_result:
        ax = figure.add_subplot(111)
        ax.text(0.5, 0.5, "No purchase order data available", 
               horizontalalignment='center', verticalalignment='center',
               transform=ax.transAxes, fontsize=12)
        ax.axis('off')
        return
    
    # Process the data for stacked bar chart
    months_dict = {}
    statuses = set()
    
    for r in query_result:
        month_key = f"{int(r.month)}/{int(r.year)}"
        if month_key not in months_dict:
            months_dict[month_key] = {}
        
        months_dict[month_key][r.status] = r.count
        statuses.add(r.status)
    
    months = sorted(months_dict.keys(), key=lambda x: (int(x.split('/')[1]), int(x.split('/')[0])))
    statuses = sorted(list(statuses))
    
    # Create stacked bar chart
    ax = figure.add_subplot(111)
    
    bottom = np.zeros(len(months))
    for status in statuses:
        values = [months_dict[month].get(status, 0) for month in months]
        ax.bar(months, values, label=status.capitalize(), bottom=bottom)
        bottom += values
    
    ax.set_xlabel('Month')
    ax.set_ylabel('Number of Orders')
    ax.set_title('Purchase Orders by Status')
    ax.legend()
    
    # Rotate x labels for better readability
    plt.setp(ax.get_xticklabels(), rotation=45, ha='right')


def create_supplier_performance_chart(session, figure):
    """Create supplier performance chart for reports."""
    # Get top 10 suppliers by order count
    suppliers = session.query(
        Supplier.name,
        func.count(PurchaseOrder.id).label('order_count'),
        func.sum(PurchaseOrder.total_amount).label('total_value')
    ).join(
        PurchaseOrder, Supplier.id == PurchaseOrder.supplier_id
    ).group_by(
        Supplier.id
    ).order_by(
        desc('order_count')
    ).limit(10).all()
    
    # Check if we have data
    if not suppliers:
        ax = figure.add_subplot(111)
        ax.text(0.5, 0.5, "No supplier performance data available", 
               horizontalalignment='center', verticalalignment='center',
               transform=ax.transAxes, fontsize=12)
        ax.axis('off')
        return
    
    # Extract data
    names = [s.name for s in suppliers]
    order_counts = [s.order_count for s in suppliers]
    total_values = [float(s.total_value) if s.total_value else 0 for s in suppliers]
    
    # Create two subplots
    ax1 = figure.add_subplot(121)
    ax2 = figure.add_subplot(122)
    
    # Bar chart for order count
    y_pos = np.arange(len(names))
    ax1.barh(y_pos, order_counts, align='center')
    ax1.set_yticks(y_pos)
    ax1.set_yticklabels(names)
    ax1.invert_yaxis()  # Labels read top-to-bottom
    ax1.set_xlabel('Number of Orders')
    ax1.set_title('Orders by Supplier')
    
    # Bar chart for total value
    ax2.barh(y_pos, total_values, align='center')
    ax2.set_yticks(y_pos)
    ax2.set_yticklabels(names)
    ax2.invert_yaxis()  # Labels read top-to-bottom
    ax2.set_xlabel('Total Value ($)')
    ax2.set_title('Order Value by Supplier')
    
    # Add a main title
    figure.suptitle('Top Suppliers by Order Volume', fontsize=14)


def create_category_analysis_chart(session, figure):
    """Create category analysis chart for reports."""
    # Query data for categories: total products, total value
    categories = session.query(
        func.coalesce(Product.category, "Uncategorized").label('category'),
        func.count(Product.id).label('product_count'),
        func.sum(Product.quantity_in_stock * Product.unit_price).label('value')
    ).group_by(
        func.coalesce(Product.category, "Uncategorized")
    ).all()
    
    # Check if we have data
    if not categories:
        ax = figure.add_subplot(111)
        ax.text(0.5, 0.5, "No category data available", 
               horizontalalignment='center', verticalalignment='center',
               transform=ax.transAxes, fontsize=12)
        ax.axis('off')
        return
    
    # Extract data
    cat_names = [c.category for c in categories]
    product_counts = [c.product_count for c in categories]
    values = [float(c.value) if c.value else 0 for c in categories]
    
    # Create two subplots
    ax1 = figure.add_subplot(121)
    ax2 = figure.add_subplot(122)
    
    # Create pie chart for product count
    ax1.pie(product_counts, labels=cat_names, autopct='%1.1f%%')
    ax1.axis('equal')  # Equal aspect ratio
    ax1.set_title('Products by Category')
    
    # Create pie chart for inventory value
    ax2.pie(values, labels=cat_names, autopct='%1.1f%%')
    ax2.axis('equal')  # Equal aspect ratio
    ax2.set_title('Inventory Value by Category')
    
    # Add a main title
    figure.suptitle('Category Analysis', fontsize=14)


def create_monthly_purchases_chart(session, figure, custom_data=None):
    """Create monthly purchases chart for reports."""
    if custom_data:
        # Use provided custom data
        months = [item['month'] for item in custom_data]
        values = [item['value'] for item in custom_data]
        order_counts = [item['orders'] for item in custom_data]
    else:
        # Query the last 6 months
        end_date = datetime.datetime.now()
        start_date = end_date - datetime.timedelta(days=180)
        
        # Get monthly data
        query_result = session.query(
            extract('year', PurchaseOrder.order_date).label('year'),
            extract('month', PurchaseOrder.order_date).label('month'),
            func.count(PurchaseOrder.id).label('order_count'),
            func.sum(case([(PurchaseOrder.status != 'cancelled', PurchaseOrder.total_amount)], else_=0)).label('value')
        ).filter(
            PurchaseOrder.order_date.between(start_date, end_date)
        ).group_by(
            extract('year', PurchaseOrder.order_date),
            extract('month', PurchaseOrder.order_date)
        ).order_by(
            extract('year', PurchaseOrder.order_date),
            extract('month', PurchaseOrder.order_date)
        ).all()
        
        # Process the data
        months = [f"{int(r.month)}/{int(r.year)}" for r in query_result]
        order_counts = [r.order_count for r in query_result]
        values = [float(r.value) if r.value else 0 for r in query_result]
    
    # Check if we have data
    if not months:
        ax = figure.add_subplot(111)
        ax.text(0.5, 0.5, "No monthly purchase data available", 
               horizontalalignment='center', verticalalignment='center',
               transform=ax.transAxes, fontsize=12)
        ax.axis('off')
        return
    
    # Create plot with two y-axes
    ax1 = figure.add_subplot(111)
    
    # Plot order counts as bars
    x = np.arange(len(months))
    width = 0.4
    bars = ax1.bar(x, order_counts, width, label='Order Count', color='skyblue')
    
    # Add value labels on top of the bars
    for bar in bars:
        height = bar.get_height()
        ax1.annotate(f"{height}",
                    xy=(bar.get_x() + bar.get_width() / 2, height),
                    xytext=(0, 3),  # 3 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom')
    
    # Set up the first y-axis
    ax1.set_xlabel('Month')
    ax1.set_ylabel('Number of Orders', color='skyblue')
    ax1.tick_params(axis='y', labelcolor='skyblue')
    
    # Create second y-axis for values
    ax2 = ax1.twinx()
    line = ax2.plot(x, values, 'ro-', label='Order Value')
    
    # Add value labels to the line
    for i, val in enumerate(values):
        ax2.annotate(f"${val:.2f}",
                    xy=(x[i], val),
                    xytext=(0, 5),  # 5 points vertical offset
                    textcoords="offset points",
                    ha='center', va='bottom',
                    fontsize=8)
    
    ax2.set_ylabel('Order Value ($)', color='red')
    ax2.tick_params(axis='y', labelcolor='red')
    
    # Set the x-tick labels
    ax1.set_xticks(x)
    ax1.set_xticklabels(months, rotation=45)
    
    # Set title
    ax1.set_title("Monthly Purchase Trends")
    
    # Create legend
    lines, labels = ax1.get_legend_handles_labels()
    lines2, labels2 = ax2.get_legend_handles_labels()
    ax1.legend(lines + lines2, labels + labels2, loc='upper left')


def clear_widget_layout(widget):
    """Clear the layout of a widget if it exists."""
    if widget and widget.layout() is not None:
        while widget.layout().count():
            item = widget.layout().takeAt(0)
            if item.widget():
                item.widget().deleteLater()
            elif item.layout():
                # Recursively clear sub-layouts
                while item.layout().count():
                    sub_item = item.layout().takeAt(0)
                    if sub_item.widget():
                        sub_item.widget().deleteLater()


def display_error_on_chart(parent_widget):
    """Display an error message on the chart widget."""
    try:
        # Clear any existing layouts
        clear_widget_layout(parent_widget)
        
        # Create matplotlib figure and canvas
        figure = Figure(figsize=(5, 4), dpi=100)
        canvas = FigureCanvas(figure)
        
        # Create layout and add canvas
        layout = QVBoxLayout(parent_widget)
        layout.addWidget(canvas)
        
        # Add error message
        ax = figure.add_subplot(111)
        ax.text(0.5, 0.5, "Error creating chart", 
               horizontalalignment='center', verticalalignment='center',
               transform=ax.transAxes, fontsize=12, color='red')
        ax.axis('off')
        
        # Draw the canvas
        canvas.draw()
        
    except Exception as e:
        logger.error(f"Error displaying error message on chart: {str(e)}")
