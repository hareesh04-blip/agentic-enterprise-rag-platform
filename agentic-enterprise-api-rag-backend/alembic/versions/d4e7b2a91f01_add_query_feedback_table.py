"""add query_feedback table for answer quality ratings

Revision ID: d4e7b2a91f01
Revises: b8f3a1c9e2d0
Create Date: 2026-05-11
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e7b2a91f01"
down_revision: Union[str, Sequence[str], None] = "b8f3a1c9e2d0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "query_feedback",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False, index=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("chat_sessions.id"), nullable=True, index=True),
        sa.Column("message_id", sa.Integer(), sa.ForeignKey("chat_messages.id"), nullable=True, index=True),
        sa.Column(
            "knowledge_base_id",
            sa.Integer(),
            sa.ForeignKey("knowledge_bases.id"),
            nullable=False,
            index=True,
        ),
        sa.Column("question_text", sa.Text(), nullable=False),
        sa.Column("answer_text", sa.Text(), nullable=False),
        sa.Column("rating", sa.String(length=32), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )
    op.create_index("ix_query_feedback_created_at", "query_feedback", ["created_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_query_feedback_created_at", table_name="query_feedback")
    op.drop_table("query_feedback")
