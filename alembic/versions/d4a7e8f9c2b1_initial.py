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

    op.execute("CREATE TYPE messagerole AS ENUM ('user', 'assistant', 'tool', 'system')")
    op.execute("CREATE TYPE bookingstatus AS ENUM ('confirmed', 'cancelled')")

    op.execute("""
        CREATE TABLE chat_sessions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            customer_name VARCHAR(255),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE chat_messages (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            session_id UUID NOT NULL REFERENCES chat_sessions(id) ON DELETE CASCADE,
            role messagerole NOT NULL,
            content TEXT NOT NULL,
            tool_name VARCHAR(100),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE bookings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            customer_name VARCHAR(255) NOT NULL,
            start_date DATE NOT NULL,
            end_date DATE NOT NULL,
            destination VARCHAR(255) NOT NULL,
            flight_number VARCHAR(20) NOT NULL,
            hotel_name VARCHAR(255) NOT NULL,
            total_price_eur NUMERIC(10, 2) NOT NULL,
            status bookingstatus NOT NULL DEFAULT 'confirmed',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
    """)

    op.execute("""
        CREATE TABLE faq_chunks (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            source VARCHAR(255) NOT NULL,
            page INTEGER NOT NULL,
            chunk_index INTEGER NOT NULL,
            content TEXT NOT NULL,
            embedding vector(384),
            CONSTRAINT uq_faq_chunk UNIQUE (source, page, chunk_index)
        )
    """)

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
