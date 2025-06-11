"""add pgcrypto extension

Revision ID: add_pgcrypto
Revises: 91de16f3d1d6
Create Date: 2025-06-10 09:15:00.000000

"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "add_pgcrypto"
down_revision = "91de16f3d1d6"
branch_labels = None
depends_on = None


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")


def downgrade():
    op.execute("DROP EXTENSION IF EXISTS pgcrypto;")
