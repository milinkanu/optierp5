from __future__ import annotations

import os
from uuid import UUID, uuid4
from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import Response

from models.credit_notes import (
    CreditNoteCreateRequest,
    CreditNoteUpdateRequest,
    CreditNoteResponse,
    CreditNoteApplyRequest,
    CreditNoteInvoiceMappingResponse,
    CreditNoteActivityLogResponse,
)
from services import credit_note_service
from utils.auth import TenantContext, get_current_context

router = APIRouter(prefix="/credit-notes", tags=["credit-notes"])


@router.post("", response_model=CreditNoteResponse, status_code=status.HTTP_201_CREATED)
def create_credit_note(
    payload: CreditNoteCreateRequest,
    current_context: TenantContext = Depends(get_current_context),
):
    return credit_note_service.create_credit_note(
        payload=payload,
        company_id=current_context.company_id,
        user_id=current_context.user_id
    )


@router.get("", response_model=list[CreditNoteResponse])
def list_credit_notes(
    current_context: TenantContext = Depends(get_current_context),
):
    return credit_note_service.list_credit_notes(company_id=current_context.company_id)


@router.get("/{credit_note_id}", response_model=CreditNoteResponse)
def get_credit_note(
    credit_note_id: UUID,
    current_context: TenantContext = Depends(get_current_context),
):
    return credit_note_service.get_credit_note(
        credit_note_id=credit_note_id,
        company_id=current_context.company_id
    )


@router.put("/{credit_note_id}", response_model=CreditNoteResponse)
def update_credit_note(
    credit_note_id: UUID,
    payload: CreditNoteUpdateRequest,
    current_context: TenantContext = Depends(get_current_context),
):
    return credit_note_service.update_credit_note(
        credit_note_id=credit_note_id,
        payload=payload,
        company_id=current_context.company_id,
        user_id=current_context.user_id
    )


@router.delete("/{credit_note_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_credit_note(
    credit_note_id: UUID,
    current_context: TenantContext = Depends(get_current_context),
):
    credit_note_service.delete_credit_note(
        credit_note_id=credit_note_id,
        company_id=current_context.company_id,
        user_id=current_context.user_id
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/{credit_note_id}/apply-to-invoice", response_model=CreditNoteInvoiceMappingResponse)
def apply_credit_note(
    credit_note_id: UUID,
    payload: CreditNoteApplyRequest,
    current_context: TenantContext = Depends(get_current_context),
):
    return credit_note_service.apply_credit_note_to_invoice(
        credit_note_id=credit_note_id,
        payload=payload,
        company_id=current_context.company_id,
        user_id=current_context.user_id
    )


@router.get("/{credit_note_id}/pdf")
def get_credit_note_pdf(
    credit_note_id: UUID,
    current_context: TenantContext = Depends(get_current_context),
):
    cn = credit_note_service.get_credit_note(
        credit_note_id=credit_note_id,
        company_id=current_context.company_id
    )
    pdf_bytes = credit_note_service.get_credit_note_pdf(cn.credit_note_number)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=credit_note_{cn.credit_note_number}.pdf"}
    )


@router.get("/{credit_note_id}/activities", response_model=list[CreditNoteActivityLogResponse])
def get_credit_note_activities(
    credit_note_id: UUID,
    current_context: TenantContext = Depends(get_current_context),
):
    return credit_note_service.get_credit_note_activities(
        credit_note_id=credit_note_id,
        company_id=current_context.company_id
    )


@router.get("/{credit_note_id}/mappings", response_model=list[CreditNoteInvoiceMappingResponse])
def get_credit_note_mappings(
    credit_note_id: UUID,
    current_context: TenantContext = Depends(get_current_context),
):
    return credit_note_service.get_credit_note_mappings(
        credit_note_id=credit_note_id,
        company_id=current_context.company_id
    )
