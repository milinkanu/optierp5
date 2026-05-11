from __future__ import annotations

from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from models.auth import UserCreateRequest, UserResponse
from models.db_models import Role, User, UserRole
from utils.auth import TenantContext, get_current_context
from utils.db import get_db_session
from utils.security import hash_password

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_user(
    payload: UserCreateRequest,
    current_context: TenantContext = Depends(get_current_context),
    db: Session = Depends(get_db_session),
) -> UserResponse:
    email = payload.email.strip().lower()
    existing_user = db.scalar(
        select(User).where(User.company_id == current_context.company_id, User.email == email)
    )
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already exists for this company")

    user = User(
        user_id=uuid4(),
        company_id=current_context.company_id,
        email=email,
        name=payload.name,
        password_hash=hash_password(payload.password),
        is_active=True,
        email_verified=False,
    )
    db.add(user)
    db.flush()

    role_name = payload.roles[0] if payload.roles else "employee"
    role = db.scalar(
        select(Role).where(Role.company_id == current_context.company_id, Role.name == role_name)
    )
    if role is None:
        role = Role(
            company_id=current_context.company_id,
            name=role_name,
            description="Auto-created role for the company",
        )
        db.add(role)
        db.flush()

    db.add(UserRole(user_id=user.user_id, role_id=role.role_id))
    db.commit()

    return UserResponse(
        user_id=user.user_id,
        company_id=user.company_id,
        email=user.email,
        name=user.name,
        roles=[role.name],
        email_verified=user.email_verified,
        is_active=user.is_active,
    )

