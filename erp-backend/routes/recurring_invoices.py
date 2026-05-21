from datetime import date
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from models.recurring_invoices import (
    RecurringInvoiceProfileCreateRequest,
    RecurringInvoiceProfileResponse,
    RecurringInvoiceLogResponse
)
from utils.auth import TenantContext, get_current_context
from services import recurring_invoice_service

router = APIRouter(prefix="/recurring-invoices", tags=["recurring-invoices"])

@router.post("", response_model=RecurringInvoiceProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_profile(
    payload: RecurringInvoiceProfileCreateRequest,
    current_context: TenantContext = Depends(get_current_context)
):
    try:
        profile = recurring_invoice_service.create_recurring_profile(
            payload=payload,
            company_id=current_context.company_id,
            user_id=current_context.user_id
        )
        return profile
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create recurring profile: {str(e)}"
        )

@router.get("", response_model=list[RecurringInvoiceProfileResponse])
async def list_profiles(
    current_context: TenantContext = Depends(get_current_context)
):
    try:
        profiles = recurring_invoice_service.list_recurring_profiles(company_id=current_context.company_id)
        return profiles
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve recurring profiles: {str(e)}"
        )

@router.get("/{profile_id}", response_model=RecurringInvoiceProfileResponse)
async def get_profile(
    profile_id: UUID,
    current_context: TenantContext = Depends(get_current_context)
):
    try:
        profile = recurring_invoice_service.get_recurring_profile(
            profile_id=profile_id,
            company_id=current_context.company_id
        )
        return profile
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recurring profile {profile_id} not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve recurring profile: {str(e)}"
        )

@router.put("/{profile_id}/status", response_model=RecurringInvoiceProfileResponse)
async def update_status(
    profile_id: UUID,
    status_val: str,  # "active", "paused", "stopped"
    current_context: TenantContext = Depends(get_current_context)
):
    if status_val not in ("active", "paused", "stopped"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid status. Must be active, paused, or stopped."
        )
    try:
        profile = recurring_invoice_service.update_profile_status(
            profile_id=profile_id,
            company_id=current_context.company_id,
            status=status_val
        )
        return profile
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recurring profile {profile_id} not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update profile status: {str(e)}"
        )

@router.post("/{profile_id}/trigger")
async def trigger_manual_generation(
    profile_id: UUID,
    run_date: date | None = None,
    current_context: TenantContext = Depends(get_current_context)
):
    if not run_date:
        run_date = date.today()
    try:
        invoice_id = recurring_invoice_service.trigger_invoice_generation(
            profile_id=profile_id,
            company_id=current_context.company_id,
            user_id=current_context.user_id,
            run_date=run_date
        )
        return {
            "success": True,
            "message": "Invoice successfully generated from recurring profile.",
            "generated_invoice_id": invoice_id
        }
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Recurring profile {profile_id} not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to trigger invoice generation: {str(e)}"
        )

@router.get("/{profile_id}/logs", response_model=list[RecurringInvoiceLogResponse])
async def get_logs(
    profile_id: UUID,
    current_context: TenantContext = Depends(get_current_context)
):
    try:
        logs = recurring_invoice_service.get_profile_logs(
            profile_id=profile_id,
            company_id=current_context.company_id
        )
        return logs
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve run logs: {str(e)}"
        )
