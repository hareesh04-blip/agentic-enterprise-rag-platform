"""fix chat_sessions.summary_message_count default and NOT NULL

Revision ID: a7c4e9d12f00
Revises: c2e8a1b304d9
Create Date: 2026-05-12

Step 50.2: migration b8f3a1c9e2d0 added summary_message_count then removed server_default,
so INSERTs that omit the column received NULL. Backfill, restore DEFAULT 0, keep NOT NULL.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "a7c4e9d12f00"
down_revision: Union[str, Sequence[str], None] = "c2e8a1b304d9"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(sa.text("UPDATE chat_sessions SET summary_message_count = 0 WHERE summary_message_count IS NULL"))
    op.alter_column(
        "chat_sessions",
        "summary_message_count",
        existing_type=sa.Integer(),
        nullable=False,
        server_default=sa.text("0"),
    )


def downgrade() -> None:
    op.alter_column(
        "chat_sessions",
        "summary_message_count",
        existing_type=sa.Integer(),
        nullable=False,
        server_default=None,
    )
