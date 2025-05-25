"""update_event_model

Revision ID: 2883e176464b
Revises: 8b92bccd8308
Create Date: 2025-05-19 14:35:53.493426

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "2883e176464b"
down_revision: Union[str, None] = "2c71c52a2da3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Drop existing event table
    op.drop_table("deliveries")
    op.drop_table("events")

    # Create new event table
    op.create_table(
        "events",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("tenant_id", sa.Integer(), nullable=False),
        sa.Column("sha256", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("duplicate", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Add index for duplicate detection
    op.create_index("ix_event_unique", "events", ["tenant_id", "sha256"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_event_unique", table_name="events")
    op.drop_table("events")
