from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.supply_chain import PurchaseOrder, TransportationLog
from app.schemas.supply_chain import (
    PurchaseOrderCreate,
    PurchaseOrderSchema,
    PurchaseOrderUpdate,
    TransportationLogCreate,
    TransportationLogSchema,
    TransportationLogUpdate,
    ShipmentMarginResponse,
)
from app.utils.helpers import safe_divide

router = APIRouter(prefix="/supply-chain", tags=["Supplier & Supply Chain Management"])


# ============================================================
# PURCHASE ORDERS CRUD
# ============================================================

@router.get("/purchase-orders", response_model=List[PurchaseOrderSchema])
async def get_purchase_orders(db: AsyncSession = Depends(get_db)):
    """List all purchase orders."""
    result = await db.execute(select(PurchaseOrder))
    return result.scalars().all()


@router.post("/purchase-orders", response_model=PurchaseOrderSchema, status_code=status.HTTP_201_CREATED)
async def create_purchase_order(obj_in: PurchaseOrderCreate, db: AsyncSession = Depends(get_db)):
    """Create a new purchase order."""
    db_obj = PurchaseOrder(**obj_in.model_dump())
    db.add(db_obj)
    await db.flush()
    await db.refresh(db_obj)
    return db_obj


@router.get("/purchase-orders/{id}", response_model=PurchaseOrderSchema)
async def get_purchase_order(id: int, db: AsyncSession = Depends(get_db)):
    """Get a purchase order by ID."""
    po = await db.get(PurchaseOrder, id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    return po


@router.patch("/purchase-orders/{id}", response_model=PurchaseOrderSchema)
async def update_purchase_order(id: int, obj_in: PurchaseOrderUpdate, db: AsyncSession = Depends(get_db)):
    """Update a purchase order."""
    po = await db.get(PurchaseOrder, id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    
    update_data = obj_in.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(po, field, value)
        
    await db.flush()
    await db.refresh(po)
    return po


@router.delete("/purchase-orders/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_purchase_order(id: int, db: AsyncSession = Depends(get_db)):
    """Delete a purchase order."""
    po = await db.get(PurchaseOrder, id)
    if not po:
        raise HTTPException(status_code=404, detail="Purchase order not found")
    await db.delete(po)
    await db.flush()
    return None


# ============================================================
# TRANSPORTATION LOGS CRUD
# ============================================================

@router.get("/transport-logs", response_model=List[TransportationLogSchema])
async def get_transport_logs(db: AsyncSession = Depends(get_db)):
    """List all transportation logs."""
    result = await db.execute(select(TransportationLog))
    return result.scalars().all()


@router.post("/transport-logs", response_model=TransportationLogSchema, status_code=status.HTTP_201_CREATED)
async def create_transport_log(obj_in: TransportationLogCreate, db: AsyncSession = Depends(get_db)):
    """Create a new transportation log."""
    # Ensure PO exists
    po = await db.get(PurchaseOrder, obj_in.purchase_order_id)
    if not po:
        raise HTTPException(status_code=404, detail="Associated Purchase Order not found")
        
    db_obj = TransportationLog(**obj_in.model_dump())
    db.add(db_obj)
    await db.flush()
    await db.refresh(db_obj)
    return db_obj


@router.get("/transport-logs/{id}", response_model=TransportationLogSchema)
async def get_transport_log(id: int, db: AsyncSession = Depends(get_db)):
    """Get a transportation log by ID."""
    log = await db.get(TransportationLog, id)
    if not log:
        raise HTTPException(status_code=404, detail="Transportation log not found")
    return log


@router.patch("/transport-logs/{id}", response_model=TransportationLogSchema)
async def update_transport_log(id: int, obj_in: TransportationLogUpdate, db: AsyncSession = Depends(get_db)):
    """Update a transportation log."""
    log = await db.get(TransportationLog, id)
    if not log:
        raise HTTPException(status_code=404, detail="Transportation log not found")
        
    update_data = obj_in.model_dump(exclude_none=True)
    for field, value in update_data.items():
        setattr(log, field, value)
        
    await db.flush()
    await db.refresh(log)
    return log


@router.delete("/transport-logs/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_transport_log(id: int, db: AsyncSession = Depends(get_db)):
    """Delete a transportation log."""
    log = await db.get(TransportationLog, id)
    if not log:
        raise HTTPException(status_code=404, detail="Transportation log not found")
    await db.delete(log)
    await db.flush()
    return None


# ============================================================
# SHIPMENT PROFIT MARGINS
# ============================================================

@router.get("/margins", response_model=List[ShipmentMarginResponse])
async def get_shipment_margins(db: AsyncSession = Depends(get_db)):
    """Calculate profit margin per shipment (revenue_at_sale - unit_cost * quantity - shipping_cost)."""
    result = await db.execute(select(TransportationLog))
    logs = result.scalars().all()
    
    margins = []
    for log in logs:
        po = log.purchase_order
        if po:
            product_cost = po.quantity * po.unit_cost
            total_cost = product_cost + log.shipping_cost
            margin_profit = log.revenue_at_sale - total_cost
            margin_pct = safe_divide(margin_profit, log.revenue_at_sale, 0.0) * 100
            
            margins.append(ShipmentMarginResponse(
                purchase_order_id=po.id,
                carrier=log.carrier,
                shipping_cost=log.shipping_cost,
                unit_cost=po.unit_cost,
                quantity=po.quantity,
                revenue_at_sale=log.revenue_at_sale,
                margin_profit=margin_profit,
                margin_pct=margin_pct,
            ))
            
    return margins
