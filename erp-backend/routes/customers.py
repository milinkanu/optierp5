from __future__ import annotations
import json
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from models.customers import (
    CustomerCreateRequest,
    CustomerUpdateRequest,
    CustomerResponse
)
from services.common import TenantContext, get_current_context
from utils.db import get_db_session
from services import customer_service

router = APIRouter(prefix="/customers", tags=["customers"])

class GSTINRequest(BaseModel):
    gstin: str

# Create Customer
@router.post("", response_model=CustomerResponse, status_code=status.HTTP_201_CREATED)
def create_customer(
    payload: CustomerCreateRequest,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session)
):
    try:
        customer = customer_service.create_customer(
            db=db,
            payload=payload,
            company_id=current_context.company_id,
            user_id=current_context.user_id
        )
        return customer_service.get_customer(db, customer.customer_id, current_context.company_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# List Customers
@router.get("", response_model=list[CustomerResponse])
def list_customers(
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=500),
    q: str | None = Query(None),
    is_active: bool | None = Query(None),
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session)
):
    customers = customer_service.list_customers(
        db=db,
        company_id=current_context.company_id,
        page=page,
        limit=limit,
        q=q,
        is_active=is_active
    )
    # Ensure PAN is decrypted for response
    for c in customers:
        if c.pan:
            try:
                c.pan = customer_service.decrypt_pan(c.pan)
            except Exception:
                pass
    return customers

# Get Customer Detail
@router.get("/{customer_id}", response_model=CustomerResponse)
def get_customer(
    customer_id: UUID,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session)
):
    try:
        return customer_service.get_customer(db, customer_id, current_context.company_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

# Update Customer
@router.put("/{customer_id}", response_model=CustomerResponse)
def update_customer(
    customer_id: UUID,
    payload: CustomerUpdateRequest,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session)
):
    try:
        customer = customer_service.update_customer(
            db=db,
            customer_id=customer_id,
            payload=payload,
            company_id=current_context.company_id,
            user_id=current_context.user_id
        )
        return customer_service.get_customer(db, customer.customer_id, current_context.company_id)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# Delete Customer (Soft Delete)
@router.delete("/{customer_id}")
def delete_customer(
    customer_id: UUID,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session)
):
    try:
        customer_service.delete_customer(db, customer_id, current_context.company_id)
        return {"success": True, "message": "Customer deleted successfully"}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))

# Validate GSTIN Checksum
@router.post("/validate-gstin")
def validate_gstin(payload: GSTINRequest):
    is_valid = customer_service.validate_gstin_checksum(payload.gstin)
    if is_valid:
        return {"valid": True, "pan": customer_service.extract_pan_from_gstin(payload.gstin)}
    return {"valid": False, "detail": "Invalid GSTIN format or checksum"}

# Prefill GSTIN Details (Mock)
@router.post("/prefill-gstin")
def prefill_gstin(payload: GSTINRequest):
    try:
        details = customer_service.prefill_gstin_details(payload.gstin)
        return {"success": True, "data": details}
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

# Bulk Import CSV
@router.post("/import")
async def import_customers(
    file: UploadFile = File(...),
    mapping: str = Query(...), # JSON stringified column mapping dict
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session)
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file must be a CSV")

    try:
        column_mapping = json.loads(mapping)
    except json.JSONDecodeError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Mapping parameter must be a valid JSON string")

    content = await file.read()
    csv_text = content.decode("utf-8-sig", errors="replace")
    
    try:
        report = customer_service.bulk_import_customers_csv(
            db=db,
            csv_text=csv_text,
            column_mapping=column_mapping,
            company_id=current_context.company_id,
            user_id=current_context.user_id
        )
        return report
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
