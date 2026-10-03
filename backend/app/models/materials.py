from datetime import datetime
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Table,
)
from sqlalchemy.orm import relationship

from app.database import Base

# Join table for RawMaterial <-> Product (Many-to-Many)
product_material_association = Table(
    "product_material_association",
    Base.metadata,
    Column(
        "product_id",
        Integer,
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    ),
    Column(
        "material_id",
        Integer,
        ForeignKey("raw_materials.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)


class RawMaterial(Base):
    """Raw materials inventory tracking."""

    __tablename__ = "raw_materials"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False)
    unit = Column(String(50), nullable=False)  # e.g., kg, unit, liter
    current_unit_price = Column(Float, nullable=False, default=0.0)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)
    reorder_threshold = Column(Float, nullable=False, default=0.0)

    # Relationships
    supplier = relationship("Supplier", backref="raw_materials")
    products = relationship(
        "Product",
        secondary=product_material_association,
        backref="raw_materials",
    )
    price_history = relationship(
        "MaterialPriceHistory",
        back_populates="material",
        cascade="all, delete-orphan",
    )


class MaterialPriceHistory(Base):
    """Historical spot pricing registry per raw material."""

    __tablename__ = "material_price_history"

    id = Column(Integer, primary_key=True, index=True)
    material_id = Column(
        Integer,
        ForeignKey("raw_materials.id", ondelete="CASCADE"),
        nullable=False,
    )
    recorded_price = Column(Float, nullable=False)
    recorded_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    source = Column(String(50), default="MANUAL")  # MANUAL | DOC_INGESTED

    # Relationships
    material = relationship("RawMaterial", back_populates="price_history")
