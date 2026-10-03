"""
Business Operations Router — Full CRUD for all core business entities.

Endpoints:
  /business/company           POST / GET / PATCH
  /business/customers         POST / GET / PATCH /{id}
  /business/suppliers         POST / GET / PATCH /{id}
  /business/products          POST / GET / PATCH /{id}
  /business/inventory         GET / PATCH /{product_id}
  /business/sales             POST / GET
  /business/invoices          POST / GET / PATCH /{id}
  /business/employees         POST / GET
  /business/events            POST / GET
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.business import (
    Company,
    Customer,
    Employee,
    Inventory,
    Invoice,
    Product,
    Sales,
    Supplier,
)
from app.models.history import BusinessEvent
from app.schemas.business import (
    BusinessEventCreate,
    BusinessEventSchema,
    ChatRequest,
    CompanyCreate,
    CompanySchema,
    CompanyUpdate,
    CustomerCreate,
    CustomerSchema,
    CustomerUpdate,
    EmployeeCreate,
    EmployeeSchema,
    InventorySchema,
    InventoryUpdate,
    InvoiceCreate,
    InvoiceSchema,
    InvoiceUpdate,
    ProductCreate,
    ProductSchema,
    ProductUpdate,
    SalesCreate,
    SalesSchema,
    SupplierCreate,
    SupplierSchema,
    SupplierUpdate,
)
from app.services.event_engine import EventEngineService

router = APIRouter(prefix="/business", tags=["Business CRUD"])
logger = logging.getLogger(__name__)


# ============================================================
# COMPANY
# ============================================================

@router.post("/company", response_model=CompanySchema, status_code=status.HTTP_201_CREATED)
async def create_company(obj_in: CompanyCreate, db: AsyncSession = Depends(get_db)):
    """Create the company master record. Only one company is expected per deployment."""
    existing = (await db.execute(select(Company))).scalars().first()
    if existing:
        raise HTTPException(status_code=409, detail="Company record already exists. Use PATCH to update.")
    db_obj = Company(**obj_in.model_dump())
    db.add(db_obj)
    await db.flush()
    await db.refresh(db_obj)
    return db_obj


@router.get("/company", response_model=CompanySchema)
async def get_company(db: AsyncSession = Depends(get_db)):
    company = (await db.execute(select(Company))).scalars().first()
    if not company:
        raise HTTPException(status_code=404, detail="No company record found. Create one first via POST /business/company")
    return company


@router.patch("/company", response_model=CompanySchema)
async def update_company(obj_in: CompanyUpdate, db: AsyncSession = Depends(get_db)):
    company = (await db.execute(select(Company))).scalars().first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found.")
    for field, value in obj_in.model_dump(exclude_none=True).items():
        setattr(company, field, value)
    await db.flush()
    await db.refresh(company)
    return company


# ============================================================
# CUSTOMERS
# ============================================================

@router.post("/customers", response_model=CustomerSchema, status_code=status.HTTP_201_CREATED)
async def create_customer(obj_in: CustomerCreate, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(select(Customer).where(Customer.email == obj_in.email))).scalars().first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Customer with email '{obj_in.email}' already exists.")
    db_obj = Customer(**obj_in.model_dump())
    db.add(db_obj)
    await db.flush()
    await db.refresh(db_obj)
    return db_obj


@router.get("/customers", response_model=List[CustomerSchema])
async def list_customers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Customer).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/customers/{customer_id}", response_model=CustomerSchema)
async def get_customer(customer_id: int, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(Customer).where(Customer.id == customer_id))).scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="Customer not found.")
    return obj


@router.patch("/customers/{customer_id}", response_model=CustomerSchema)
async def update_customer(customer_id: int, obj_in: CustomerUpdate, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(Customer).where(Customer.id == customer_id))).scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="Customer not found.")
    for field, value in obj_in.model_dump(exclude_none=True).items():
        setattr(obj, field, value)
    await db.flush()
    await db.refresh(obj)
    return obj


# ============================================================
# SUPPLIERS
# ============================================================

@router.post("/suppliers", response_model=SupplierSchema, status_code=status.HTTP_201_CREATED)
async def create_supplier(obj_in: SupplierCreate, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(select(Supplier).where(Supplier.email == obj_in.email))).scalars().first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Supplier with email '{obj_in.email}' already registered.")
    db_obj = Supplier(**obj_in.model_dump())
    db.add(db_obj)
    await db.flush()
    await db.refresh(db_obj)
    return db_obj


@router.get("/suppliers", response_model=List[SupplierSchema])
async def list_suppliers(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Supplier).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/suppliers/{supplier_id}", response_model=SupplierSchema)
async def get_supplier(supplier_id: int, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(Supplier).where(Supplier.id == supplier_id))).scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="Supplier not found.")
    return obj


@router.patch("/suppliers/{supplier_id}", response_model=SupplierSchema)
async def update_supplier(supplier_id: int, obj_in: SupplierUpdate, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(Supplier).where(Supplier.id == supplier_id))).scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="Supplier not found.")
    for field, value in obj_in.model_dump(exclude_none=True).items():
        setattr(obj, field, value)
    await db.flush()
    await db.refresh(obj)
    return obj


# ============================================================
# PRODUCTS
# ============================================================

@router.post("/products", response_model=ProductSchema, status_code=status.HTTP_201_CREATED)
async def create_product(obj_in: ProductCreate, db: AsyncSession = Depends(get_db)):
    existing = (await db.execute(select(Product).where(Product.sku == obj_in.sku))).scalars().first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Product with SKU '{obj_in.sku}' already exists.")

    product_data = obj_in.model_dump()
    db_obj = Product(**product_data)
    db.add(db_obj)
    await db.flush()  # Get generated id

    # Auto-initialise inventory record
    db_inv = Inventory(product_id=db_obj.id, current_stock=obj_in.stock_level)
    db.add(db_inv)

    await db.flush()
    await db.refresh(db_obj)
    return db_obj


@router.get("/products", response_model=List[ProductSchema])
async def list_products(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    category: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Product)
    if category:
        stmt = stmt.where(Product.category == category)
    result = await db.execute(stmt.offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/products/{product_id}", response_model=ProductSchema)
async def get_product(product_id: int, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(Product).where(Product.id == product_id))).scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="Product not found.")
    return obj


@router.patch("/products/{product_id}", response_model=ProductSchema)
async def update_product(product_id: int, obj_in: ProductUpdate, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(Product).where(Product.id == product_id))).scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="Product not found.")
    for field, value in obj_in.model_dump(exclude_none=True).items():
        setattr(obj, field, value)
    await db.flush()
    await db.refresh(obj)
    return obj


# ============================================================
# INVENTORY
# ============================================================

@router.get("/inventory", response_model=List[InventorySchema])
async def list_inventory(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Inventory))
    return result.scalars().all()


@router.patch("/inventory/{product_id}", response_model=InventorySchema)
async def update_inventory(product_id: int, obj_in: InventoryUpdate, db: AsyncSession = Depends(get_db)):
    inv = (await db.execute(select(Inventory).where(Inventory.product_id == product_id))).scalars().first()
    if not inv:
        raise HTTPException(status_code=404, detail="Inventory record not found for this product.")
    for field, value in obj_in.model_dump(exclude_none=True).items():
        setattr(inv, field, value)
    # Mirror stock_level back to product table
    if obj_in.current_stock is not None:
        product = (await db.execute(select(Product).where(Product.id == product_id))).scalars().first()
        if product:
            product.stock_level = obj_in.current_stock
            # Emit InventoryLow event if stock is at or below reorder point
            if product.stock_level <= product.reorder_point:
                try:
                    await EventEngineService.record_inventory_low(
                        db=db,
                        product_id=product.id,
                        sku=product.sku,
                        name=product.name,
                        current_stock=product.stock_level,
                        reorder_point=product.reorder_point,
                        source="inventory_service",
                    )
                except Exception as exc:
                    logger.warning("Failed to emit InventoryLow event: %s", exc)
    await db.flush()
    await db.refresh(inv)
    return inv


# ============================================================
# SALES
# ============================================================

@router.post("/sales", response_model=SalesSchema, status_code=status.HTTP_201_CREATED)
async def create_sale(obj_in: SalesCreate, db: AsyncSession = Depends(get_db)):
    # Validate product exists and has sufficient stock
    product = (await db.execute(select(Product).where(Product.id == obj_in.product_id))).scalars().first()
    if not product:
        raise HTTPException(status_code=404, detail="Product not found.")
    if product.stock_level < obj_in.quantity:
        raise HTTPException(
            status_code=400,
            detail=f"Insufficient stock. Available: {product.stock_level}, Requested: {obj_in.quantity}",
        )

    # Validate customer exists
    customer = (await db.execute(select(Customer).where(Customer.id == obj_in.customer_id))).scalars().first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found.")

    # Calculate final price applying discount
    discount_factor = 1.0 - (obj_in.discount_pct / 100.0)
    total_price = round(obj_in.quantity * obj_in.unit_price * discount_factor, 2)

    db_obj = Sales(
        product_id=obj_in.product_id,
        customer_id=obj_in.customer_id,
        quantity=obj_in.quantity,
        unit_price=obj_in.unit_price,
        discount_pct=obj_in.discount_pct,
        total_price=total_price,
        channel=obj_in.channel,
    )
    db.add(db_obj)

    # Decrement stock
    product.stock_level -= obj_in.quantity

    # Keep inventory table in sync
    inv = (await db.execute(select(Inventory).where(Inventory.product_id == obj_in.product_id))).scalars().first()
    if inv:
        inv.current_stock = product.stock_level

    # Accumulate Customer Lifetime Value
    customer.clv = round(customer.clv + total_price, 2)

    await db.flush()
    await db.refresh(db_obj)

    # Emit RevenueIncrease event
    try:
        await EventEngineService.record_revenue_increase(
            db=db,
            amount=total_price,
            description_text=(
                f"Sale of {obj_in.quantity}x '{product.name}' to '{customer.name}' "
                f"at ${obj_in.unit_price:.2f}/unit (discount: {obj_in.discount_pct}%)."
            ),
            customer_id=customer.id,
            sale_id=db_obj.id,
        )
    except Exception as exc:
        logger.warning("Failed to emit RevenueIncrease event: %s", exc)

    # Emit InventoryLow event if product now at or below reorder point
    if product.stock_level <= product.reorder_point:
        try:
            await EventEngineService.record_inventory_low(
                db=db,
                product_id=product.id,
                sku=product.sku,
                name=product.name,
                current_stock=product.stock_level,
                reorder_point=product.reorder_point,
                source="sales_service",
            )
        except Exception as exc:
            logger.warning("Failed to emit InventoryLow event after sale: %s", exc)

    return db_obj


@router.get("/sales", response_model=List[SalesSchema])
async def list_sales(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    customer_id: int = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Sales)
    if customer_id:
        stmt = stmt.where(Sales.customer_id == customer_id)
    result = await db.execute(stmt.order_by(Sales.date.desc()).offset(skip).limit(limit))
    return result.scalars().all()


# ============================================================
# INVOICES
# ============================================================

@router.post("/invoices", response_model=InvoiceSchema, status_code=status.HTTP_201_CREATED)
async def create_invoice(obj_in: InvoiceCreate, db: AsyncSession = Depends(get_db)):
    if not obj_in.customer_id and not obj_in.supplier_id:
        raise HTTPException(status_code=422, detail="Invoice must be linked to either a customer or supplier.")
    db_obj = Invoice(**obj_in.model_dump())
    db.add(db_obj)
    await db.flush()
    await db.refresh(db_obj)
    return db_obj


@router.get("/invoices", response_model=List[InvoiceSchema])
async def list_invoices(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    status: str = Query(None),
    invoice_type: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Invoice)
    if status:
        stmt = stmt.where(Invoice.status == status)
    if invoice_type:
        stmt = stmt.where(Invoice.invoice_type == invoice_type)
    result = await db.execute(stmt.order_by(Invoice.due_date.desc()).offset(skip).limit(limit))
    return result.scalars().all()


@router.get("/invoices/{invoice_id}", response_model=InvoiceSchema)
async def get_invoice(invoice_id: int, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(Invoice).where(Invoice.id == invoice_id))).scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    return obj


@router.patch("/invoices/{invoice_id}", response_model=InvoiceSchema)
async def update_invoice(invoice_id: int, obj_in: InvoiceUpdate, db: AsyncSession = Depends(get_db)):
    obj = (await db.execute(select(Invoice).where(Invoice.id == invoice_id))).scalars().first()
    if not obj:
        raise HTTPException(status_code=404, detail="Invoice not found.")
    for field, value in obj_in.model_dump(exclude_none=True).items():
        setattr(obj, field, value)
    await db.flush()
    await db.refresh(obj)
    return obj


# ============================================================
# EMPLOYEES
# ============================================================

@router.post("/employees", response_model=EmployeeSchema, status_code=status.HTTP_201_CREATED)
async def create_employee(obj_in: EmployeeCreate, db: AsyncSession = Depends(get_db)):
    db_obj = Employee(**obj_in.model_dump())
    db.add(db_obj)
    await db.flush()
    await db.refresh(db_obj)
    return db_obj


@router.get("/employees", response_model=List[EmployeeSchema])
async def list_employees(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Employee))
    return result.scalars().all()


# ============================================================
# BUSINESS EVENTS (Manual logging)
# ============================================================

@router.post("/events", response_model=BusinessEventSchema, status_code=status.HTTP_201_CREATED)
async def log_business_event(obj_in: BusinessEventCreate, db: AsyncSession = Depends(get_db)):
    """Manually log a business event into the episodic memory store."""
    db_obj = BusinessEvent(**obj_in.model_dump())
    db.add(db_obj)
    await db.flush()
    await db.refresh(db_obj)
    return db_obj


@router.get("/events", response_model=List[BusinessEventSchema])
async def list_business_events(
    limit: int = Query(50, ge=1, le=500),
    event_type: str = Query(None),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(BusinessEvent).order_by(BusinessEvent.timestamp.desc()).limit(limit)
    if event_type:
        stmt = select(BusinessEvent).where(BusinessEvent.event_type == event_type).order_by(
            BusinessEvent.timestamp.desc()
        ).limit(limit)
    result = await db.execute(stmt)
    return result.scalars().all()
