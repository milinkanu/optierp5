from __future__ import annotations

import csv
import io
from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from models.contacts import ContactCreateRequest, ContactResponse, ContactUpdateRequest
from models.db_models import Party
from utils.auth import TenantContext, get_current_context
from utils.db import get_db_session

router = APIRouter(prefix="/contacts", tags=["contacts"])

ALLOWED_CONTACT_TYPES = {"customer", "vendor", "both"}


def _contact_type_to_party_type(contact_type: str) -> str:
    if contact_type not in ALLOWED_CONTACT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid contact_type")
    return contact_type


@router.post("", response_model=ContactResponse, status_code=status.HTTP_201_CREATED)
def create_contact(
    payload: ContactCreateRequest,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    now = datetime.utcnow()
    row = Party(
        company_id=current_context.company_id,
        party_name=payload.name,
        party_type=_contact_type_to_party_type(payload.contact_type),
        gstin=payload.gstin,
        pan=payload.pan,
        email=str(payload.email) if payload.email else None,
        phone=payload.phone,
        payment_terms=payload.payment_terms,
        currency=payload.currency,
        billing_address=payload.billing_address,
        shipping_address=payload.shipping_address,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ContactResponse(
        contact_id=row.party_id,
        contact_type=row.party_type,
        name=row.party_name,
        email=row.email,
        phone=row.phone,
        gstin=row.gstin,
        pan=row.pan,
        payment_terms=row.payment_terms,
        currency=row.currency,
        billing_address=row.billing_address,
        shipping_address=row.shipping_address,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.get("", response_model=list[ContactResponse])
def list_contacts(
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=200),
    q: str | None = Query(None),
    contact_type: str | None = Query(None),
):
    stmt = select(Party).where(Party.company_id == current_context.company_id)
    if q:
        stmt = stmt.where(Party.party_name.ilike(f"%{q}%"))
    if contact_type:
        stmt = stmt.where(Party.party_type == _contact_type_to_party_type(contact_type))
    stmt = stmt.order_by(Party.party_name).offset((page - 1) * limit).limit(limit)
    rows = db.scalars(stmt).all()
    return [
        ContactResponse(
            contact_id=r.party_id,
            contact_type=r.party_type,
            name=r.party_name,
            email=r.email,
            phone=r.phone,
            gstin=r.gstin,
            pan=r.pan,
            payment_terms=r.payment_terms,
            currency=r.currency,
            billing_address=r.billing_address,
            shipping_address=r.shipping_address,
            created_at=r.created_at,
            updated_at=r.updated_at,
        )
        for r in rows
    ]


@router.get("/{contact_id}", response_model=ContactResponse)
def get_contact(
    contact_id: UUID,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    row = db.scalar(
        select(Party)
        .where(Party.company_id == current_context.company_id)
        .where(Party.party_id == contact_id)
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    return ContactResponse(
        contact_id=row.party_id,
        contact_type=row.party_type,
        name=row.party_name,
        email=row.email,
        phone=row.phone,
        gstin=row.gstin,
        pan=row.pan,
        payment_terms=row.payment_terms,
        currency=row.currency,
        billing_address=row.billing_address,
        shipping_address=row.shipping_address,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


@router.patch("/{contact_id}", response_model=ContactResponse)
def update_contact(
    contact_id: UUID,
    payload: ContactUpdateRequest,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    values = payload.model_dump(exclude_unset=True)
    if "contact_type" in values:
        values["party_type"] = _contact_type_to_party_type(values.pop("contact_type"))
    if "name" in values:
        values["party_name"] = values.pop("name")
    if "email" in values:
        values["email"] = str(values["email"]) if values["email"] else None
    if not values:
        return get_contact(contact_id, current_context, db)

    values["updated_at"] = datetime.utcnow()
    row = db.execute(
        update(Party)
        .where(Party.company_id == current_context.company_id)
        .where(Party.party_id == contact_id)
        .values(**values)
        .returning(Party)
    ).fetchone()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contact not found")
    db.commit()
    result = row[0]
    return ContactResponse(
        contact_id=result.party_id,
        contact_type=result.party_type,
        name=result.party_name,
        email=result.email,
        phone=result.phone,
        gstin=result.gstin,
        pan=result.pan,
        payment_terms=result.payment_terms,
        currency=result.currency,
        billing_address=result.billing_address,
        shipping_address=result.shipping_address,
        created_at=result.created_at,
        updated_at=result.updated_at,
    )


@router.post("/import-csv")
async def import_contacts_csv(
    file: UploadFile = File(...),
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Please upload a .csv file")

    content = await file.read()
    text = content.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))

    required = {"contact_type", "name"}
    if reader.fieldnames is None or not required.issubset(set(h.strip() for h in reader.fieldnames)):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="CSV must include headers: contact_type,name")

    now = datetime.utcnow()
    created = 0
    for raw in reader:
        contact_type = (raw.get("contact_type") or "").strip().lower()
        name = (raw.get("name") or "").strip()
        if not contact_type or not name:
            continue
        party_type = _contact_type_to_party_type(contact_type)

        row = Party(
            company_id=current_context.company_id,
            party_name=name,
            party_type=party_type,
            email=(raw.get("email") or None),
            phone=(raw.get("phone") or None),
            gstin=(raw.get("gstin") or None),
            pan=(raw.get("pan") or None),
            payment_terms=(raw.get("payment_terms") or None),
            currency=(raw.get("currency") or "INR").strip() or "INR",
            billing_address=None,
            shipping_address=None,
            created_at=now,
            updated_at=now,
        )
        db.add(row)
        created += 1

    db.commit()
    return {"created": created}

