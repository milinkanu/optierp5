from __future__ import annotations

import json
from datetime import datetime, timedelta
from hashlib import sha256
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status, Body
from pydantic import UUID4
from sqlalchemy import select, update
from sqlalchemy.orm import Session

from models.auth import (
    AuthResponse,
    ForgotPasswordRequest,
    LoginRequest,
    RefreshTokenRequest,
    ResetPasswordRequest,
    SignUpRequest,
    UserResponse,
)
from models.db_models import AuditLog, Company, RefreshToken, Role, User, UserRole
from utils.auth import JWT_REFRESH_TOKEN_EXPIRE_DAYS, TenantContext, create_access_token, get_current_context
from utils.db import get_db_session
from utils.email import build_password_reset_url, build_verification_url, send_email
from utils.security import generate_token, hash_password, hash_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])

COMPANY_TYPE_ALIASES: dict[str, str] = {
    "sole proprietorship": "sole_prop",
    "sole prop": "sole_prop",
    "proprietorship": "sole_prop",
    "partnership": "partnership",
    "private limited": "pvt_ltd",
    "pvt ltd": "pvt_ltd",
    "pvt_ltd": "pvt_ltd",
    "llp": "llp",
    "opc": "opc",
    "huf": "HUF",
}
COMPANY_TYPE_ALLOWED: set[str] = {"sole_prop", "partnership", "pvt_ltd", "llp", "opc", "HUF"}


def normalize_company_type(value: str) -> str:
    normalized = value.strip()
    key = " ".join(normalized.lower().replace("_", " ").split())
    resolved = COMPANY_TYPE_ALIASES.get(key, normalized)
    if resolved not in COMPANY_TYPE_ALLOWED:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid company_type '{value}'. Allowed: {', '.join(sorted(COMPANY_TYPE_ALLOWED))}",
        )
    return resolved


def normalize_email(email: str) -> str:
    return email.strip().lower()


def audit_hash(payload: Any) -> str:
    raw = json.dumps(payload, default=str, sort_keys=True)
    return sha256(raw.encode()).hexdigest()


def log_auth_event(db: Session, company_id: UUID4, actor_id: UUID4, operation: str, before: dict | None = None, after: dict | None = None) -> None:
    audit_record = AuditLog(
        company_id=company_id,
        entity_name="auth",
        entity_id=actor_id,
        operation=operation,
        actor_id=actor_id,
        before_state=before or {},
        after_state=after or {},
        record_hash=audit_hash({"company_id": str(company_id), "actor_id": str(actor_id), "operation": operation, "timestamp": datetime.utcnow().isoformat()}),
    )
    db.add(audit_record)


def get_user_by_email(db: Session, email: str, company_id: UUID4 | None = None) -> User | None:
    normalized = normalize_email(email)
    query = select(User).where(User.email == normalized)
    if company_id is not None:
        query = query.where(User.company_id == company_id)
        return db.scalar(query)

    users = db.scalars(query).all()
    if len(users) == 1:
        return users[0]
    if len(users) > 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Multiple companies found for this email. Please include company_id.",
        )
    return None


def get_role_names(user: User) -> list[str]:
    return [assignment.role.name for assignment in user.roles if assignment.role]


def create_refresh_token_for_user(db: Session, user: User) -> str:
    token = generate_token(48)
    refresh = RefreshToken(
        user_id=user.user_id,
        token_hash=hash_token(token),
        expires_at=datetime.utcnow() + timedelta(days=JWT_REFRESH_TOKEN_EXPIRE_DAYS),
    )
    db.add(refresh)
    db.flush()
    return token


def revoke_refresh_token(db: Session, refresh_token: str) -> None:
    token_hash = hash_token(refresh_token)
    stmt = (
        update(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .where(RefreshToken.revoked == False)
        .values(revoked=True)
    )
    db.execute(stmt)


def revoke_all_refresh_tokens_for_user(db: Session, user: User) -> None:
    stmt = update(RefreshToken).where(RefreshToken.user_id == user.user_id).values(revoked=True)
    db.execute(stmt)


def resolve_refresh_token(db: Session, refresh_token: str) -> RefreshToken:
    token_hash = hash_token(refresh_token)
    refresh = db.scalar(
        select(RefreshToken)
        .where(RefreshToken.token_hash == token_hash)
        .where(RefreshToken.revoked == False)
        .where(RefreshToken.expires_at > datetime.utcnow())
    )
    if refresh is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Refresh token invalid or expired")
    return refresh


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
def signup(payload: SignUpRequest, db: Session = Depends(get_db_session)) -> AuthResponse:
    existing = get_user_by_email(db, payload.user.email)
    if existing is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already in use")

    company_type = normalize_company_type(payload.company.company_type)
    company = Company(
        company_name=payload.company.company_name,
        trade_name=payload.company.trade_name,
        company_type=company_type,
        pan=payload.company.pan,
        gstin=payload.company.gstin,
        tan=payload.company.tan,
        udyam_no=payload.company.udyam_no,
        gst_type=payload.company.gst_type,
        primary_state=payload.company.primary_state,
        extra_states=payload.company.extra_states,
    )
    db.add(company)
    db.flush()

    verification_token = generate_token(32)
    user = User(
        company_id=company.company_id,
        email=normalize_email(payload.user.email),
        password_hash=hash_password(payload.user.password),
        name=payload.user.name,
        email_verified=True,  # Auto-verified for dev
        verification_token_hash=hash_token(verification_token),
        verification_token_expires_at=datetime.utcnow() + timedelta(hours=24),
    )
    db.add(user)
    db.flush()

    owner_role = Role(
        company_id=company.company_id,
        name="owner",
        description="Primary owner and administrator for the company",
    )
    db.add(owner_role)
    db.flush()

    db.add(UserRole(user_id=user.user_id, role_id=owner_role.role_id))
    db.commit()

    send_email(
        recipient=user.email,
        subject="Verify your FinOps email",
        body=f"Verify your email: {build_verification_url(verification_token)}",
    )
    log_auth_event(db, company.company_id, user.user_id, "signup", after={"email": user.email})

    access_token = create_access_token(
        subject=str(user.user_id),
        company_id=user.company_id,
        user_version=user.user_version,
        roles=get_role_names(user),
        delegations=[],
    )
    refresh_token = create_refresh_token_for_user(db, user)
    db.commit()

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(timedelta(minutes=15).total_seconds()),
    )


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginRequest, db: Session = Depends(get_db_session)) -> AuthResponse:
    user = get_user_by_email(db, payload.email, payload.company_id)
    if user is None or not user.is_active:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

    if not user.email_verified:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Email address must be verified before signing in")

    access_token = create_access_token(
        subject=str(user.user_id),
        company_id=user.company_id,
        user_version=user.user_version,
        roles=get_role_names(user),
        delegations=[],
    )
    refresh_token = create_refresh_token_for_user(db, user)
    db.commit()

    log_auth_event(db, user.company_id, user.user_id, "login", after={"email": user.email})

    return AuthResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        expires_in=int(timedelta(minutes=15).total_seconds()),
    )


