"""expand api parameters param type

Revision ID: e1a5c8d2f744
Revises: c2e4a9d71b33
Create Date: 2026-05-06 17:08:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "e1a5c8d2f744"
down_revision: Union[str, Sequence[str], None] = "c2e4a9d71b33"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "api_parameters",
        "param_type",
        existing_type=sa.String(length=100),
        type_=sa.Text(),
        existing_nullable=True,
        postgresql_using="param_type::text",
    )


def downgrade() -> None:
    op.alter_column(
        "api_parameters",
        "param_type",
        existing_type=sa.Text(),
        type_=sa.String(length=100),
        existing_nullable=True,
        postgresql_using="left(param_type, 100)",
    )
