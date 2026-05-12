from __future__ import annotations

from uuid import UUID, uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from models.auth import CompanyCreateRequest
from models.companies import CompanyProfileResponse, CompanyProfileUpdateRequest
from models.db_models import Company
from utils.auth import TenantContext, get_current_context
from utils.db import get_db_session

router = APIRouter(prefix="/companies", tags=["companies"])


@router.post("")
async def create_company(payload: CompanyCreateRequest):
    return {"company_id": str(uuid4()), "company_name": payload.company_name}


@router.post("/{company_id}/bank-accounts")
async def add_bank_account(company_id: UUID, payload: dict, current_context: TenantContext = Depends(get_current_context)):
    if str(current_context.company_id) != str(company_id):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Tenant mismatch")
    return {"bank_account_id": str(uuid4()), "company_id": str(company_id)}


@router.get("/me", response_model=CompanyProfileResponse)
def get_my_company_profile(
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    company = db.scalar(select(Company).where(Company.company_id == current_context.company_id))
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return CompanyProfileResponse(**company.__dict__)


@router.patch("/me", response_model=CompanyProfileResponse)
def update_my_company_profile(
    payload: CompanyProfileUpdateRequest,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
):
    values = payload.model_dump(exclude_unset=True)
    if not values:
        company = db.scalar(select(Company).where(Company.company_id == current_context.company_id))
        if company is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
        return CompanyProfileResponse(**company.__dict__)

    db.execute(update(Company).where(Company.company_id == current_context.company_id).values(**values))
    db.commit()
    company = db.scalar(select(Company).where(Company.company_id == current_context.company_id))
    if company is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Company not found")
    return CompanyProfileResponse(**company.__dict__)

