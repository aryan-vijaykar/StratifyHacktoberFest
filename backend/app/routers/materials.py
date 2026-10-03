from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models.business import Product
from app.models.materials import RawMaterial, MaterialPriceHistory
from app.schemas.materials import (
    RawMaterialCreate,
    RawMaterialSchema,
    RawMaterialUpdate,
    MaterialPriceHistoryCreate,
    MaterialPriceHistorySchema,
    ProductForecastRequest,
    ProductForecastResponse,
    MaterialBuyingAdviceSchema,
)
from app.utils.helpers import safe_divide

router = APIRouter(prefix="/materials", tags=["Raw Materials & Pricing Engine"])


# ============================================================
# RAW MATERIALS CRUD
# ============================================================

@router.get("/", response_model=List[RawMaterialSchema])
async def get_materials(db: AsyncSession = Depends(get_db)):
    """List all raw materials, including their linked product IDs."""
    result = await db.execute(select(RawMaterial).options(selectinload(RawMaterial.products)))
    materials = result.scalars().all()
    
    schemas = []
    for m in materials:
        schema = RawMaterialSchema.model_validate(m)
        schema.product_ids = [p.id for p in m.products]
        schemas.append(schema)
    return schemas


@router.post("/", response_model=RawMaterialSchema, status_code=status.HTTP_201_CREATED)
async def create_material(obj_in: RawMaterialCreate, db: AsyncSession = Depends(get_db)):
    """Create a new raw material and optionally link it to products."""
    product_ids = obj_in.product_ids
    data = obj_in.model_dump(exclude={"product_ids"})
    
    db_obj = RawMaterial(**data)
    if product_ids:
        prod_result = await db.execute(select(Product).where(Product.id.in_(product_ids)))
        products = prod_result.scalars().all()
        db_obj.products = products
        
    db.add(db_obj)
    await db.flush()
    await db.refresh(db_obj, ["products"])
    
    # Store initial price history entry if price is set
    if db_obj.current_unit_price >= 0:
        history_entry = MaterialPriceHistory(
            material_id=db_obj.id,
            recorded_price=db_obj.current_unit_price,
            source="MANUAL"
        )
        db.add(history_entry)
        await db.flush()
        
    schema = RawMaterialSchema.model_validate(db_obj)
    schema.product_ids = [p.id for p in db_obj.products]
    return schema


# ============================================================
# SEASONAL & PRICE TREND BUYING ADVICE
# ============================================================

import calendar
from collections import defaultdict

@router.get("/buying-advice", response_model=List[MaterialBuyingAdviceSchema])
async def get_buying_advice(db: AsyncSession = Depends(get_db)):
    """
    Analyzes historical pricing records to advise:
    - What timing is best to purchase (seasonality).
    - What materials to stockpile, delay, or hold.
    """
    result = await db.execute(select(RawMaterial))
    materials = result.scalars().all()
    
    advice_list = []
    for m in materials:
        hist_result = await db.execute(
            select(MaterialPriceHistory)
            .where(MaterialPriceHistory.material_id == m.id)
            .order_by(MaterialPriceHistory.recorded_at.asc())
        )
        history = hist_result.scalars().all()
        
        if len(history) < 3:
            advice_list.append(MaterialBuyingAdviceSchema(
                material_id=m.id,
                name=m.name,
                current_unit_price=m.current_unit_price,
                historical_average=m.current_unit_price,
                best_month_to_buy="N/A",
                advice="INSIGNIFICANT_DATA",
                justification="Log at least 3 historical price points to enable trend timing analysis."
            ))
            continue
            
        prices = [h.recorded_price for h in history]
        avg_price = sum(prices) / len(prices)
        
        # Calculate monthly average prices to detect seasonality
        monthly_prices = defaultdict(list)
        for h in history:
            monthly_prices[h.recorded_at.month].append(h.recorded_price)
            
        monthly_averages = {}
        for month, price_list in monthly_prices.items():
            monthly_averages[month] = sum(price_list) / len(price_list)
            
        best_month_num = min(monthly_averages, key=monthly_averages.get)
        best_month_name = calendar.month_name[best_month_num]
        
        price_diff_pct = (m.current_unit_price - avg_price) / (avg_price or 1.0)
        
        if price_diff_pct < -0.05:
            advice = "STOCKPILE"
            justification = f"Spot price is {abs(price_diff_pct):.0%} lower than average (${avg_price:.2f}). Storing/stockpiling is highly recommended. Best seasonal buy month is {best_month_name}."
        elif price_diff_pct > 0.05:
            advice = "DELAY"
            justification = f"Spot price is {price_diff_pct:.0%} higher than average (${avg_price:.2f}). Delay purchases where possible. Best seasonal buy month is {best_month_name}."
        else:
            advice = "HOLD"
            justification = f"Spot price is stable with historical average (${avg_price:.2f}). Purchase normal operational volumes. Best seasonal buy month is {best_month_name}."
            
        advice_list.append(MaterialBuyingAdviceSchema(
            material_id=m.id,
            name=m.name,
            current_unit_price=m.current_unit_price,
            historical_average=avg_price,
            best_month_to_buy=best_month_name,
            advice=advice,
            justification=justification
        ))
        
    return advice_list


