"""add chat session knowledge base id

Revision ID: f4d8a02b8a11
Revises: a3b9f2d11c77
Create Date: 2026-05-06 16:25:00
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f4d8a02b8a11"
down_revision: Union[str, Sequence[str], None] = "a3b9f2d11c77"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("chat_sessions", sa.Column("knowledge_base_id", sa.Integer(), nullable=True))
    op.create_index(op.f("ix_chat_sessions_knowledge_base_id"), "chat_sessions", ["knowledge_base_id"], unique=False)
    op.create_foreign_key(
        "fk_chat_sessions_knowledge_base_id_knowledge_bases",
        "chat_sessions",
        "knowledge_bases",
        ["knowledge_base_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_chat_sessions_knowledge_base_id_knowledge_bases", "chat_sessions", type_="foreignkey")
    op.drop_index(op.f("ix_chat_sessions_knowledge_base_id"), table_name="chat_sessions")
    op.drop_column("chat_sessions", "knowledge_base_id")