@router.post("/refresh", response_model=AuthResponse)
def refresh_token(payload: RefreshTokenRequest, db: Session = Depends(get_db_session)) -> AuthResponse:
    refresh = resolve_refresh_token(db, payload.refresh_token)
    user = refresh.user
    revoke_refresh_token(db, payload.refresh_token)
    new_refresh_token = create_refresh_token_for_user(db, user)
    access_token = create_access_token(
        subject=str(user.user_id),
        company_id=user.company_id,
        user_version=user.user_version,
        roles=get_role_names(user),
        delegations=[],
    )
    db.commit()
    log_auth_event(db, user.company_id, user.user_id, "refresh_token")
    return AuthResponse(
        access_token=access_token,
        refresh_token=new_refresh_token,
        expires_in=int(timedelta(minutes=15).total_seconds()),
    )


@router.post("/logout")
def logout(payload: RefreshTokenRequest | None = Body(None), current_context: TenantContext = Depends(get_current_context), db: Session = Depends(get_db_session)) -> dict[str, str]:
    if payload and payload.refresh_token:
        revoke_refresh_token(db, payload.refresh_token)
    else:
        user = db.scalar(select(User).where(User.user_id == current_context.user_id))
        if user:
            revoke_all_refresh_tokens_for_user(db, user)
    db.commit()
    return {"message": "Logged out successfully"}


@router.post("/forgot-password")
def forgot_password(payload: ForgotPasswordRequest, db: Session = Depends(get_db_session)) -> dict[str, str]:
    user = get_user_by_email(db, payload.email, payload.company_id)
    if user is None:
        return {"message": "If that account exists, we sent a password reset email."}

    reset_token = generate_token(48)
    user.reset_token_hash = hash_token(reset_token)
    user.reset_token_expires_at = datetime.utcnow() + timedelta(hours=1)
    db.add(user)
    db.commit()

    send_email(
        recipient=user.email,
        subject="Reset your FinOps password",
        body=f"Reset your password: {build_password_reset_url(reset_token)}",
    )
    log_auth_event(db, user.company_id, user.user_id, "forgot_password")

    return {"message": "If that account exists, we sent a password reset email."}


@router.post("/reset-password")
def reset_password(payload: ResetPasswordRequest, db: Session = Depends(get_db_session)) -> dict[str, str]:
    token_hash = hash_token(payload.reset_token)
    user = db.scalar(
        select(User)
        .where(User.reset_token_hash == token_hash)
        .where(User.reset_token_expires_at > datetime.utcnow())
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Reset token is invalid or expired")

    user.password_hash = hash_password(payload.password)
    user.user_version += 1
    user.reset_token_hash = None
    user.reset_token_expires_at = None
    db.add(user)
    revoke_all_refresh_tokens_for_user(db, user)
    db.commit()

    log_auth_event(db, user.company_id, user.user_id, "reset_password")
    return {"message": "Password has been reset successfully"}


@router.get("/verify-email")
def verify_email(token: str = Query(...), db: Session = Depends(get_db_session)) -> dict[str, str]:
    token_hash = hash_token(token)
    user = db.scalar(
        select(User)
        .where(User.verification_token_hash == token_hash)
        .where(User.verification_token_expires_at > datetime.utcnow())
    )
    if user is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Verification token is invalid or expired")

    user.email_verified = True
    user.verification_token_hash = None
    user.verification_token_expires_at = None
    db.add(user)
    db.commit()

    log_auth_event(db, user.company_id, user.user_id, "verify_email")
    return {"message": "Email verified successfully"}


@router.get("/me", response_model=UserResponse)
def me(current_context: TenantContext = Depends(get_current_context), db: Session = Depends(get_db_session)) -> UserResponse:
    user = db.scalar(select(User).where(User.user_id == current_context.user_id))
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    return UserResponse(
        user_id=user.user_id,
        company_id=user.company_id,
        email=user.email,
        name=user.name,
        roles=get_role_names(user),
        email_verified=user.email_verified,
        is_active=user.is_active,
    )

