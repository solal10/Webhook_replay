"""add_delivery_retry_columns

Revision ID: 9c23ca15018e
Revises: a40bf122ccbd
Create Date: 2025-05-26 09:31:36.172411

"""

from datetime import datetime, timezone
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "9c23ca15018e"
down_revision: Union[str, None] = "a40bf122ccbd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "deliveries",
        sa.Column("attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "deliveries", sa.Column("next_run", sa.DateTime(timezone=True), nullable=True)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("deliveries", "next_run")
    op.drop_column("deliveries", "attempts")
