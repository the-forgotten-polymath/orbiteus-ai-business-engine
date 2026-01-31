"""AI credentials + pgvector embeddings

Adds:
- pgvector extension (CREATE EXTENSION IF NOT EXISTS vector)
- ir_ai_credentials table (BYOK, Fernet-encrypted secret)
- ir_embeddings table with VECTOR(1536) column + HNSW index

Revision ID: c3b5d2e1c004
Revises: b2a4e1c0d003
Create Date: 2026-05-03

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "c3b5d2e1c004"
down_revision: Union[str, None] = "b2a4e1c0d003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


# Default embedding width matches the most common provider models in MVP
# (OpenAI text-embedding-3-small @ 1536, Anthropic Voyage @ 1024 will need
# their own table or per-row indexing). HNSW recall is fine at this size.
EMBEDDING_DIM = 1536


def _advisory_lock() -> None:
    op.get_bind().exec_driver_sql("SELECT pg_advisory_lock(11534116837)")


def _advisory_unlock() -> None:
    op.get_bind().exec_driver_sql("SELECT pg_advisory_unlock(11534116837)")


def upgrade() -> None:
    _advisory_lock()
    try:
        # Ensure the pgvector extension is installed.
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")

        # ir_ai_credentials
        op.create_table(
            "ir_ai_credentials",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("create_date", sa.DateTime(timezone=True), nullable=False),
            sa.Column("write_date", sa.DateTime(timezone=True), nullable=False),
            sa.Column("tenant_id", sa.UUID(), nullable=True),
            sa.Column("provider", sa.String(length=50), nullable=False),
            sa.Column("secret_encrypted", sa.LargeBinary(), nullable=False),
            sa.Column("model_default", sa.String(length=255), nullable=True),
            sa.Column("is_active", sa.Boolean(), server_default="true", nullable=False),
            sa.Column("monthly_token_budget", sa.Integer(), nullable=True),
            sa.Column("usage_tokens", sa.Integer(), server_default="0", nullable=False),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_ir_ai_credentials")),
            sa.UniqueConstraint("tenant_id", "provider", name="uq_ir_ai_credentials_tenant_provider"),
        )
        op.create_index(op.f("ix_ir_ai_credentials_tenant_id"), "ir_ai_credentials", ["tenant_id"])

        # ir_embeddings — VECTOR(N) plus HNSW index.
        op.create_table(
            "ir_embeddings",
            sa.Column("id", sa.UUID(), nullable=False),
            sa.Column("create_date", sa.DateTime(timezone=True), nullable=False),
            sa.Column("write_date", sa.DateTime(timezone=True), nullable=False),
            sa.Column("tenant_id", sa.UUID(), nullable=True),
            sa.Column("model", sa.String(length=255), nullable=False),
            sa.Column("record_id", sa.UUID(), nullable=True),
            sa.Column("provider", sa.String(length=50), nullable=False),
            sa.Column("model_name", sa.String(length=255), nullable=False),
            sa.Column("dim", sa.Integer(), server_default="0", nullable=False),
            sa.PrimaryKeyConstraint("id", name=op.f("pk_ir_embeddings")),
        )
        # Add the vector column via raw SQL — SQLAlchemy core doesn't know
        # `vector(N)` without the pgvector dialect plugin loaded.
        op.execute(f"ALTER TABLE ir_embeddings ADD COLUMN vector vector({EMBEDDING_DIM})")
        op.create_index(op.f("ix_ir_embeddings_tenant_id"), "ir_embeddings", ["tenant_id"])
        op.create_index(op.f("ix_ir_embeddings_model"), "ir_embeddings", ["model"])
        op.create_index(op.f("ix_ir_embeddings_record_id"), "ir_embeddings", ["record_id"])
        op.create_unique_constraint(
            "uq_ir_embeddings_scope",
            "ir_embeddings",
            ["tenant_id", "model", "record_id", "provider", "model_name"],
        )
        # HNSW index for cosine similarity.
        op.execute(
            "CREATE INDEX IF NOT EXISTS ix_ir_embeddings_hnsw "
            "ON ir_embeddings USING hnsw (vector vector_cosine_ops)"
        )
    finally:
        _advisory_unlock()


def downgrade() -> None:
    _advisory_lock()
    try:
        op.execute("DROP INDEX IF EXISTS ix_ir_embeddings_hnsw")
        op.drop_constraint("uq_ir_embeddings_scope", "ir_embeddings", type_="unique")
        op.drop_index(op.f("ix_ir_embeddings_record_id"), table_name="ir_embeddings")
        op.drop_index(op.f("ix_ir_embeddings_model"), table_name="ir_embeddings")
        op.drop_index(op.f("ix_ir_embeddings_tenant_id"), table_name="ir_embeddings")
        op.drop_table("ir_embeddings")

        op.drop_index(op.f("ix_ir_ai_credentials_tenant_id"), table_name="ir_ai_credentials")
        op.drop_constraint(
            "uq_ir_ai_credentials_tenant_provider",
            "ir_ai_credentials",
            type_="unique",
        )
        op.drop_table("ir_ai_credentials")
        # Leave the extension in place; other tables may depend on it.
    finally:
        _advisory_unlock()
