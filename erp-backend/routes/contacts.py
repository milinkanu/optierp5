from __future__ import annotations

import json
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, File, UploadFile, status
from sqlalchemy.orm import Session
from pydantic import BaseModel

from models.contacts import (
    ContactCreateRequest,
    ContactUpdateRequest,
    ContactResponse,
    CustomerAddressResponse,
    CustomerContactResponse,
    CustomerCustomFieldResponse,
)
from models.customers import CustomerCreateRequest as BackendCustomerCreateRequest, CustomerUpdateRequest as BackendCustomerUpdateRequest
from services.common import TenantContext, get_current_context
from utils.db import get_db_session
from services import customer_service

router = APIRouter(prefix="/contacts", tags=["contacts"])


class GSTINRequest(BaseModel):
    gstin: str


def _map_to_contact_response(c) -> ContactResponse:
    """Explicitly map a Customer DB model to a ContactResponse"""
    return ContactResponse(
        contact_id=c.customer_id,
        contact_type="customer",
        company_id=c.company_id,
        customer_code=c.customer_code,
        customer_name=c.customer_name,
        customer_type=c.customer_type,
        display_name=c.display_name,
        name=c.display_name,
        currency=c.currency,
        email=c.email,
        mobile=c.mobile,
        phone=c.phone,
        gst_registration_type=c.gst_registration_type,
        gstin=c.gstin,
        pan=c.pan,
        payment_terms=c.payment_terms,
        credit_limit=float(c.credit_limit) if c.credit_limit is not None else 0.0,
        opening_balance=float(c.opening_balance) if c.opening_balance is not None else 0.0,
        opening_balance_type=c.opening_balance_type,
        msme_status=c.msme_status,
        msme_registration_no=c.msme_registration_no,
        cin=c.cin,
        invoice_delivery_preference=c.invoice_delivery_preference,
        is_active=c.is_active,
        created_at=c.created_at,
        updated_at=c.updated_at,
        addresses=[
            CustomerAddressResponse(
                address_id=a.address_id,
                address_type=a.address_type,
                attention=a.attention,
                address_line1=a.address_line1,
                address_line2=a.address_line2,
                city=a.city,
                state=a.state,
                zip_code=a.zip_code,
                country=a.country,
                phone=a.phone,
            )
            for a in c.addresses
        ],
        contacts=[
            CustomerContactResponse(
                contact_id=ct.contact_id,
                first_name=ct.first_name,
                last_name=ct.last_name,
                email=ct.email,
                phone=ct.phone,
                mobile=ct.mobile,
                designation=ct.designation,
                is_primary=ct.is_primary,
            )
            for ct in c.contacts
        ],
        custom_fields=[
            CustomerCustomFieldResponse(
                field_id=cf.field_id,
                field_key=cf.field_key,
                field_value=cf.field_value,
            )
            for cf in c.custom_fields
        ],
        tags=[t.tag_name for t in c.tags],
    )


