"""add resolution fields to improvement_tasks

Revision ID: b3d8f1a92c42
Revises: a5c9e2f0b8d1
Create Date: 2026-05-11
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b3d8f1a92c42"
down_revision: Union[str, Sequence[str], None] = "a5c9e2f0b8d1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("improvement_tasks", sa.Column("resolution_notes", sa.Text(), nullable=True))
    op.add_column(
        "improvement_tasks",
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "improvement_tasks",
        sa.Column("resolved_by", sa.Integer(), sa.ForeignKey("users.id"), nullable=True),
    )
    op.create_index("ix_improvement_tasks_resolved_by", "improvement_tasks", ["resolved_by"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_improvement_tasks_resolved_by", table_name="improvement_tasks")
    op.drop_column("improvement_tasks", "resolved_by")
    op.drop_column("improvement_tasks", "resolved_at")
    op.drop_column("improvement_tasks", "resolution_notes")
