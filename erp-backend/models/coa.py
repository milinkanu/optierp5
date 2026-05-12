from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel


class ChartOfAccountCreateRequest(BaseModel):
    account_code: str
    account_name: str
    account_type: str  # asset|liability|equity|income|expense
    description: Optional[str] = None
    parent_account_id: Optional[UUID] = None
    is_active: bool = True


class ChartOfAccountUpdateRequest(BaseModel):
    account_code: Optional[str] = None
    account_name: Optional[str] = None
    account_type: Optional[str] = None
    description: Optional[str] = None
    parent_account_id: Optional[UUID] = None
    is_active: Optional[bool] = None


class ChartOfAccountResponse(BaseModel):
    account_id: UUID
    account_code: str
    account_name: str
    account_type: str
    description: Optional[str] = None
    parent_account_id: Optional[UUID] = None
    is_active: bool
    created_at: datetime
    updated_at: datetime

