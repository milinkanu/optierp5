from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class PaymentAllocationCreate(BaseModel):
    invoice_id: UUID
    amount: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)]


class PaymentCreateRequest(BaseModel):
    party_id: UUID  # Customer
    amount: Annotated[Decimal, Field(gt=0, max_digits=18, decimal_places=2)]
    payment_date: date
    payment_mode: str  # Cash, Bank Transfer, Check, UPI, Credit Card, etc.
    settlement_bank_account_id: Optional[UUID] = None
    reference_number: Optional[str] = None
    bank_charges: Annotated[Decimal, Field(ge=0, max_digits=18, decimal_places=2)] = Decimal("0")
    notes: Optional[str] = None
    allocations: List[PaymentAllocationCreate] = []


class PaymentAllocationResponse(BaseModel):
    allocation_id: UUID
    invoice_id: UUID
    invoice_number: str
    allocated_amount: float
    allocated_at: datetime


class PaymentResponse(BaseModel):
    payment_id: UUID
    company_id: UUID
    payment_number: str
    party_id: UUID
    amount: float
    unused_balance: float
    payment_date: date
    payment_mode: str
    settlement_bank_account_id: UUID
    reference_number: Optional[str] = None
    bank_charges: float
    notes: Optional[str] = None
    status: str
    created_at: datetime
    allocations: Optional[List[PaymentAllocationResponse]] = []