# Create Contact (Customer)
@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def create_contact(
    payload: ContactCreateRequest,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    try:
        # Map ContactCreateRequest to CustomerCreateRequest internally
        service_payload = BackendCustomerCreateRequest(
            customer_code=payload.customer_code,
            customer_name=payload.customer_name,
            customer_type=payload.customer_type,
            display_name=payload.display_name,
            currency=payload.currency,
            email=payload.email,
            mobile=payload.mobile,
            phone=payload.phone,
            gst_registration_type=payload.gst_registration_type,
            gstin=payload.gstin,
            pan=payload.pan,
            payment_terms=payload.payment_terms,
            credit_limit=payload.credit_limit,
            opening_balance=payload.opening_balance,
            opening_balance_type=payload.opening_balance_type,
            msme_status=payload.msme_status,
            msme_registration_no=payload.msme_registration_no,
            cin=payload.cin,
            invoice_delivery_preference=payload.invoice_delivery_preference,
            addresses=[
                dict(
                    address_type=a.address_type,
                    attention=a.attention,
                    address_line1=a.address_line1,
                    address_line2=a.address_line2,
                    city=a.city,
                    state=a.state,
                    zip_code=a.zip_code,
                    country=a.country,
                    phone=a.phone,
                )
                for a in payload.addresses
            ],
            contacts=[
                dict(
                    first_name=ct.first_name,
                    last_name=ct.last_name,
                    email=ct.email,
                    phone=ct.phone,
                    mobile=ct.mobile,
                    designation=ct.designation,
                    is_primary=ct.is_primary,
                )
                for ct in payload.contacts
            ],
            custom_fields=[
                dict(field_key=cf.field_key, field_value=cf.field_value)
                for cf in payload.custom_fields
            ],
            tags=payload.tags,
        )

        customer = customer_service.create_customer(
            db=db,
            payload=service_payload,
            company_id=current_context.company_id,
            user_id=current_context.user_id,
        )
        # Load from DB with relationships
        customer_db = customer_service.get_customer(db, customer.customer_id, current_context.company_id)
        return _map_to_contact_response(customer_db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# List Contacts (filtered by query and is_active, forced to customer type)
@router.get("", response_model=list[ContactResponse])
def list_contacts(
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=500),
    q: str | None = Query(None),
    is_active: bool | None = Query(None),
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    customers = customer_service.list_customers(
        db=db,
        company_id=current_context.company_id,
        page=page,
        limit=limit,
        q=q,
        is_active=is_active,
    )
    # Ensure PAN is decrypted for response mapping
    results = []
    for c in customers:
        if c.pan:
            try:
                c.pan = customer_service.decrypt_pan(c.pan)
            except Exception:
                pass
        results.append(_map_to_contact_response(c))
    return results


# Get Contact Detail
@router.get("/{contact_id}", response_model=ContactResponse)
def get_contact(
    contact_id: UUID,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    try:
        customer = customer_service.get_customer(db, contact_id, current_context.company_id)
        return _map_to_contact_response(customer)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


# Update Contact
@router.patch("/{contact_id}", response_model=ContactResponse)
def update_contact(
    contact_id: UUID,
    payload: ContactUpdateRequest,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    try:
        # Convert Pydantic fields to CustomerUpdateRequest schema
        update_data = payload.model_dump(exclude_unset=True)
        addresses_data = update_data.pop("addresses", None)
        contacts_data = update_data.pop("contacts", None)
        cf_data = update_data.pop("custom_fields", None)
        tags_data = update_data.pop("tags", None)

        service_payload = BackendCustomerUpdateRequest(
            **update_data,
            addresses=addresses_data,
            contacts=contacts_data,
            custom_fields=cf_data,
            tags=tags_data,
        )

        customer = customer_service.update_customer(
            db=db,
            customer_id=contact_id,
            payload=service_payload,
            company_id=current_context.company_id,
            user_id=current_context.user_id,
        )
        customer_db = customer_service.get_customer(db, customer.customer_id, current_context.company_id)
        return _map_to_contact_response(customer_db)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))


# Soft Delete Contact
@router.delete("/{contact_id}")
def delete_contact(
    contact_id: UUID,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    try:
        customer_service.delete_customer(db, contact_id, current_context.company_id)
        return {"success": True, "message": "Contact deleted successfully"}
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


# Bulk Import CSV with savepoint transaction isolation
@router.post("/import-csv")
async def import_contacts_csv(
    file: UploadFile = File(...),
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Uploaded file must be a CSV")

    # Fixed Zoho customer mapping for Contacts page uploads
    column_mapping = {
        "customer_name": "Name",
        "customer_code": "Code",
        "customer_type": "Type",
        "gstin": "GSTIN",
        "email": "Email",
        "mobile": "Mobile",
        "opening_balance": "OpeningBal",
        "opening_balance_type": "BalType",
    }

    content = await file.read()
    csv_text = content.decode("utf-8-sig", errors="replace")

    try:
        report = customer_service.bulk_import_customers_csv(
            db=db,
            csv_text=csv_text,
            column_mapping=column_mapping,
            company_id=current_context.company_id,
            user_id=current_context.user_id,
        )
        return {"created": report["imported"], "failed": report["failed"], "duplicates": report["duplicates"]}
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
