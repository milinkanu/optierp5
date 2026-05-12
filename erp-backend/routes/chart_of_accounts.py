from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from models.coa import ChartOfAccountCreateRequest, ChartOfAccountResponse, ChartOfAccountUpdateRequest
from models.db_models import ChartOfAccount
from services.coa_seed import seed_default_chart_of_accounts
from utils.auth import TenantContext, get_current_context
from utils.db import get_db_session

router = APIRouter(prefix="/chart-of-accounts", tags=["chart-of-accounts"])

ALLOWED_ACCOUNT_TYPES = {"asset", "liability", "equity", "income", "expense"}


@router.post("/seed")
def seed_default_coa(
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    created = seed_default_chart_of_accounts(db, current_context.company_id)
    db.commit()
    return {"seeded": created}


@router.post("", response_model=ChartOfAccountResponse, status_code=status.HTTP_201_CREATED)
def create_account(
    payload: ChartOfAccountCreateRequest,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    if payload.account_type not in ALLOWED_ACCOUNT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid account_type")

    now = datetime.utcnow()
    row = ChartOfAccount(
        company_id=current_context.company_id,
        account_code=payload.account_code,
        account_name=payload.account_name,
        account_type=payload.account_type,
        parent_account_id=payload.parent_account_id,
        is_active=payload.is_active,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return ChartOfAccountResponse(**row.__dict__)


@router.get("", response_model=list[ChartOfAccountResponse])
def list_accounts(
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
    page: int = Query(1, ge=1),
    limit: int = Query(25, ge=1, le=200),
    q: str | None = Query(None),
    is_active: bool | None = Query(None),
):
    stmt = select(ChartOfAccount).where(ChartOfAccount.company_id == current_context.company_id)
    if q:
        stmt = stmt.where(ChartOfAccount.account_name.ilike(f"%{q}%") | ChartOfAccount.account_code.ilike(f"%{q}%"))
    if is_active is not None:
        stmt = stmt.where(ChartOfAccount.is_active == is_active)
    stmt = stmt.order_by(ChartOfAccount.account_code).offset((page - 1) * limit).limit(limit)
    rows = db.scalars(stmt).all()
    return [ChartOfAccountResponse(**r.__dict__) for r in rows]


@router.get("/{account_id}", response_model=ChartOfAccountResponse)
def get_account(
    account_id: UUID,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    row = db.scalar(
        select(ChartOfAccount)
        .where(ChartOfAccount.company_id == current_context.company_id)
        .where(ChartOfAccount.account_id == account_id)
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    return ChartOfAccountResponse(**row.__dict__)


@router.patch("/{account_id}", response_model=ChartOfAccountResponse)
def update_account(
    account_id: UUID,
    payload: ChartOfAccountUpdateRequest,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    values = payload.model_dump(exclude_unset=True)
    if "account_type" in values and values["account_type"] not in ALLOWED_ACCOUNT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid account_type")
    if not values:
        return get_account(account_id, current_context, db)

    values["updated_at"] = datetime.utcnow()
    result = db.execute(
        update(ChartOfAccount)
        .where(ChartOfAccount.company_id == current_context.company_id)
        .where(ChartOfAccount.account_id == account_id)
        .values(**values)
        .returning(ChartOfAccount)
    ).fetchone()
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    db.commit()
    row = result[0]
    return ChartOfAccountResponse(**row.__dict__)


@router.delete("/{account_id}")
def deactivate_account(
    account_id: UUID,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    row = db.scalar(
        select(ChartOfAccount)
        .where(ChartOfAccount.company_id == current_context.company_id)
        .where(ChartOfAccount.account_id == account_id)
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Account not found")
    row.is_active = False
    row.updated_at = datetime.utcnow()
    db.commit()
    return {"success": True}

