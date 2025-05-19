"""Remove hash constraint

Revision ID: remove_hash_constraint
Revises: 69737ee331ef
Create Date: 2025-05-19 10:46:02.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "remove_hash_constraint"
down_revision: Union[str, None] = "69737ee331ef"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the unique constraint
    op.drop_constraint("uq_event_hash_per_tenant", "events")


def downgrade() -> None:
    # Re-create the unique constraint
    op.create_unique_constraint(
        "uq_event_hash_per_tenant", "events", ["tenant_id", "hash"]
    )
