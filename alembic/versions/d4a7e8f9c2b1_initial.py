"""initial schema

Revision ID: d4a7e8f9c2b1
Revises:
Create Date: 2026-05-11 00:00:00.000000

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "d4a7e8f9c2b1"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    messagerole = sa.Enum("user", "assistant", "tool", "system", name="messagerole")
    bookingstatus = sa.Enum("confirmed", "cancelled", name="bookingstatus")
    messagerole.create(op.get_bind(), checkfirst=True)
    bookingstatus.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "chat_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_name", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "chat_messages",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("chat_sessions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("role", messagerole, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("tool_name", sa.String(100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "bookings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("customer_name", sa.String(255), nullable=False),
        sa.Column("start_date", sa.Date, nullable=False),
        sa.Column("end_date", sa.Date, nullable=False),
        sa.Column("destination", sa.String(255), nullable=False),
        sa.Column("flight_number", sa.String(20), nullable=False),
        sa.Column("hotel_name", sa.String(255), nullable=False),
        sa.Column("total_price_eur", sa.Numeric(10, 2), nullable=False),
        sa.Column("status", bookingstatus, nullable=False, server_default="confirmed"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
    )

    op.create_table(
        "faq_chunks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("source", sa.String(255), nullable=False),
        sa.Column("page", sa.Integer, nullable=False),
        sa.Column("chunk_index", sa.Integer, nullable=False),
        sa.Column("content", sa.Text, nullable=False),
        sa.Column("embedding", sa.Text, nullable=False),  # placeholder; cast below
        sa.UniqueConstraint("source", "page", "chunk_index", name="uq_faq_chunk"),
    )

    op.execute(
        "ALTER TABLE faq_chunks ALTER COLUMN embedding"
        " TYPE vector(384) USING embedding::vector(384)"
    )
    op.execute(
        "CREATE INDEX faq_chunks_embedding_hnsw"
        " ON faq_chunks USING hnsw (embedding vector_cosine_ops)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS faq_chunks_embedding_hnsw")
    op.drop_table("faq_chunks")
    op.drop_table("bookings")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")

    sa.Enum(name="bookingstatus").drop(op.get_bind(), checkfirst=True)
    sa.Enum(name="messagerole").drop(op.get_bind(), checkfirst=True)
