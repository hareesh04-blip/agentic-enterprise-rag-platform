"""add chat session summary columns for conversation memory

Revision ID: b8f3a1c9e2d0
Revises: e1a5c8d2f744
Create Date: 2026-05-11
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8f3a1c9e2d0"
down_revision: Union[str, Sequence[str], None] = "e1a5c8d2f744"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("chat_sessions", sa.Column("summary_text", sa.Text(), nullable=True))
    op.add_column(
        "chat_sessions",
        sa.Column("summary_updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "chat_sessions",
        sa.Column("summary_message_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.alter_column("chat_sessions", "summary_message_count", server_default=None)


def downgrade() -> None:
    op.drop_column("chat_sessions", "summary_message_count")
    op.drop_column("chat_sessions", "summary_updated_at")
    op.drop_column("chat_sessions", "summary_text")
