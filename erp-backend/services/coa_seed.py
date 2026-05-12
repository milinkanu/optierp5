from __future__ import annotations

from datetime import datetime
from typing import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from models.db_models import ChartOfAccount


DEFAULT_INDIAN_COA: list[dict] = [
    {"code": "1000", "name": "Assets", "type": "asset", "parent": None},
    {"code": "1100", "name": "Bank", "type": "asset", "parent": "1000"},
    {"code": "1110", "name": "Cash", "type": "asset", "parent": "1000"},
    {"code": "1200", "name": "Accounts Receivable", "type": "asset", "parent": "1000"},
    {"code": "1300", "name": "Inventory", "type": "asset", "parent": "1000"},
    {"code": "1500", "name": "Fixed Assets", "type": "asset", "parent": "1000"},
    {"code": "2000", "name": "Liabilities", "type": "liability", "parent": None},
    {"code": "2100", "name": "Accounts Payable", "type": "liability", "parent": "2000"},
    {"code": "2200", "name": "GST Payable", "type": "liability", "parent": "2000"},
    {"code": "3000", "name": "Equity", "type": "equity", "parent": None},
    {"code": "3100", "name": "Owner's Capital", "type": "equity", "parent": "3000"},
    {"code": "4000", "name": "Income", "type": "income", "parent": None},
    {"code": "4100", "name": "Sales", "type": "income", "parent": "4000"},
    {"code": "4200", "name": "Service Income", "type": "income", "parent": "4000"},
    {"code": "5000", "name": "Expenses", "type": "expense", "parent": None},
    {"code": "5100", "name": "Cost of Goods Sold", "type": "expense", "parent": "5000"},
    {"code": "5200", "name": "Rent Expense", "type": "expense", "parent": "5000"},
    {"code": "5300", "name": "Office Expense", "type": "expense", "parent": "5000"},
]


def seed_default_chart_of_accounts(db: Session, company_id: UUID) -> int:
    existing = db.scalar(select(ChartOfAccount.account_id).where(ChartOfAccount.company_id == company_id))
    if existing is not None:
        return 0

    created_at = datetime.utcnow()
    updated_at = created_at
    code_to_id: dict[str, UUID] = {}
    rows: list[ChartOfAccount] = []

    for item in DEFAULT_INDIAN_COA:
        account = ChartOfAccount(
            company_id=company_id,
            account_code=item["code"],
            account_name=item["name"],
            account_type=item["type"],
            parent_account_id=None,
            is_active=True,
            created_at=created_at,
            updated_at=updated_at,
        )
        rows.append(account)

    db.add_all(rows)
    db.flush()

    for account in rows:
        code_to_id[account.account_code] = account.account_id

    for item in DEFAULT_INDIAN_COA:
        parent_code = item["parent"]
        if parent_code is None:
            continue
        child = next(a for a in rows if a.account_code == item["code"])
        child.parent_account_id = code_to_id[parent_code]

    db.flush()
    return len(rows)

