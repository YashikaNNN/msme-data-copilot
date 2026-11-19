"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-11-19
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Tables are created by SQLAlchemy metadata at startup for SQLite and local
    # development. This revision documents the baseline for Postgres deployments.
    pass


def downgrade() -> None:
    pass
