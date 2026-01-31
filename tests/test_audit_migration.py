"""Static checks on the audit migration file (no DB connection)."""
from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
MIGRATION = REPO_ROOT / "backend" / "migrations" / "versions" / "a1f3c0e1b002_audit_log_and_attribution.py"


def test_migration_file_exists():
    assert MIGRATION.exists()


def test_migration_revises_initial():
    text = MIGRATION.read_text()
    assert 'down_revision: Union[str, None] = "b04954bd8aec"' in text


def test_migration_creates_audit_log_table():
    text = MIGRATION.read_text()
    assert 'op.create_table(\n            "ir_audit_log"' in text
    for column in (
        '"actor"', '"user_id"', '"request_id"', '"model"',
        '"record_id"', '"operation"', '"diff"', '"metadata"',
    ):
        assert column in text, f"audit migration missing column {column}"


def test_migration_uses_advisory_lock():
    text = MIGRATION.read_text()
    assert "pg_advisory_lock" in text
    assert "11534116837" in text  # ORBITEUS_MIGRATION_LOCK_ID


def test_migration_adds_attribution_columns_to_business_tables():
    text = MIGRATION.read_text()
    for tbl in (
        "base_companies", "base_partners", "base_users", "ir_attachments",
        "crm_pipelines", "crm_stages", "crm_customers", "crm_opportunities",
    ):
        assert f'"{tbl}"' in text, f"missing attribution add for {tbl}"
    assert '"created_by_id"' in text
    assert '"modified_by_id"' in text


def test_migration_has_downgrade():
    text = MIGRATION.read_text()
    assert "def downgrade()" in text
    assert 'op.drop_table("ir_audit_log")' in text
