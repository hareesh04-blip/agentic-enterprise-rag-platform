"""add ingestion_runs and document lineage columns

Revision ID: f8a1c2d3e4b5
Revises: a7c4e9d12f00
Create Date: 2026-05-12

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "f8a1c2d3e4b5"
down_revision: Union[str, Sequence[str], None] = "a7c4e9d12f00"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "ingestion_runs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("knowledge_base_id", sa.Integer(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("uploaded_by", sa.Integer(), nullable=True),
        sa.Column("document_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("chunk_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("vector_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("status", sa.String(length=50), nullable=False, server_default="running"),
        sa.Column("embedding_provider", sa.String(length=50), nullable=True),
        sa.Column("vector_collection", sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(["knowledge_base_id"], ["knowledge_bases.id"]),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_ingestion_runs_knowledge_base_id"), "ingestion_runs", ["knowledge_base_id"], unique=False)
    op.create_index(op.f("ix_ingestion_runs_uploaded_by"), "ingestion_runs", ["uploaded_by"], unique=False)

    op.add_column("api_documents", sa.Column("ingestion_run_id", sa.Integer(), nullable=True))
    op.add_column("api_documents", sa.Column("uploaded_by", sa.Integer(), nullable=True))
    op.add_column(
        "api_documents",
        sa.Column("uploaded_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column("api_documents", sa.Column("embedding_provider", sa.String(length=50), nullable=True))
    op.add_column("api_documents", sa.Column("vector_collection_name", sa.String(length=255), nullable=True))
    op.add_column(
        "api_documents",
        sa.Column("ingestion_status", sa.String(length=50), nullable=True, server_default="completed"),
    )
    op.add_column("api_documents", sa.Column("superseded_by_document_id", sa.Integer(), nullable=True))
    op.add_column(
        "api_documents",
        sa.Column("is_active_document", sa.Boolean(), nullable=False, server_default=sa.text("true")),
    )

    op.create_foreign_key(
        "fk_api_documents_ingestion_run_id_ingestion_runs",
        "api_documents",
        "ingestion_runs",
        ["ingestion_run_id"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_api_documents_uploaded_by_users",
        "api_documents",
        "users",
        ["uploaded_by"],
        ["id"],
    )
    op.create_foreign_key(
        "fk_api_documents_superseded_by_document_id",
        "api_documents",
        "api_documents",
        ["superseded_by_document_id"],
        ["id"],
    )
    op.create_index(op.f("ix_api_documents_ingestion_run_id"), "api_documents", ["ingestion_run_id"], unique=False)
    op.create_index(op.f("ix_api_documents_uploaded_by"), "api_documents", ["uploaded_by"], unique=False)
    op.create_index(op.f("ix_api_documents_is_active_document"), "api_documents", ["is_active_document"], unique=False)

    op.add_column("document_chunks", sa.Column("ingestion_run_id", sa.Integer(), nullable=True))
    op.create_foreign_key(
        "fk_document_chunks_ingestion_run_id_ingestion_runs",
        "document_chunks",
        "ingestion_runs",
        ["ingestion_run_id"],
        ["id"],
    )
    op.create_index(op.f("ix_document_chunks_ingestion_run_id"), "document_chunks", ["ingestion_run_id"], unique=False)

    op.execute("UPDATE api_documents SET uploaded_at = created_at WHERE uploaded_at IS NULL")
    op.execute("UPDATE api_documents SET ingestion_status = 'completed' WHERE ingestion_status IS NULL")


def downgrade() -> None:
    op.drop_index(op.f("ix_document_chunks_ingestion_run_id"), table_name="document_chunks")
    op.drop_constraint("fk_document_chunks_ingestion_run_id_ingestion_runs", "document_chunks", type_="foreignkey")
    op.drop_column("document_chunks", "ingestion_run_id")

    op.drop_index(op.f("ix_api_documents_is_active_document"), table_name="api_documents")
    op.drop_index(op.f("ix_api_documents_uploaded_by"), table_name="api_documents")
    op.drop_index(op.f("ix_api_documents_ingestion_run_id"), table_name="api_documents")
    op.drop_constraint("fk_api_documents_superseded_by_document_id", "api_documents", type_="foreignkey")
    op.drop_constraint("fk_api_documents_uploaded_by_users", "api_documents", type_="foreignkey")
    op.drop_constraint("fk_api_documents_ingestion_run_id_ingestion_runs", "api_documents", type_="foreignkey")
    op.drop_column("api_documents", "is_active_document")
    op.drop_column("api_documents", "superseded_by_document_id")
    op.drop_column("api_documents", "ingestion_status")
    op.drop_column("api_documents", "vector_collection_name")
    op.drop_column("api_documents", "embedding_provider")
    op.drop_column("api_documents", "uploaded_at")
    op.drop_column("api_documents", "uploaded_by")
    op.drop_column("api_documents", "ingestion_run_id")

    op.drop_index(op.f("ix_ingestion_runs_uploaded_by"), table_name="ingestion_runs")
    op.drop_index(op.f("ix_ingestion_runs_knowledge_base_id"), table_name="ingestion_runs")
    op.drop_table("ingestion_runs")
