"""add kb fields and document kb id

Revision ID: a3b9f2d11c77
Revises: 7f1c2d9a4a10
Create Date: 2026-05-06 16:10:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a3b9f2d11c77"
down_revision: Union[str, Sequence[str], None] = "7f1c2d9a4a10"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("knowledge_bases", sa.Column("domain_type", sa.String(length=50), nullable=True))
    op.add_column("knowledge_bases", sa.Column("is_active", sa.Boolean(), nullable=True))
    op.add_column("knowledge_bases", sa.Column("created_by", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_knowledge_bases_created_by"), "knowledge_bases", ["created_by"], unique=False)
    op.create_foreign_key(
        "fk_knowledge_bases_created_by_users",
        "knowledge_bases",
        "users",
        ["created_by"],
        ["id"],
    )
    op.execute("UPDATE knowledge_bases SET domain_type = 'api' WHERE domain_type IS NULL")
    op.execute("UPDATE knowledge_bases SET is_active = TRUE WHERE is_active IS NULL")
    op.alter_column("knowledge_bases", "domain_type", nullable=False)
    op.alter_column("knowledge_bases", "is_active", nullable=False)

    op.add_column("api_documents", sa.Column("knowledge_base_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_api_documents_knowledge_base_id"), "api_documents", ["knowledge_base_id"], unique=False)
    op.create_foreign_key(
        "fk_api_documents_knowledge_base_id_knowledge_bases",
        "api_documents",
        "knowledge_bases",
        ["knowledge_base_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_api_documents_knowledge_base_id_knowledge_bases", "api_documents", type_="foreignkey")
    op.drop_index(op.f("ix_api_documents_knowledge_base_id"), table_name="api_documents")
    op.drop_column("api_documents", "knowledge_base_id")

    op.drop_constraint("fk_knowledge_bases_created_by_users", "knowledge_bases", type_="foreignkey")
    op.drop_index(op.f("ix_knowledge_bases_created_by"), table_name="knowledge_bases")
    op.drop_column("knowledge_bases", "created_by")
    op.drop_column("knowledge_bases", "is_active")
    op.drop_column("knowledge_bases", "domain_type")