@router.get("/{id}", response_model=RawMaterialSchema)
async def get_material(id: int, db: AsyncSession = Depends(get_db)):
    """Get a raw material by ID."""
    result = await db.execute(
        select(RawMaterial)
        .where(RawMaterial.id == id)
        .options(selectinload(RawMaterial.products))
    )
    material = result.scalars().first()
    if not material:
        raise HTTPException(status_code=404, detail="Raw material not found")
    
    schema = RawMaterialSchema.model_validate(material)
    schema.product_ids = [p.id for p in material.products]
    return schema


@router.patch("/{id}", response_model=RawMaterialSchema)
async def update_material(id: int, obj_in: RawMaterialUpdate, db: AsyncSession = Depends(get_db)):
    """Update a raw material, recording price history if the price changes."""
    result = await db.execute(
        select(RawMaterial)
        .where(RawMaterial.id == id)
        .options(selectinload(RawMaterial.products))
    )
    material = result.scalars().first()
    if not material:
        raise HTTPException(status_code=404, detail="Raw material not found")
    
    update_data = obj_in.model_dump(exclude_none=True)
    product_ids = update_data.pop("product_ids", None)
    
    price_changed = False
    new_price = None
    if "current_unit_price" in update_data and update_data["current_unit_price"] != material.current_unit_price:
        price_changed = True
        new_price = update_data["current_unit_price"]
        
    for field, value in update_data.items():
        setattr(material, field, value)
        
    if product_ids is not None:
        prod_result = await db.execute(select(Product).where(Product.id.in_(product_ids)))
        products = prod_result.scalars().all()
        material.products = products
        
    await db.flush()
    
    if price_changed and new_price is not None:
        history_entry = MaterialPriceHistory(
            material_id=material.id,
            recorded_price=new_price,
            source="MANUAL"
        )
        db.add(history_entry)
        await db.flush()
        
    await db.refresh(material, ["products"])
    schema = RawMaterialSchema.model_validate(material)
    schema.product_ids = [p.id for p in material.products]
    return schema


@router.delete("/{id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_material(id: int, db: AsyncSession = Depends(get_db)):
    """Delete a raw material."""
    material = await db.get(RawMaterial, id)
    if not material:
        raise HTTPException(status_code=404, detail="Raw material not found")
    await db.delete(material)
    await db.flush()
    return None


# ============================================================
# PRICE HISTORY CRUD
# ============================================================

@router.post("/price-history", response_model=MaterialPriceHistorySchema, status_code=status.HTTP_201_CREATED)
async def create_price_history(obj_in: MaterialPriceHistoryCreate, db: AsyncSession = Depends(get_db)):
    """Add a price history entry and update the material's current spot price."""
    material = await db.get(RawMaterial, obj_in.material_id)
    if not material:
        raise HTTPException(status_code=404, detail="Raw material not found")
    
    db_obj = MaterialPriceHistory(**obj_in.model_dump())
    material.current_unit_price = db_obj.recorded_price
    
    db.add(db_obj)
    await db.flush()
    await db.refresh(db_obj)
    return db_obj


@router.get("/price-history/{material_id}", response_model=List[MaterialPriceHistorySchema])
async def get_price_history(material_id: int, db: AsyncSession = Depends(get_db)):
    """Get the price history of a raw material (newest first)."""
    result = await db.execute(
        select(MaterialPriceHistory)
        .where(MaterialPriceHistory.material_id == material_id)
        .order_by(MaterialPriceHistory.recorded_at.desc())
    )
    return result.scalars().all()


# ============================================================
# COGS & MARGIN FORECAST
# ============================================================

@router.post("/forecast", response_model=ProductForecastResponse)
async def forecast_margin(request: ProductForecastRequest, db: AsyncSession = Depends(get_db)):
    """
    Project product gross margin changes based on linked raw material price changes.
    Projected COGS is calculated as the sum of current linked raw material spot prices.
    """
    product = await db.get(Product, request.product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")
    
    materials = product.raw_materials
    original_cogs = product.cost
    
    if materials:
        projected_cogs = sum(m.current_unit_price for m in materials)
    else:
        projected_cogs = original_cogs
        
    original_margin = safe_divide(product.price - original_cogs, product.price, 0.0)
    projected_margin = safe_divide(product.price - projected_cogs, product.price, 0.0)
    
    return ProductForecastResponse(
        product_id=product.id,
        sku=product.sku,
        name=product.name,
        price=product.price,
        original_cogs=original_cogs,
        projected_cogs=projected_cogs,
        original_margin=original_margin,
        projected_margin=projected_margin,
    )




