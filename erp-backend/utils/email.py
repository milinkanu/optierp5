from __future__ import annotations

import os
from urllib.parse import urlencode

from fastapi import HTTPException


SMTP_ENABLED = os.getenv("SMTP_ENABLED", "false").lower() in ("1", "true")
EMAIL_FROM = os.getenv("EMAIL_FROM", "noreply@finops.local")
FRONTEND_BASE_URL = os.getenv("FRONTEND_BASE_URL", "http://localhost:5173")


def build_verification_url(verification_token: str) -> str:
    return f"{FRONTEND_BASE_URL}/auth/verify-email?{urlencode({'token': verification_token})}"


def build_password_reset_url(reset_token: str) -> str:
    return f"{FRONTEND_BASE_URL}/auth/reset-password?{urlencode({'token': reset_token})}"


def send_email(recipient: str, subject: str, body: str) -> None:
    if SMTP_ENABLED:
        # Add SMTP sending logic here for production.
        raise HTTPException(status_code=500, detail="SMTP is enabled but no mailer is configured")

    print(f"[AUTH EMAIL] to={recipient} subject={subject}\n{body}\n")
