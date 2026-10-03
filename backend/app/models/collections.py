from datetime import datetime
from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
)
from sqlalchemy.orm import relationship

from app.database import Base


class PaymentHistory(Base):
    """AR Payment history per invoice tracks payment timeliness and delinquency."""

    __tablename__ = "payment_histories"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(
        Integer,
        ForeignKey("invoices.id", ondelete="CASCADE"),
        nullable=False,
    )
    due_date = Column(DateTime, nullable=False)
    paid_date = Column(DateTime, nullable=True)
    days_late = Column(Integer, default=0, nullable=False)
    amount = Column(Float, nullable=False)

    # Relationships
    invoice = relationship("Invoice", backref="payment_histories")
