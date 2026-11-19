"""Business registration, login, and token sessions."""

from __future__ import annotations

import hashlib
import re
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.errors import AppError
from app.models import AuthSession, Business

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
TOKEN_DAYS = 14


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000).hex()
    return f"pbkdf2${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt, digest = stored.split("$", 2)
    except ValueError:
        return False
    if scheme != "pbkdf2":
        return False
    check = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 120_000).hex()
    return secrets.compare_digest(check, digest)


def _normalize_email(email: str) -> str:
    return email.strip().lower()


def register_business(
    db: Session,
    *,
    business_name: str,
    owner_name: str,
    email: str,
    password: str,
) -> tuple[Business, str]:
    name = " ".join((business_name or "").split())
    owner = " ".join((owner_name or "").split())
    clean_email = _normalize_email(email or "")
    if not name or len(name) > 160:
        raise AppError("Enter a business name (1–160 characters).")
    if not owner or len(owner) > 120:
        raise AppError("Enter the owner name (1–120 characters).")
    if not EMAIL_RE.match(clean_email) or len(clean_email) > 255:
        raise AppError("Enter a valid email address.")
    if not password or len(password) < 8:
        raise AppError("Password must be at least 8 characters.")
    if len(password) > 128:
        raise AppError("Password is too long.")
    if db.query(Business).filter_by(email=clean_email).first():
        raise AppError("An account with this email already exists.", 409)

    business = Business(
        business_name=name,
        owner_name=owner,
        email=clean_email,
        password_hash=hash_password(password),
    )
    db.add(business)
    db.flush()
    token = create_session(db, business)
    return business, token


def login_business(db: Session, *, email: str, password: str) -> tuple[Business, str]:
    clean_email = _normalize_email(email or "")
    business = db.query(Business).filter_by(email=clean_email).first()
    if business is None or not verify_password(password or "", business.password_hash):
        raise AppError("Invalid email or password.", 401)
    token = create_session(db, business)
    return business, token


def create_session(db: Session, business: Business) -> str:
    token = secrets.token_urlsafe(32)
    db.add(
        AuthSession(
            business_id=business.id,
            token=token,
            expires_at=datetime.now(timezone.utc) + timedelta(days=TOKEN_DAYS),
        )
    )
    db.flush()
    return token


def logout_session(db: Session, token: str | None) -> None:
    if not token:
        return
    session = db.query(AuthSession).filter_by(token=token).first()
    if session:
        db.delete(session)
        db.flush()


def business_from_token(db: Session, token: str | None) -> Business:
    if not token:
        raise AppError("Please sign in to continue.", 401)
    session = db.query(AuthSession).filter_by(token=token).first()
    if session is None:
        raise AppError("Your session expired. Please sign in again.", 401)
    expires = session.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)
    if expires < datetime.now(timezone.utc):
        db.delete(session)
        db.flush()
        raise AppError("Your session expired. Please sign in again.", 401)
    business = db.get(Business, session.business_id)
    if business is None:
        raise AppError("Please sign in to continue.", 401)
    return business


def business_payload(business: Business) -> dict:
    return {
        "id": business.id,
        "business_name": business.business_name,
        "owner_name": business.owner_name,
        "email": business.email,
        "created_at": business.created_at.isoformat() if business.created_at else None,
    }
