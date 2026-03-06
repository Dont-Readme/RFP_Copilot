"""Add multi-file RFP metadata and requirement items.

Revision ID: 0004_rfp_multifile_and_requirements
Revises: 0003_add_draft_chat_messages
Create Date: 2026-03-06 16:20:00
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "0004_rfp_multifile_and_requirements"
down_revision = "0003_add_draft_chat_messages"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("project_files") as batch_op:
        batch_op.add_column(
            sa.Column("role", sa.String(length=50), nullable=False, server_default="other")
        )

    with op.batch_alter_table("rfp_extractions") as batch_op:
        batch_op.add_column(
            sa.Column("project_summary_text", sa.Text(), nullable=False, server_default="")
        )

    with op.batch_alter_table("evaluation_items") as batch_op:
        batch_op.add_column(
            sa.Column("score_text", sa.String(length=100), nullable=False, server_default="")
        )

    op.create_table(
        "rfp_requirement_items",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("project_id", sa.Integer(), nullable=False),
        sa.Column("sort_order", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("requirement_no", sa.String(length=100), nullable=False, server_default=""),
        sa.Column("name", sa.String(length=255), nullable=False, server_default=""),
        sa.Column("definition", sa.Text(), nullable=False, server_default=""),
        sa.Column("details", sa.Text(), nullable=False, server_default=""),
        sa.Column("created_at", sa.DateTime(timezone=False), nullable=False),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_rfp_requirement_items_project_id"),
        "rfp_requirement_items",
        ["project_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_rfp_requirement_items_project_id"), table_name="rfp_requirement_items")
    op.drop_table("rfp_requirement_items")

    with op.batch_alter_table("evaluation_items") as batch_op:
        batch_op.drop_column("score_text")

    with op.batch_alter_table("rfp_extractions") as batch_op:
        batch_op.drop_column("project_summary_text")

    with op.batch_alter_table("project_files") as batch_op:
        batch_op.drop_column("role")

