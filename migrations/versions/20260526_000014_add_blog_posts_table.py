"""Add blog_posts table

Revision ID: 20260526_000014
Revises: 20260521_000013
Create Date: 2026-05-26 00:00:00

"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "20260526_000014"
down_revision = "20260521_000013"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "blog_posts",
        sa.Column("id", sa.Uuid(as_uuid=True), nullable=False),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("excerpt", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("cover_image_url", sa.Text(), nullable=True),
        sa.Column("author_name", sa.Text(), nullable=False),
        sa.Column("is_published", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug", name="uq_blog_posts_slug"),
    )
    op.create_index("ix_blog_posts_published_at", "blog_posts", [sa.text("published_at DESC")])
    op.create_index("ix_blog_posts_is_published", "blog_posts", ["is_published"])


def downgrade() -> None:
    op.drop_index("ix_blog_posts_is_published", table_name="blog_posts")
    op.drop_index("ix_blog_posts_published_at", table_name="blog_posts")
    op.drop_table("blog_posts")
