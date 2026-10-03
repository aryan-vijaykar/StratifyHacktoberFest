"""
Business Models — Core operational entities for the SME Operating System.

Tables:
  Company       — Single company profile (one-row master record)
  Customer      — Buyers / clients
  Supplier      — Vendors / procurement partners
  Product       — SKU catalogue with pricing and stock
  Invoice       — AR (customer invoices) and AP (supplier bills)
  Sales         — Individual sales transactions
  Inventory     — Real-time stock tracking per product
  Employee      — Headcount and payroll data
"""

from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
)
from sqlalchemy.orm import relationship

from app.database import Base


class Company(Base):
    """Single master record representing the operating business."""

    __tablename__ = "companies"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    industry = Column(String(100), nullable=True)
    tax_id = Column(String(50), nullable=True)
    registration_number = Column(String(50), nullable=True)
    address = Column(String(500), nullable=True)
    phone = Column(String(30), nullable=True)
    email = Column(String(255), nullable=True)
    cash_balance = Column(Float, default=0.0)
    annual_revenue_target = Column(Float, default=0.0)
    founded_year = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class Customer(Base):
    """Buyers and clients with credit and lifetime value tracking."""

    __tablename__ = "customers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=False)
    phone = Column(String(30), nullable=True)
    address = Column(String(500), nullable=True)
    company_name = Column(String(255), nullable=True)
    credit_score = Column(Integer, default=700)          # 300–850
    credit_limit = Column(Float, default=10000.0)
    clv = Column(Float, default=0.0)                     # Customer Lifetime Value (accumulated)
    payment_terms_days = Column(Integer, default=30)
    is_active = Column(Integer, default=1)               # 1=active, 0=churned
    region = Column(String(100), nullable=True, default="East")  # East | West | North | South
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sales = relationship("Sales", back_populates="customer")
    invoices = relationship("Invoice", back_populates="customer")


class Supplier(Base):
    """Vendors and procurement partners with reliability tracking."""

    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    contact = Column(String(100), nullable=True)
    phone = Column(String(30), nullable=True)
    address = Column(String(500), nullable=True)
    payment_terms_days = Column(Integer, default=30)
    reliability_score = Column(Float, default=1.0)       # 0.0 (worst) → 1.0 (perfect)
    average_lead_days = Column(Integer, default=7)
    total_orders_placed = Column(Integer, default=0)
    total_delayed_orders = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    invoices = relationship("Invoice", back_populates="supplier")


class Product(Base):
    """SKU catalogue entry with cost, price, stock and reorder logic."""

    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    sku = Column(String(50), unique=True, index=True, nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(String(1000), nullable=True)
    category = Column(String(100), nullable=True)
    unit_of_measure = Column(String(20), default="unit")
    price = Column(Float, nullable=False)                # Selling price
    cost = Column(Float, nullable=False)                 # Purchase / production cost
    stock_level = Column(Integer, default=0)
    reorder_point = Column(Integer, default=10)
    reorder_quantity = Column(Integer, default=50)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    sales = relationship("Sales", back_populates="product")
    inventory = relationship("Inventory", back_populates="product", uselist=False)


class Invoice(Base):
    """
    Covers both:
      - Accounts Receivable (AR): customer_id set, supplier_id null  → money owed TO company
      - Accounts Payable   (AP): supplier_id set, customer_id null   → money owed BY company
    """

    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    invoice_number = Column(String(100), unique=True, index=True, nullable=False)
    invoice_type = Column(String(10), default="AR")      # "AR" | "AP"
    issue_date = Column(DateTime, default=datetime.utcnow)
    due_date = Column(DateTime, nullable=False)
    total_amount = Column(Float, nullable=False)
    tax_amount = Column(Float, default=0.0)
    discount_amount = Column(Float, default=0.0)
    paid_amount = Column(Float, default=0.0)
    status = Column(String(20), default="UNPAID")        # UNPAID | PARTIAL | PAID | OVERDUE
    notes = Column(String(1000), nullable=True)

    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    purchase_order_id = Column(Integer, ForeignKey("purchase_orders.id", ondelete="SET NULL"), nullable=True)

    # Relationships
    customer = relationship("Customer", back_populates="invoices")
    supplier = relationship("Supplier", back_populates="invoices")
    purchase_order = relationship("PurchaseOrder", backref="invoices")


class Sales(Base):
    """Individual sales transaction linking a product, customer and revenue."""

    __tablename__ = "sales"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False)
    customer_id = Column(Integer, ForeignKey("customers.id"), nullable=False)
    quantity = Column(Integer, nullable=False)
    unit_price = Column(Float, nullable=False)
    discount_pct = Column(Float, default=0.0)
    total_price = Column(Float, nullable=False)
    channel = Column(String(50), default="direct")       # direct | online | partner
    date = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    product = relationship("Product", back_populates="sales")
    customer = relationship("Customer", back_populates="sales")


class Inventory(Base):
    """Current stock level per product with audit timestamps."""

    __tablename__ = "inventory"

    id = Column(Integer, primary_key=True, index=True)
    product_id = Column(Integer, ForeignKey("products.id"), nullable=False, unique=True)
    current_stock = Column(Integer, default=0)
    reserved_stock = Column(Integer, default=0)          # Stock reserved for pending orders
    warehouse_location = Column(String(100), nullable=True)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    product = relationship("Product", back_populates="inventory")


class Employee(Base):
    """Headcount record with payroll and department info."""

    __tablename__ = "employees"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    role = Column(String(100), nullable=False)
    department = Column(String(100), nullable=False)
    salary = Column(Float, nullable=False)
    employment_type = Column(String(20), default="full_time")  # full_time | part_time | contractor
    hire_date = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Integer, default=1)
    created_at = Column(DateTime, default=datetime.utcnow)
