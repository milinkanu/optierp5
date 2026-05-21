from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Response, status
from models.delivery_challans import (
    DeliveryChallanCreateRequest,
    DeliveryChallanResponse
)
from models.invoices import InvoiceResponse
from utils.auth import TenantContext, get_current_context
from services import delivery_challan_service

router = APIRouter(prefix="/delivery-challans", tags=["delivery-challans"])

@router.post("", response_model=DeliveryChallanResponse, status_code=status.HTTP_201_CREATED)
async def create_challan(
    payload: DeliveryChallanCreateRequest,
    current_context: TenantContext = Depends(get_current_context)
):
    try:
        challan = delivery_challan_service.create_delivery_challan(
            payload=payload,
            company_id=current_context.company_id,
            user_id=current_context.user_id
        )
        return challan
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to create delivery challan: {str(e)}"
        )

@router.get("", response_model=list[DeliveryChallanResponse])
async def list_challans(
    current_context: TenantContext = Depends(get_current_context)
):
    try:
        challans = delivery_challan_service.list_delivery_challans(company_id=current_context.company_id)
        return challans
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve delivery challans: {str(e)}"
        )

@router.get("/{delivery_challan_id}", response_model=DeliveryChallanResponse)
async def get_challan(
    delivery_challan_id: UUID,
    current_context: TenantContext = Depends(get_current_context)
):
    try:
        challan = delivery_challan_service.get_delivery_challan(
            delivery_challan_id=delivery_challan_id,
            company_id=current_context.company_id
        )
        return challan
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Delivery challan {delivery_challan_id} not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve delivery challan: {str(e)}"
        )

@router.get("/{delivery_challan_id}/pdf")
async def get_challan_pdf(
    delivery_challan_id: UUID,
    current_context: TenantContext = Depends(get_current_context)
):
    try:
        challan = delivery_challan_service.get_delivery_challan(
            delivery_challan_id=delivery_challan_id,
            company_id=current_context.company_id
        )
        pdf_bytes = delivery_challan_service.get_delivery_challan_pdf(challan.challan_number)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename=challan_{challan.challan_number}.pdf"
            }
        )
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Delivery challan {delivery_challan_id} not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate delivery challan PDF: {str(e)}"
        )

@router.post("/{delivery_challan_id}/convert", response_model=InvoiceResponse)
async def convert_challan(
    delivery_challan_id: UUID,
    current_context: TenantContext = Depends(get_current_context)
):
    try:
        invoice = delivery_challan_service.convert_challan_to_invoice(
            delivery_challan_id=delivery_challan_id,
            company_id=current_context.company_id,
            user_id=current_context.user_id
        )
        return invoice
    except KeyError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Delivery challan {delivery_challan_id} not found"
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to convert delivery challan to invoice: {str(e)}"
        )
