"""Shared FastAPI dependencies."""

from __future__ import annotations

from fastapi import Depends, Header
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import Business, Dataset
from app.services.auth import business_from_token
from app.services.repository import get_dataset


def _extract_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    value = authorization.strip()
    if value.lower().startswith("bearer "):
        return value[7:].strip() or None
    return value or None


def current_business(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_db),
) -> Business:
    return business_from_token(db, _extract_token(authorization))


def optional_token(authorization: str | None = Header(default=None)) -> str | None:
    return _extract_token(authorization)


def owned_dataset(dataset_id: int, business: Business, db: Session) -> Dataset:
    return get_dataset(db, dataset_id, business_id=business.id)
