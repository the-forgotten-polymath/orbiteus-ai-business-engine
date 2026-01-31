"""Static checks on the outbox migration file (no DB)."""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION = REPO_ROOT / "backend" / "migrations" / "versions" / "b2a4e1c0d003_outbox_and_webhooks.py"


def test_migration_file_exists():
    assert MIGRATION.exists()


def test_migration_revises_audit_log():
    text = MIGRATION.read_text()
    assert 'down_revision: Union[str, None] = "a1f3c0e1b002"' in text


def test_migration_creates_outbox_table_and_indexes():
    text = MIGRATION.read_text()
    assert 'op.create_table(\n            "ir_outbox"' in text
    for needle in (
        '"status"', '"event"', '"payload"', '"target_kind"', '"retries"',
        '"next_run_at"', '"last_error"',
        "ix_ir_outbox_status_next_run_at",
    ):
        assert needle in text, f"outbox migration missing: {needle}"


def test_migration_creates_webhooks_table():
    text = MIGRATION.read_text()
    assert 'op.create_table(\n            "ir_webhooks"' in text
    for needle in ('"url"', '"secret"', '"event_mask"', '"is_active"'):
        assert needle in text, f"webhooks migration missing: {needle}"


def test_migration_uses_advisory_lock():
    text = MIGRATION.read_text()
    assert "pg_advisory_lock" in text
    assert "11534116837" in text


def test_migration_has_downgrade():
    text = MIGRATION.read_text()
    assert "def downgrade()" in text
    assert 'op.drop_table("ir_outbox")' in text
    assert 'op.drop_table("ir_webhooks")' in text
