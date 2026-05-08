"""expand api parameters mandatory optional

Revision ID: c2e4a9d71b33
Revises: 9b7c1e2d4f90
Create Date: 2026-05-06 17:00:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "c2e4a9d71b33"
down_revision: Union[str, Sequence[str], None] = "9b7c1e2d4f90"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        "api_parameters",
        "mandatory_optional",
        existing_type=sa.String(length=50),
        type_=sa.Text(),
        existing_nullable=True,
        postgresql_using="mandatory_optional::text",
    )


def downgrade() -> None:
    op.alter_column(
        "api_parameters",
        "mandatory_optional",
        existing_type=sa.Text(),
        type_=sa.String(length=50),
        existing_nullable=True,
        postgresql_using="left(mandatory_optional, 50)",
    )
