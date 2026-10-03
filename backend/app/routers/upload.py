"""
File Upload Router — Accepts document uploads and queues background parsing.

Endpoints:
  POST /upload/invoice          — PDF/Image invoices
  POST /upload/gst              — GST reports (PDF/JSON/XLSX)
  POST /upload/bank             — Bank statements (any format)
  POST /upload/excel            — Excel data imports (inventory)
  POST /upload/supplier_notice  — Price increase notifications (PDF/Image)
  POST /upload/purchase_order   — Purchase orders (PDF/Image)

Files are stored immediately; parsing is done asynchronously via BackgroundTasks.
"""

import logging
import os
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, File, HTTPException, UploadFile

from app.config import settings
from app.services.doc_intelligence import DocumentIntelligenceService

router = APIRouter(prefix="/upload", tags=["File Upload"])
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS: dict[str, set[str]] = {
    "invoice": {".pdf", ".png", ".jpg", ".jpeg"},
    "gst": {".pdf", ".json", ".xlsx"},
    "bank": {".pdf", ".csv", ".xlsx", ".xls"},
    "excel": {".xls", ".xlsx"},
    "supplier_notice": {".pdf", ".png", ".jpg", ".jpeg"},
    "purchase_order": {".pdf", ".png", ".jpg", ".jpeg"},
}


def _save_file(file: UploadFile, subfolder: str) -> str:
    """Persist the uploaded bytes to disk synchronously and return absolute path."""
    target_dir = os.path.join(settings.UPLOAD_DIR, subfolder)
    os.makedirs(target_dir, exist_ok=True)

    ext = os.path.splitext(file.filename or "file")[1].lower()
    unique_name = f"{uuid.uuid4()}{ext}"
    filepath = os.path.join(target_dir, unique_name)

    with open(filepath, "wb") as buf:
        buf.write(file.file.read())

    logger.info("Saved upload → %s", filepath)
    return filepath


def _validate_extension(filename: str, category: str) -> None:
    ext = os.path.splitext(filename or "")[1].lower()
    allowed = ALLOWED_EXTENSIONS.get(category, set())
    if allowed and ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file extension '{ext}'. Allowed for {category}: {sorted(allowed)}",
        )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/invoice")
async def upload_invoice(
    file: UploadFile = File(...),
    doc_service: DocumentIntelligenceService = Depends(DocumentIntelligenceService),
):
    """Upload a supplier or customer invoice for automated data extraction."""
    _validate_extension(file.filename, "invoice")
    filepath = _save_file(file, "invoices")
    await doc_service.process_document_task(filepath, "invoice")
    return {
        "message": "Invoice processed successfully.",
        "filepath": filepath,
        "original_filename": file.filename,
    }


@router.post("/gst")
async def upload_gst(
    file: UploadFile = File(...),
    doc_service: DocumentIntelligenceService = Depends(DocumentIntelligenceService),
):
    """Upload a GST return/report for extraction and reconciliation."""
    _validate_extension(file.filename, "gst")
    filepath = _save_file(file, "gst")
    await doc_service.process_document_task(filepath, "gst")
    return {
        "message": "GST document processed successfully.",
        "filepath": filepath,
        "original_filename": file.filename,
    }


@router.post("/bank")
async def upload_bank(
    file: UploadFile = File(...),
    doc_service: DocumentIntelligenceService = Depends(DocumentIntelligenceService),
):
    """Upload a bank statement for cashflow analysis."""
    _validate_extension(file.filename, "bank")
    filepath = _save_file(file, "bank_statements")
    await doc_service.process_document_task(filepath, "bank")
    return {
        "message": "Bank statement processed and reconciled successfully.",
        "filepath": filepath,
        "original_filename": file.filename,
    }


@router.post("/excel")
async def upload_excel(
    file: UploadFile = File(...),
    doc_service: DocumentIntelligenceService = Depends(DocumentIntelligenceService),
):
    """Upload an Excel file for bulk data import (sales, products, inventory, etc.)."""
    _validate_extension(file.filename, "excel")
    filepath = _save_file(file, "excel_imports")
    await doc_service.process_document_task(filepath, "excel")
    return {
        "message": "Excel file processed. Bulk import complete.",
        "filepath": filepath,
        "original_filename": file.filename,
    }


@router.post("/supplier_notice")
async def upload_supplier_notice(
    file: UploadFile = File(...),
    doc_service: DocumentIntelligenceService = Depends(DocumentIntelligenceService),
):
    """Upload a price increase notice or supplier update."""
    _validate_extension(file.filename, "supplier_notice")
    filepath = _save_file(file, "supplier_notices")
    await doc_service.process_document_task(filepath, "supplier_notice")
    return {
        "message": "Supplier notice processed and applied successfully.",
        "filepath": filepath,
        "original_filename": file.filename,
    }


@router.post("/purchase_order")
async def upload_purchase_order(
    file: UploadFile = File(...),
    doc_service: DocumentIntelligenceService = Depends(DocumentIntelligenceService),
):
    """Upload a customer purchase order."""
    _validate_extension(file.filename, "purchase_order")
    filepath = _save_file(file, "purchase_orders")
    await doc_service.process_document_task(filepath, "purchase_order")
    return {
        "message": "Purchase order processed successfully.",
        "filepath": filepath,
        "original_filename": file.filename,
    }


@router.post("/sample")
async def upload_sample(
    payload: dict,
    doc_service: DocumentIntelligenceService = Depends(DocumentIntelligenceService),
):
    """Process a preloaded demo document from sample_docs folder."""
    sample_key = payload.get("sample_key")
    samples_map = {
        "invoice_001": ("invoices/invoice_001.pdf", "invoice"),
        "invoice_002": ("invoices/invoice_002.pdf", "invoice"),
        "overdue_invoice": ("invoices/overdue_invoice.pdf", "invoice"),
        "gst_return": ("gst/gst_return_june.pdf", "gst"),
        "bank_statement": ("bank/bank_statement.csv", "bank"),
        "july_statement": ("bank/july_statement.xlsx", "bank"),
        "inventory": ("inventory/inventory.xlsx", "excel"),
        "price_increase": ("suppliers/price_increase_notice.pdf", "supplier_notice"),
        "po_2101": ("purchase_orders/po_2101.pdf", "purchase_order"),
    }

    if sample_key not in samples_map:
        raise HTTPException(status_code=400, detail=f"Invalid sample key: {sample_key}")

    rel_path, category = samples_map[sample_key]
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..", "sample_docs"))
    filepath = os.path.join(base_dir, rel_path)

    if not os.path.exists(filepath):
        raise HTTPException(status_code=404, detail=f"Sample file not found: {filepath}")

    await doc_service.process_document_task(filepath, category)
    return {
        "message": f"Sample document '{sample_key}' processed successfully.",
        "filepath": filepath,
        "category": category
    }

