from __future__ import annotations

from datetime import date, datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import BaseModel, Field


class CompanyProfileResponse(BaseModel):
    company_id: UUID
    company_name: str
    trade_name: Optional[str] = None
    company_type: str
    pan: str
    gstin: Optional[str] = None
    tan: Optional[str] = None
    udyam_no: Optional[str] = None
    gst_type: str
    primary_state: str
    extra_states: list[str] = []
    address: Optional[dict[str, Any]] = None
    logo_url: Optional[str] = None
    fiscal_year_start: Optional[date] = None
    currency: str = "INR"
    timezone: str = "Asia/Kolkata"
    created_at: datetime
    updated_at: datetime


class CompanyProfileUpdateRequest(BaseModel):
    company_name: Optional[str] = None
    trade_name: Optional[str] = None
    address: Optional[dict[str, Any]] = None
    logo_url: Optional[str] = None
    fiscal_year_start: Optional[date] = None
    currency: Optional[str] = Field(default=None, min_length=3, max_length=3)
    timezone: Optional[str] = None

