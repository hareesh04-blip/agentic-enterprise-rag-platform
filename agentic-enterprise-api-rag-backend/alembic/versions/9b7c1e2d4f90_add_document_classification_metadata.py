"""add document classification metadata

Revision ID: 9b7c1e2d4f90
Revises: f4d8a02b8a11
Create Date: 2026-05-06 16:45:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9b7c1e2d4f90"
down_revision: Union[str, Sequence[str], None] = "f4d8a02b8a11"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("api_documents", sa.Column("document_type", sa.String(length=50), nullable=True))
    op.add_column("api_documents", sa.Column("source_domain", sa.String(length=100), nullable=True))
    op.add_column("api_documents", sa.Column("product_name", sa.String(length=255), nullable=True))
    op.execute("UPDATE api_documents SET document_type = 'api' WHERE document_type IS NULL")
    op.alter_column("api_documents", "document_type", nullable=False)


def downgrade() -> None:
    op.drop_column("api_documents", "product_name")
    op.drop_column("api_documents", "source_domain")
    op.drop_column("api_documents", "document_type")
