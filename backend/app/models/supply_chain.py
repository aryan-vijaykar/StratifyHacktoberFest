from datetime import datetime
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import relationship

from app.database import Base


class PurchaseOrder(Base):
    """Purchase orders placed with suppliers for products or raw materials."""

    __tablename__ = "purchase_orders"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(
        Integer,
        ForeignKey("suppliers.id", ondelete="CASCADE"),
        nullable=False,
    )
    material_id = Column(
        Integer,
        ForeignKey("raw_materials.id", ondelete="SET NULL"),
        nullable=True,
    )
    product_id = Column(
        Integer,
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
    )
    quantity = Column(Integer, nullable=False, default=1)
    unit_cost = Column(Float, nullable=False, default=0.0)
    order_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    expected_delivery_date = Column(DateTime, nullable=False)
    actual_delivery_date = Column(DateTime, nullable=True)
    status = Column(
        String(50),
        default="PENDING",
    )  # PENDING | SHIPPED | DELIVERED | CANCELLED

    # Relationships
    supplier = relationship("Supplier", backref="purchase_orders")
    material = relationship("RawMaterial")
    product = relationship("Product")


class TransportationLog(Base):
    """Shipment log tracks carrier, transit, and shipping overheads."""

    __tablename__ = "transportation_logs"

    id = Column(Integer, primary_key=True, index=True)
    purchase_order_id = Column(
        Integer,
        ForeignKey("purchase_orders.id", ondelete="CASCADE"),
        nullable=False,
    )
    carrier = Column(String(255), nullable=False)
    shipping_cost = Column(Float, nullable=False, default=0.0)
    transit_days = Column(Integer, nullable=False, default=1)
    revenue_at_sale = Column(Float, nullable=False, default=0.0)

    # Relationships
    purchase_order = relationship("PurchaseOrder", backref="transportation_log")
