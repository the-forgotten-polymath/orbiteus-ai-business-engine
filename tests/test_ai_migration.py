"""Static checks on the AI migration."""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MIG = REPO_ROOT / "backend" / "migrations" / "versions" / "c3b5d2e1c004_ai_credentials_and_embeddings.py"


def test_migration_file_exists():
    assert MIG.exists()


def test_migration_revises_outbox():
    assert 'down_revision: Union[str, None] = "b2a4e1c0d003"' in MIG.read_text()


def test_migration_creates_pgvector_extension():
    assert "CREATE EXTENSION IF NOT EXISTS vector" in MIG.read_text()


def test_migration_creates_ai_credentials_with_unique_constraint():
    text = MIG.read_text()
    assert 'op.create_table(\n            "ir_ai_credentials"' in text
    assert "uq_ir_ai_credentials_tenant_provider" in text
    assert '"secret_encrypted"' in text


def test_migration_creates_embeddings_with_hnsw_index():
    text = MIG.read_text()
    assert 'op.create_table(\n            "ir_embeddings"' in text
    assert "ALTER TABLE ir_embeddings ADD COLUMN vector vector(" in text
    assert "USING hnsw (vector vector_cosine_ops)" in text


def test_migration_uses_advisory_lock():
    assert "11534116837" in MIG.read_text()


def test_migration_has_downgrade():
    text = MIG.read_text()
    assert "def downgrade()" in text
    assert 'op.drop_table("ir_ai_credentials")' in text
    assert 'op.drop_table("ir_embeddings")' in text
