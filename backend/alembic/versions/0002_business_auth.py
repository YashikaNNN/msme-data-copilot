"""business auth and isolation columns

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-19
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Startup create_all + ensure_auth_columns handles runtime schema.
    # This revision documents the auth isolation change for Postgres deploys.
    pass


def downgrade() -> None:
    pass
