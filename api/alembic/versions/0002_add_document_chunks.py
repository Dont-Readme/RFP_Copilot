"""Add document_chunks table.

Revision ID: 0002_add_document_chunks
Revises: 0001_bootstrap_placeholder
Create Date: 2026-03-06 12:50:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0002_add_document_chunks"
down_revision = "0001_bootstrap_placeholder"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "document_chunks",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("document_kind", sa.String(length=20), nullable=False),
        sa.Column("document_id", sa.Integer(), nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("source_path", sa.Text(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column("page_start", sa.Integer(), nullable=True),
        sa.Column("page_end", sa.Integer(), nullable=True),
        sa.Column("route_label", sa.String(length=50), nullable=True),
        sa.Column("token_estimate", sa.Integer(), nullable=False),
        sa.Column("text_content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("document_kind", "document_id", "chunk_index", name="uq_document_chunk"),
    )
    op.create_index(op.f("ix_document_chunks_document_id"), "document_chunks", ["document_id"], unique=False)
    op.create_index(op.f("ix_document_chunks_document_kind"), "document_chunks", ["document_kind"], unique=False)
    op.create_index(op.f("ix_document_chunks_project_id"), "document_chunks", ["project_id"], unique=False)
    op.create_index(op.f("ix_document_chunks_route_label"), "document_chunks", ["route_label"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_document_chunks_route_label"), table_name="document_chunks")
    op.drop_index(op.f("ix_document_chunks_project_id"), table_name="document_chunks")
    op.drop_index(op.f("ix_document_chunks_document_kind"), table_name="document_chunks")
    op.drop_index(op.f("ix_document_chunks_document_id"), table_name="document_chunks")
    op.drop_table("document_chunks")
