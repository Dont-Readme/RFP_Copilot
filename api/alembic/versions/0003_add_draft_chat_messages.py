"""Add draft_chat_messages table.

Revision ID: 0003_add_draft_chat_messages
Revises: 0002_add_document_chunks
Create Date: 2026-03-06 13:10:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0003_add_draft_chat_messages"
down_revision = "0002_add_document_chunks"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "draft_chat_messages",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("draft_section_id", sa.Integer(), nullable=False),
        sa.Column("role", sa.String(length=20), nullable=False),
        sa.Column("message_text", sa.Text(), nullable=False),
        sa.Column("suggestion_text", sa.Text(), nullable=True),
        sa.Column("apply_mode", sa.String(length=30), nullable=False),
        sa.Column("selection_start", sa.Integer(), nullable=True),
        sa.Column("selection_end", sa.Integer(), nullable=True),
        sa.Column("selection_text", sa.Text(), nullable=True),
        sa.Column("applied_at", sa.DateTime(timezone=False), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(["draft_section_id"], ["draft_sections.id"]),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_draft_chat_messages_draft_section_id"), "draft_chat_messages", ["draft_section_id"], unique=False)
    op.create_index(op.f("ix_draft_chat_messages_project_id"), "draft_chat_messages", ["project_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_draft_chat_messages_project_id"), table_name="draft_chat_messages")
    op.drop_index(op.f("ix_draft_chat_messages_draft_section_id"), table_name="draft_chat_messages")
    op.drop_table("draft_chat_messages")
