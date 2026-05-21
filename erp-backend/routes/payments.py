from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response, status
from models.payments import (
    PaymentCreateRequest,
    PaymentResponse
)
from utils.auth import TenantContext, get_current_context
from services import payment_service

router = APIRouter(prefix="/payments", tags=["payments"])

@router.post("", response_model=PaymentResponse, status_code=status.HTTP_201_CREATED)
async def create_payment(
    payload: PaymentCreateRequest,
    current_context: TenantContext = Depends(get_current_context)
):
    try:
        payment = payment_service.create_payment(
            payload=payload,
            company_id=current_context.company_id,
            user_id=current_context.user_id
        )
        return payment
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to record payment: {str(e)}"
        )

@router.get("", response_model=list[PaymentResponse])
async def list_payments(
    current_context: TenantContext = Depends(get_current_context)
):
    try:
        payments = payment_service.list_payments(company_id=current_context.company_id)
        return payments
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve payments: {str(e)}"
        )

@router.get("/{payment_id}", response_model=PaymentResponse)
async def get_payment(
    payment_id: UUID,
    current_context: TenantContext = Depends(get_current_context)
):
    try:
        payment = payment_service.get_payment(
            payment_id=payment_id,
            company_id=current_context.company_id
        )
        return payment
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment {payment_id} not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve payment: {str(e)}"
        )

@router.get("/{payment_id}/pdf")
async def get_payment_pdf(
    payment_id: UUID,
    current_context: TenantContext = Depends(get_current_context)
):
    try:
        payment = payment_service.get_payment(
            payment_id=payment_id,
            company_id=current_context.company_id
        )
        pdf_bytes = payment_service.get_payment_receipt_pdf(payment.payment_number)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=receipt_{payment.payment_number}.pdf"
            }
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Payment {payment_id} not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate payment receipt PDF: {str(e)}"
        )
